import json
import re
import typer
from datetime import date, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from tanren import config
from tanren.storage import db

console = Console()

_ASSESSMENT_INTERVAL_DAYS = 7

MAJOR_CATEGORIES: dict[str, str] = {
    "実装力":       "言語・フレームワーク・ライブラリ・ツール",
    "設計力":       "システム設計・DB設計・API設計・アーキテクチャ",
    "インフラ・運用": "クラウド・コンテナ・CI/CD・監視・ネットワーク・OS",
    "品質・テスト":  "テスト・デバッグ・コードレビュー",
    "セキュリティ":  "認証・認可・暗号化・脆弱性対策",
    "ソフトスキル":  "コミュニケーション・技術共有・文書化・PM",
}


def assess_skills_if_needed():
    """前回査定から7日以上経っていれば自動でスキル査定を実行する"""
    last = config.get("last_skill_assessment")
    if last:
        days_since = (date.today() - date.fromisoformat(last)).days
        if days_since < _ASSESSMENT_INTERVAL_DAYS:
            return

    console.print("\n[dim]スキルを自動査定中...[/dim]")
    try:
        _run_assessment()
        config.set_value("last_skill_assessment", date.today().isoformat())
    except Exception as e:
        console.print(f"[dim]スキル自動査定をスキップしました: {e}[/dim]")


def skills(
    assess: bool = typer.Option(False, "--assess", "-a", help="今すぐAIにスキルを査定させる"),
):
    """AIが査定したスキルマップを表示する"""
    if assess:
        console.print("[cyan]スキルを査定中...[/cyan]")
        try:
            _run_assessment()
            config.set_value("last_skill_assessment", date.today().isoformat())
        except Exception as e:
            console.print(f"[red]査定に失敗しました: {e}[/red]")
            return
        console.print()
    _list_skills()


def _list_skills():
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM skills ORDER BY major_category, category, level DESC"
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[dim]スキルが登録されていません。tanren checkin を続けると自動査定されます。[/dim]")
        return

    # major_category → category → skills の2階層でグループ化
    grouped: dict[str, dict[str, list]] = {}
    for r in rows:
        major = r["major_category"] or "実装力"
        minor = r["category"] or "その他"
        grouped.setdefault(major, {}).setdefault(minor, []).append(r)

    last = config.get("last_skill_assessment")
    assessed_label = f"[dim]最終査定: {last}[/dim]" if last else ""
    console.print(Panel(f"[bold cyan]スキルマップ[/bold cyan]  {assessed_label}", expand=False))
    console.print()

    for major in MAJOR_CATEGORIES:
        if major not in grouped:
            continue
        console.print(f"[bold cyan]◆ {major}[/bold cyan]")
        for minor, skills_in_minor in grouped[major].items():
            table = Table(title=f"  {minor}", title_style="dim", show_header=False, box=None, padding=(0, 2))
            table.add_column("スキル名", style="white")
            table.add_column("レベル", width=12)
            table.add_column("メモ", style="dim")
            for r in skills_in_minor:
                level = r["level"] or 0
                bar = "█" * level + "░" * (5 - level)
                table.add_row(r["name"], f"{bar} {level}/5", r["notes"] or "")
            console.print(table)
        console.print()


def _build_assessment_prompt() -> str:
    conn = db.get_connection()

    since = (date.today() - timedelta(days=60)).isoformat()
    checkins = conn.execute(
        """SELECT date, work_summary, learnings, blockers
           FROM checkins WHERE date >= ? ORDER BY date DESC""",
        (since,),
    ).fetchall()

    sessions = conn.execute(
        "SELECT prompt, response FROM sessions ORDER BY created_at DESC LIMIT 10"
    ).fetchall()

    goals = conn.execute(
        "SELECT title, category FROM goals WHERE status = 'active'"
    ).fetchall()

    current_skills = conn.execute(
        "SELECT name, major_category, category, level FROM skills ORDER BY major_category, category"
    ).fetchall()

    conn.close()

    checkin_text = "\n".join(
        f"[{c['date']}] 作業: {c['work_summary']} / 学び: {c['learnings']}"
        + (f" / 詰まり: {c['blockers']}" if c["blockers"] else "")
        for c in checkins
    ) or "記録なし"

    session_text = "\n".join(
        f"Q: {s['prompt'][:100]}" for s in sessions
    ) or "記録なし"

    goal_text = "\n".join(f"- [{g['category']}] {g['title']}" for g in goals) or "なし"

    current_text = "\n".join(
        f"- {s['name']} ({s['major_category']} / {s['category']}) Lv.{s['level']}"
        for s in current_skills
    ) or "なし"

    major_desc = "\n".join(
        f"- {major}: {desc}" for major, desc in MAJOR_CATEGORIES.items()
    )

    return f"""以下のエンジニアの活動記録を分析し、スキルを評価してください。

【直近60日のチェックイン記録】
{checkin_text}

【最近の質問履歴】
{session_text}

【現在の目標】
{goal_text}

【現在登録済みのスキル】
{current_text}

---

大分類の定義:
{major_desc}

上記の記録に登場した技術・スキルを評価し、以下のJSON形式のみで回答してください。
説明文や前置きは不要です。JSONだけを出力してください。

レベル基準: 1=入門 2=基礎 3=中級（実務で使える） 4=上級 5=エキスパート

[
  {{
    "name": "スキル名",
    "major_category": "大分類（上記6つから選択）",
    "category": "小分類（言語/フレームワーク/ツール/概念 など具体的に）",
    "level": 1から5の整数,
    "notes": "根拠（1文）"
  }}
]

制約:
- 記録に実際に登場したスキルのみを含める
- 最大20個
- 既存スキルも再評価して含める
- major_category は必ず上記6つの大分類から選ぶ"""


def _run_assessment():
    from tanren.ai import client as ai_client

    prompt = _build_assessment_prompt()
    text, usage = ai_client.generate(prompt, max_output_tokens=1500)

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("AIの応答からJSONを抽出できませんでした")

    assessed = json.loads(match.group())

    conn = db.get_connection()
    updated, added = [], []

    with conn:
        for skill in assessed:
            name = skill.get("name", "").strip()
            major = skill.get("major_category", "実装力").strip()
            category = skill.get("category", "その他").strip()
            level = int(skill.get("level", 1))
            notes = skill.get("notes", "")

            if not name or level not in range(1, 6):
                continue
            if major not in MAJOR_CATEGORIES:
                major = "実装力"

            existing = conn.execute(
                "SELECT id, level FROM skills WHERE name = ?", (name,)
            ).fetchone()

            if existing:
                old_level = existing["level"]
                conn.execute(
                    "INSERT INTO skill_history (skill_id, level) VALUES (?, ?)",
                    (existing["id"], old_level),
                )
                conn.execute(
                    """UPDATE skills
                       SET major_category=?, category=?, level=?, notes=?, updated_at=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (major, category, level, notes or None, existing["id"]),
                )
                if old_level != level:
                    arrow = "↑" if level > old_level else "↓"
                    updated.append(f"{name}: Lv.{old_level} {arrow} Lv.{level}")
            else:
                conn.execute(
                    "INSERT INTO skills (name, major_category, category, level, notes) VALUES (?, ?, ?, ?, ?)",
                    (name, major, category, level, notes or None),
                )
                added.append(f"{name} ({major} / {category}) Lv.{level}")

    conn.close()

    if added or updated:
        console.print("[cyan]スキル自動査定結果:[/cyan]")
        for s in added:
            console.print(f"  [green]+ {s}[/green]")
        for s in updated:
            console.print(f"  [yellow]~ {s}[/yellow]")
    else:
        console.print("[dim]スキルに変更はありませんでした[/dim]")

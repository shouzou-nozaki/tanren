import json
import re
import typer
from datetime import date, timedelta
from rich.console import Console
from rich.table import Table
from tanren import config
from tanren.storage import db

console = Console()

_CATEGORIES = ["language", "framework", "infrastructure", "database", "soft", "other"]
_ASSESSMENT_INTERVAL_DAYS = 7


def assess_skills_if_needed():
    """前回査定から7日以上経っていれば自動でスキル査定を実行する"""
    last = config.get("last_skill_assessment")
    if last:
        days_since = (date.today() - date.fromisoformat(last)).days
        if days_since < _ASSESSMENT_INTERVAL_DAYS:
            return

    console.print("\n[dim]🔍 スキルを自動査定中...[/dim]")
    try:
        _run_assessment()
        config.set_value("last_skill_assessment", date.today().isoformat())
    except Exception as e:
        console.print(f"[dim]スキル自動査定をスキップしました: {e}[/dim]")


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
        "SELECT name, category, level FROM skills ORDER BY category"
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
        f"- {s['name']} ({s['category']}) Lv.{s['level']}" for s in current_skills
    ) or "なし"

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

上記の記録に登場した技術・スキルを評価し、以下のJSON形式のみで回答してください。
説明文や前置きは不要です。JSONだけを出力してください。

レベル基準: 1=入門 2=基礎 3=中級（実務で使える） 4=上級 5=エキスパート

カテゴリ: language / framework / infrastructure / database / soft / other

[
  {{"name": "スキル名", "category": "カテゴリ", "level": 1-5, "notes": "根拠（1文）"}},
  ...
]

制約:
- 記録に実際に登場したスキルのみを含める
- 最大15個
- 既存スキルも再評価して含める"""


def _run_assessment():
    from tanren.ai import client as ai_client

    prompt = _build_assessment_prompt()
    text, usage = ai_client.generate(prompt, max_output_tokens=1024)

    # JSON を抽出（```json ... ``` などで囲まれている場合も対応）
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("AIの応答からJSONを抽出できませんでした")

    assessed = json.loads(match.group())

    conn = db.get_connection()
    updated, added = [], []

    with conn:
        for skill in assessed:
            name = skill.get("name", "").strip()
            category = skill.get("category", "other")
            level = int(skill.get("level", 1))
            notes = skill.get("notes", "")

            if not name or level not in range(1, 6):
                continue
            if category not in _CATEGORIES:
                category = "other"

            existing = conn.execute(
                "SELECT id, level FROM skills WHERE name = ?", (name,)
            ).fetchone()

            if existing:
                if existing["level"] != level:
                    conn.execute(
                        "INSERT INTO skill_history (skill_id, level) VALUES (?, ?)",
                        (existing["id"], existing["level"]),
                    )
                    conn.execute(
                        "UPDATE skills SET category=?, level=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (category, level, notes or None, existing["id"]),
                    )
                    arrow = "↑" if level > existing["level"] else "↓"
                    updated.append(f"{name}: Lv.{existing['level']} {arrow} Lv.{level}")
            else:
                conn.execute(
                    "INSERT INTO skills (name, category, level, notes) VALUES (?, ?, ?, ?)",
                    (name, category, level, notes or None),
                )
                added.append(f"{name} Lv.{level}")

    conn.close()

    if added or updated:
        console.print("[cyan]📊 スキル自動査定結果:[/cyan]")
        for s in added:
            console.print(f"  [green]+ {s}[/green]")
        for s in updated:
            console.print(f"  [yellow]~ {s}[/yellow]")
    else:
        console.print("[dim]スキルに変更はありませんでした[/dim]")


def skills(
    assess: bool = typer.Option(False, "--assess", "-a", help="今すぐAIにスキルを査定させる"),
):
    """AIが査定したスキルマップを表示する"""
    if assess:
        console.print("[cyan]🔍 スキルを査定中...[/cyan]")
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
        "SELECT * FROM skills ORDER BY category, level DESC"
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[dim]スキルが登録されていません。tanren skills add で追加してください。[/dim]")
        return

    table = Table(title="スキルマップ")
    table.add_column("スキル名")
    table.add_column("カテゴリ", width=14)
    table.add_column("レベル", width=10)
    table.add_column("メモ")

    for r in rows:
        level = r["level"] or 0
        bar = "█" * level + "░" * (5 - level)
        table.add_row(r["name"], r["category"] or "-", f"{bar} {level}/5", r["notes"] or "")

    console.print(table)



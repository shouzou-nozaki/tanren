import json
import re
import typer
from datetime import date, timedelta
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.panel import Panel
from tanren import config
from tanren.storage import db

console = Console()

_ASSESSMENT_INTERVAL_DAYS = 7

MAJOR_CATEGORIES: list[str] = [
    "実装力",
    "設計力",
    "インフラ・運用",
    "データベース",
    "セキュリティ",
    "ソフトスキル",
]

_SKILL_GUIDANCE = {
    "実装力":       "プログラミング言語名・フレームワーク名のみ（Java, Python, C#, Spring Boot, React 等）。AIツール・ツール活用・開発手法は含めない",
    "設計力":       "設計手法の種別のみ（システム設計, DB設計, API設計, DDD 等）。課題名・機能名・要件名は含めない",
    "インフラ・運用": "具体的なツール・サービス名のみ（Docker, AWS, Linux, GitHub Actions, Kubernetes 等）",
    "データベース":  "具体的なDB製品名のみ（PostgreSQL, MySQL, Oracle, Redis, MongoDB 等）",
    "セキュリティ":  "セキュリティ専門分野のみ（認証・認可, 暗号化, 脆弱性対策, ゼロトラスト 等）",
    "ソフトスキル":  "対人・組織スキルのみ（コードレビュー, 技術共有, ドキュメント作成, メンタリング 等）。自己学習・課題認識・学習習慣は含めない",
}

_SUMMARY_CATEGORY = "__summary__"


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

    # major_category ごとに summary と詳細を分ける
    summaries: dict[str, dict] = {}
    details: dict[str, list] = {}
    for r in rows:
        major = r["major_category"] or "実装力"
        if r["category"] == _SUMMARY_CATEGORY:
            summaries[major] = dict(r)
        else:
            details.setdefault(major, []).append(r)

    last = config.get("last_skill_assessment")
    label = f"[dim]最終査定: {last}[/dim]" if last else ""
    level_legend = "[dim]Lv1=指示があればできる  Lv2=一人でできる  Lv3=他人に教えられる  Lv4=改善・最適化できる  Lv5=仕組み化・標準化できる[/dim]"
    console.print(Panel(f"[bold cyan]スキルマップ[/bold cyan]  {label}\n{level_legend}", expand=False))
    console.print()

    for major in MAJOR_CATEGORIES:
        summary = summaries.get(major)
        skills_list = details.get(major, [])
        if not summary and not skills_list:
            continue

        # 大分類ヘッダー（総評レベル + コメント）
        if summary:
            level = summary["level"] or 0
            bar = "█" * level + "░" * (5 - level)
            notes = summary["notes"] or ""
            console.print(f"[bold cyan]◆ {major}[/bold cyan]  {bar} {level}/5  [dim]{notes}[/dim]")
        else:
            console.print(f"[bold cyan]◆ {major}[/bold cyan]")

        # 詳細
        for r in skills_list:
            lv = r["level"] or 0
            bar = "█" * lv + "░" * (5 - lv)
            console.print(f"    {r['name']}    {bar} {lv}/5")
            if r["notes"]:
                console.print(Padding(f"[dim]{r['notes']}[/dim]", pad=(0, 4, 0, 6)))

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
        "SELECT prompt FROM sessions ORDER BY created_at DESC LIMIT 10"
    ).fetchall()

    goals = conn.execute(
        "SELECT title FROM goals WHERE status = 'active'"
    ).fetchall()

    conn.close()

    checkin_text = "\n".join(
        f"[{c['date']}] {c['work_summary']} / {c['learnings']}"
        + (f" / {c['blockers']}" if c["blockers"] else "")
        for c in checkins
    ) or "記録なし"

    session_text = "\n".join(f"- {s['prompt'][:80]}" for s in sessions) or "記録なし"
    goal_text = "\n".join(f"- {g['title']}" for g in goals) or "なし"

    guidance = "\n".join(
        f"  - {major}: skills には {hint}" for major, hint in _SKILL_GUIDANCE.items()
    )

    return f"""以下のエンジニアの活動記録を分析し、スキルを評価してください。

【直近60日のチェックイン記録】
{checkin_text}

【最近の質問履歴】
{session_text}

【現在の目標】
{goal_text}

---

以下のJSON形式のみで回答してください。説明文は不要です。JSONだけを出力してください。

レベル基準:
Lv1=指示があればできる
Lv2=一人でできる
Lv3=他人に教えられる
Lv4=改善・最適化できる
Lv5=仕組み化・標準化できる

各大分類の skills に含めるスキル名の例:
{guidance}

[
  {{
    "major_category": "大分類名（実装力/設計力/インフラ・運用/データベース/セキュリティ/ソフトスキル）",
    "level": 大分類全体の総合レベル（1〜5）,
    "summary": "総評コメント（1〜2文）",
    "skills": [
      {{"name": "個別スキル名", "level": 1〜5, "reason": "このレベルと評価した根拠（1文）"}}
    ]
  }}
]

制約:
- 必ず6つの大分類すべてを出力する（記録がない分野は level=1、summary="実績なし"、skills=[] とする）
- skills は各大分類で最大5個まで、記録に明示的に登場したものだけ含める
- スキル名は固有の技術名・製品名・手法名のみ（Java, PostgreSQL, Docker, システム設計 等）
- 以下はスキル名として絶対に使わない:
  - 練習課題名・タスク名・機能名（例: "レートリミット設計", "ユーザー認証実装"）
  - AIツール活用・AI補助・AIを使った〇〇（例: "AIを活用したコーディング", "AIでの開発"）
  - 学習行動・姿勢（例: "自己学習", "課題認識", "学習習慣"）
  - 曖昧な能力表現（例: "問題解決", "論理的思考", "プログラミング", "開発"）
- 有効なスキル名が見つからないカテゴリは skills=[] とする（無理に埋めない）"""


def _run_assessment():
    from tanren.ai import client as ai_client

    prompt = _build_assessment_prompt()
    text, _ = ai_client.generate(prompt, max_output_tokens=1500)

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("AIの応答からJSONを抽出できませんでした")

    assessed = json.loads(match.group())

    conn = db.get_connection()
    with conn:
        # 既存の査定結果を全削除して入れ直す
        conn.execute("DELETE FROM skill_history WHERE skill_id IN (SELECT id FROM skills)")
        conn.execute("DELETE FROM skills")

        for entry in assessed:
            major = entry.get("major_category", "").strip()
            level = int(entry.get("level", 1))
            summary = entry.get("summary", "")
            skills_list = entry.get("skills", [])

            if major not in MAJOR_CATEGORIES or level not in range(1, 6):
                continue

            # 総評エントリー
            conn.execute(
                "INSERT INTO skills (name, major_category, category, level, notes) VALUES (?, ?, ?, ?, ?)",
                (major, major, _SUMMARY_CATEGORY, level, summary or None),
            )

            # 詳細スキル
            for skill in skills_list[:5]:
                name = skill.get("name", "").strip()
                sk_level = int(skill.get("level", 1))
                reason = skill.get("reason", "").strip()
                if not name or sk_level not in range(1, 6):
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO skills (name, major_category, category, level, notes) VALUES (?, ?, ?, ?, ?)",
                    (name, major, "詳細", sk_level, reason or None),
                )

    conn.close()
    console.print("[cyan]スキル査定が完了しました[/cyan]")

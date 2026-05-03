from google import genai
from google.genai import types
from datetime import date
from tanren import config
from tanren.storage import db

MODEL = "gemini-2.0-flash"

_SYSTEM_PROMPT = """あなたは豊富な実務経験を持つシニアエンジニアリングコーチです。
落ち着いた専門家として、的確で実践的なアドバイスを行います。

人格：
- 冷静かつ論理的。感情的にならず、事実と経験に基づいて話す
- 言葉は簡潔・明確。無駄な修飾を使わず、本質を突く
- 問題の根本原因を重視する。表面的な解決策ではなく構造的な理解を促す
- 成長を客観的に評価する。過剰に褒めず、率直にフィードバックする
- 相手のレベルや文脈を読んで、適切な粒度で話す

忖度しない原則：
- 良いものは良い、問題があるものは問題があると率直に伝える
- 相手が聞きたいことより、相手が聞くべきことを優先する
- 間違いや改善点は曖昧にせず、具体的に指摘する
- 褒めるのは本当に価値があるときだけ。空虚な賛辞は使わない
- 厳しいフィードバックも、長期的な成長のために必要なら躊躇わない

コーチングの原則：
- ユーザーの過去の記録・文脈を踏まえた上でアドバイスする
- 抽象論より具体的な次のアクションを示す
- 詰まっている問題には根本原因を掘り下げ、再発しない理解を促す
- 技術的な質問には正確かつ実践的に答える
- キャリアやマインドセットの相談にも経験則を踏まえて向き合う
- 回答は日本語で行う"""


def _build_context() -> str:
    conn = db.get_connection()

    checkins = conn.execute(
        """SELECT date, work_summary, learnings, blockers, energy_level
           FROM checkins ORDER BY date DESC LIMIT 60"""
    ).fetchall()

    summaries = conn.execute(
        """SELECT type, period, content, original_count
           FROM summaries WHERE type != 'session_summary'
           ORDER BY period DESC LIMIT 12"""
    ).fetchall()

    session_summary = conn.execute(
        "SELECT content FROM summaries WHERE type = 'session_summary' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    recent_sessions = conn.execute(
        """SELECT prompt, response, created_at FROM sessions
           ORDER BY created_at DESC LIMIT 5"""
    ).fetchall()

    goals = conn.execute(
        "SELECT title, description, category, target_date FROM goals WHERE status = 'active'"
    ).fetchall()

    skills = conn.execute(
        "SELECT name, category, level FROM skills ORDER BY category, level DESC"
    ).fetchall()

    conn.close()

    parts = []

    if checkins:
        parts.append("【最近のチェックイン記録（週別）】")
        by_week: dict[str, list] = {}
        for c in checkins:
            d = date.fromisoformat(c["date"])
            week_key = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
            by_week.setdefault(week_key, []).append(c)
        for week_key in sorted(by_week.keys(), reverse=True):
            entries = by_week[week_key]
            avg_energy = sum(e["energy_level"] or 0 for e in entries) / len(entries)
            works = "・".join(e["work_summary"] for e in entries if e["work_summary"])
            learnings = "・".join(e["learnings"] for e in entries if e["learnings"])
            blockers = "・".join(e["blockers"] for e in entries if e["blockers"])
            entry = f"[{week_key}] 平均エネルギー:{avg_energy:.1f}/5\n  作業: {works}\n  学び: {learnings}"
            if blockers:
                entry += f"\n  詰まり: {blockers}"
            parts.append(entry)

    if summaries:
        parts.append("\n【過去のサマリー記録】")
        for s in summaries:
            parts.append(f"[{s['type']} {s['period']} / {s['original_count']}件]\n{s['content']}")

    if session_summary:
        parts.append("\n【過去のコーチングやり取り（サマリー）】")
        parts.append(session_summary["content"])

    if recent_sessions:
        parts.append("\n【直近のコーチングやり取り（新しい順）】")
        for s in recent_sessions:
            parts.append(f"[{s['created_at'][:10]}]\nQ: {s['prompt']}\nA: {s['response']}")

    if goals:
        parts.append("\n【現在の目標】")
        for g in goals:
            line = f"- [{g['category']}] {g['title']}"
            if g["target_date"]:
                line += f" (期限: {g['target_date']})"
            if g["description"]:
                line += f"\n  {g['description']}"
            parts.append(line)

    if skills:
        parts.append("\n【スキルマップ】")
        for s in skills:
            parts.append(f"- {s['name']} ({s['category']}) Lv.{s['level']}/5")

    return "\n".join(parts)


def calculate_cost(usage) -> float:
    return 0.0


def chat_stream(question: str, max_output_tokens: int = 1024):
    """ストリーミングでレスポンスを生成する。(text_chunk を yield し、最後に usage_metadata を返す)"""
    api_key = config.get("api_key")
    client = genai.Client(api_key=api_key)

    context = _build_context()
    system = _SYSTEM_PROMPT
    if context:
        system += "\n\n" + context

    response = client.models.generate_content_stream(
        model=MODEL,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_output_tokens,
        ),
    )

    usage_metadata = None
    for chunk in response:
        if chunk.text:
            yield chunk.text
        if chunk.usage_metadata:
            usage_metadata = chunk.usage_metadata

    return usage_metadata

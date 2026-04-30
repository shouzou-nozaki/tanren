import anthropic
from tanren import config
from tanren.storage import db

MODEL = "claude-sonnet-4-6"

_INPUT_PRICE       = 3.00  / 1_000_000
_OUTPUT_PRICE      = 15.00 / 1_000_000
_CACHE_WRITE_PRICE = 3.75  / 1_000_000
_CACHE_READ_PRICE  = 0.30  / 1_000_000

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
           FROM checkins ORDER BY date DESC LIMIT 30"""
    ).fetchall()

    summaries = conn.execute(
        """SELECT type, period, content, original_count
           FROM summaries ORDER BY period DESC LIMIT 12"""
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
        parts.append("【最近のチェックイン記録（新しい順）】")
        for c in checkins:
            entry = f"[{c['date']}] エネルギー:{c['energy_level']}/5\n  作業: {c['work_summary']}\n  学び: {c['learnings']}"
            if c["blockers"]:
                entry += f"\n  詰まり: {c['blockers']}"
            parts.append(entry)

    if summaries:
        parts.append("\n【過去のサマリー記録】")
        for s in summaries:
            parts.append(f"[{s['type']} {s['period']} / {s['original_count']}件]\n{s['content']}")

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
    return (
        getattr(usage, "input_tokens", 0)                  * _INPUT_PRICE
        + getattr(usage, "output_tokens", 0)               * _OUTPUT_PRICE
        + getattr(usage, "cache_creation_input_tokens", 0) * _CACHE_WRITE_PRICE
        + getattr(usage, "cache_read_input_tokens", 0)     * _CACHE_READ_PRICE
    )


def chat_stream(question: str):
    """ストリーミングでレスポンスを生成する。(text_chunk を yield し、最後に usage を返す)"""
    api_key = config.get("api_key")
    client = anthropic.Anthropic(api_key=api_key)

    context = _build_context()

    system_content = [
        {"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
    ]
    if context:
        system_content.append(
            {"type": "text", "text": context, "cache_control": {"type": "ephemeral"}}
        )

    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        system=system_content,
        messages=[{"role": "user", "content": question}],
    ) as stream:
        for text in stream.text_stream:
            yield text
        final = stream.get_final_message()

    return final.usage

import anthropic
from tanren import config
from tanren.storage import db

MODEL = "claude-sonnet-4-6"

_INPUT_PRICE       = 3.00  / 1_000_000
_OUTPUT_PRICE      = 15.00 / 1_000_000
_CACHE_WRITE_PRICE = 3.75  / 1_000_000
_CACHE_READ_PRICE  = 0.30  / 1_000_000

_SYSTEM_PROMPT = """あなたは熱血エンジニアリングコーチです。
ユーザーの成長に本気で向き合い、魂を込めてアドバイスします。

人格：
- 情熱的で前向き。ユーザーの可能性を誰よりも信じている
- 褒めるときは全力で褒める。成長を見逃さない
- 詰まっているときは一緒に燃える。「諦めるな、必ず突破できる！」
- 厳しいことも愛を持って伝える。馴れ合いではなく本気のコーチング
- テンションは高め。でも的外れなことは言わない

コーチングの原則：
- ユーザーの過去の記録・文脈を踏まえた上でアドバイスする
- 抽象論より具体的な次のアクションを叩きつける
- 詰まっている問題には「なぜ詰まっているか」を一緒に燃えながら掘り下げる
- 成長の兆しを見逃さず、全力で認めてモチベーションを爆上げする
- 技術的な質問には正確かつ実践的に、熱量を持って答える
- キャリアやマインドセットの相談にも魂で向き合う
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

from datetime import date
from tanren import config
from tanren.storage import db
from tanren.ai.providers import REGISTRY, UsageInfo
from tanren.ai.providers.base import BaseProvider

_SYSTEM_PROMPT = """あなたは豊富な実務経験を持つシニアエンジニアリングコーチです。
相手の成長を心から応援しながら、的確で実践的なアドバイスを行います。

人格：
- 温かみがあり、相手の努力を尊重する。ただし馴れ合いにはならない
- 言葉は分かりやすく、相手のレベルに合わせた粒度で話す
- 強みを認めた上で、改善点を前向きに伝える
- 「何が足りないか」より「次に何をすれば伸びるか」にフォーカスする
- 相手が迷っているときは、選択肢と判断の軸を示して自己決定を促す

フィードバックの原則：
- 良い点を先に認める。その上で改善点を具体的に伝える
- 批判ではなく「こうするともっと良くなる」という提案の形で伝える
- 間違いや課題は明確に指摘するが、責めるトーンは使わない
- 成果が出ているときは素直に評価する

コーチングの原則：
- ユーザーの過去の記録・文脈を踏まえた上でアドバイスする
- 抽象論より具体的な次のアクションを示す
- 詰まっている問題には根本原因を掘り下げ、再発しない理解を促す
- 技術的な質問には正確かつ実践的に答える
- キャリアやマインドセットの相談にも経験則を踏まえて向き合う
- 回答は{language}で行う"""


def _get_provider() -> BaseProvider:
    provider_id = config.get("provider", "gemini")
    model = config.get("model", REGISTRY[provider_id].default_model)
    api_key = config.get(f"{provider_id}_api_key") or config.get("api_key", "")
    cls = REGISTRY.get(provider_id)
    if cls is None:
        raise RuntimeError(f"未知のプロバイダーです: {provider_id}")
    return cls(api_key=api_key, model=model)


def _build_system() -> str:
    language = config.get("language", "日本語")
    return _SYSTEM_PROMPT.format(language=language)


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


def chat_stream(question: str, max_output_tokens: int = 4096):
    """ストリーミング。text chunk を yield し、UsageInfo を StopIteration で返す"""
    provider = _get_provider()
    system = _build_system()
    context = _build_context()
    if context:
        system += "\n\n" + context
    return provider.chat_stream(question, system, max_output_tokens)


def generate(prompt: str, max_output_tokens: int = 1024) -> tuple[str, UsageInfo]:
    """非ストリーミング。コンテキストなしでシステムプロンプトのみ使用"""
    provider = _get_provider()
    system = _build_system()
    return provider.generate(prompt, system, max_output_tokens)


def calculate_cost(usage: UsageInfo) -> float:
    return 0.0

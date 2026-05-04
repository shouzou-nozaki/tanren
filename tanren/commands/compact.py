from datetime import date, timedelta
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from tanren import config
from tanren.storage import db, budget

console = Console()

# 圧縮の境界日数
_WEEKLY_AFTER_DAYS = 30     # 30日以上前 → 週次サマリーへ
_MONTHLY_AFTER_DAYS = 180   # 180日以上前 → 月次サマリーへ
_YEARLY_AFTER_DAYS = 365    # 365日以上前 → 年次サマリーへ


def compact():
    """古いチェックインを段階的にサマリー化してDBを軽量に保つ"""
    today = date.today()
    conn = db.get_connection()

    weekly_count = _compact_to_weekly(conn, today)
    monthly_count = _compact_to_monthly(conn, today)
    yearly_count = _compact_to_yearly(conn, today)
    session_count = _compact_sessions(conn)

    conn.close()

    if weekly_count + monthly_count + yearly_count + session_count == 0:
        console.print("[dim]圧縮対象のデータはありませんでした[/dim]")
        return

    table = Table(title="コンパクト結果", show_header=False)
    table.add_column("種別", style="cyan")
    table.add_column("処理件数", justify="right")
    if weekly_count:
        table.add_row("週次サマリー化", f"{weekly_count} 件のチェックイン")
    if monthly_count:
        table.add_row("月次サマリー化", f"{monthly_count} 件の週次サマリー")
    if yearly_count:
        table.add_row("年次サマリー化", f"{yearly_count} 件の月次サマリー")
    if session_count:
        table.add_row("セッションサマリー化", f"{session_count} 件の過去のやり取り")
    console.print(table)


def _compact_to_weekly(conn, today: date) -> int:
    cutoff = (today - timedelta(days=_WEEKLY_AFTER_DAYS)).isoformat()
    rows = conn.execute(
        "SELECT * FROM checkins WHERE date < ? ORDER BY date ASC", (cutoff,)
    ).fetchall()

    if not rows:
        return 0

    # 週ごとにグループ化
    by_week: dict[str, list] = defaultdict(list)
    for r in rows:
        d = date.fromisoformat(r["date"])
        week_key = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
        by_week[week_key].append(r)

    count = 0
    with conn:
        for week_key, entries in by_week.items():
            # 既にサマリーがあればスキップ
            exists = conn.execute(
                "SELECT id FROM summaries WHERE type = 'weekly' AND period = ?", (week_key,)
            ).fetchone()
            if exists:
                continue

            avg_energy = sum(e["energy_level"] or 0 for e in entries) / len(entries)
            works = "・".join(e["work_summary"] for e in entries if e["work_summary"])
            learnings = "・".join(e["learnings"] for e in entries if e["learnings"])
            blockers = "・".join(e["blockers"] for e in entries if e["blockers"])

            content = (
                f"作業: {works}\n"
                f"学び: {learnings}\n"
                + (f"詰まり: {blockers}\n" if blockers else "")
                + f"平均エネルギー: {avg_energy:.1f}/5"
            )

            conn.execute(
                "INSERT INTO summaries (type, period, content, original_count) VALUES (?, ?, ?, ?)",
                ("weekly", week_key, content, len(entries)),
            )

            ids = tuple(e["id"] for e in entries)
            conn.execute(f"DELETE FROM checkins WHERE id IN ({','.join('?' * len(ids))})", ids)
            count += len(entries)

    return count


def _compact_to_monthly(conn, today: date) -> int:
    cutoff_month = _month_str(today - timedelta(days=_MONTHLY_AFTER_DAYS))
    rows = conn.execute(
        "SELECT * FROM summaries WHERE type = 'weekly' AND period < ? ORDER BY period ASC",
        (cutoff_month,),
    ).fetchall()

    if not rows:
        return 0

    # 月ごとにグループ化（週キー "2026-W01" の先頭6文字が年、W番号から月を推定）
    by_month: dict[str, list] = defaultdict(list)
    for r in rows:
        month_key = _week_to_month(r["period"])
        by_month[month_key].append(r)

    count = 0
    with conn:
        for month_key, entries in by_month.items():
            exists = conn.execute(
                "SELECT id FROM summaries WHERE type = 'monthly' AND period = ?", (month_key,)
            ).fetchone()
            if exists:
                continue

            total_orig = sum(e["original_count"] for e in entries)
            content = f"[{total_orig}件の記録]\n" + "\n---\n".join(e["content"] for e in entries)

            conn.execute(
                "INSERT INTO summaries (type, period, content, original_count) VALUES (?, ?, ?, ?)",
                ("monthly", month_key, content, total_orig),
            )

            ids = tuple(e["id"] for e in entries)
            conn.execute(f"DELETE FROM summaries WHERE id IN ({','.join('?' * len(ids))})", ids)
            count += len(entries)

    return count


def _compact_to_yearly(conn, today: date) -> int:
    cutoff_year = str(today.year - 1)
    rows = conn.execute(
        "SELECT * FROM summaries WHERE type = 'monthly' AND period < ? ORDER BY period ASC",
        (cutoff_year,),
    ).fetchall()

    if not rows:
        return 0

    by_year: dict[str, list] = defaultdict(list)
    for r in rows:
        year = r["period"][:4]
        by_year[year].append(r)

    count = 0
    with conn:
        for year, entries in by_year.items():
            exists = conn.execute(
                "SELECT id FROM summaries WHERE type = 'yearly' AND period = ?", (year,)
            ).fetchone()
            if exists:
                continue

            total_orig = sum(e["original_count"] for e in entries)
            content = f"[{total_orig}件の記録]\n" + "\n---\n".join(e["content"] for e in entries)

            conn.execute(
                "INSERT INTO summaries (type, period, content, original_count) VALUES (?, ?, ?, ?)",
                ("yearly", year, content, total_orig),
            )

            ids = tuple(e["id"] for e in entries)
            conn.execute(f"DELETE FROM summaries WHERE id IN ({','.join('?' * len(ids))})", ids)
            count += len(entries)

    return count


def compact_sessions_if_needed():
    """セッションが10件を超えていたら自動でサマリー化する"""
    conn = db.get_connection()
    count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    conn.close()
    if count <= 10:
        return
    conn = db.get_connection()
    try:
        n = _compact_sessions(conn)
        if n:
            console.print(f"[dim]過去のやり取り {n} 件を自動でサマリー化しました[/dim]")
    except Exception:
        pass
    finally:
        conn.close()


def _compact_sessions(conn) -> int:
    """直近10件を超えるセッションをAIでサマリー化する"""
    all_sessions = conn.execute(
        "SELECT id, prompt, response, created_at FROM sessions ORDER BY created_at DESC"
    ).fetchall()

    if len(all_sessions) <= 10:
        return 0

    to_compact = all_sessions[10:]  # 11件目以降（古い順）

    history_text = "\n---\n".join(
        f"[{s['created_at'][:10]}]\nQ: {s['prompt']}\nA: {s['response']}"
        for s in reversed(to_compact)
    )

    prompt = f"""以下のコーチングやり取り記録（{len(to_compact)}件）を、重要な学び・決定事項・繰り返しのテーマに絞って簡潔にサマリーしてください。
将来の会話でコーチが参照するための記録なので、具体的なトピック・結論・課題を残してください。

{history_text}"""

    from tanren.ai import client as ai_client

    summary_content, usage = ai_client.generate(prompt, max_output_tokens=1024)
    budget.record(usage)

    ids = tuple(s["id"] for s in to_compact)
    with conn:
        conn.execute(
            "DELETE FROM summaries WHERE type = 'session_summary'"
        )
        conn.execute(
            "INSERT INTO summaries (type, period, content, original_count) VALUES (?, ?, ?, ?)",
            ("session_summary", "all", summary_content, len(to_compact)),
        )
        conn.execute(f"DELETE FROM sessions WHERE id IN ({','.join('?' * len(ids))})", ids)

    tokens = getattr(usage, "total_token_count", 0)
    console.print(f"[dim]セッションサマリー生成トークン: {tokens}[/dim]")
    return len(to_compact)


def _month_str(d: date) -> str:
    return d.strftime("%Y-%m")


def _week_to_month(week_key: str) -> str:
    year, week = week_key.split("-W")
    d = date.fromisocalendar(int(year), int(week), 1)
    return d.strftime("%Y-%m")

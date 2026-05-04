import typer
from datetime import date, timedelta
from rich.console import Console
from rich.panel import Panel
from tanren import config
from tanren.ai import client
from tanren.storage import budget, db

console = Console()


def review(
    period: str = typer.Option("week", "--period", "-p", help="week / month"),
):
    """週次・月次の振り返りサマリーを生成する"""
    if not config.is_configured():
        console.print("[red]先に tanren setup を実行してください[/red]")
        return

    if not db.has_checkin_today():
        console.print("[yellow]⚠ 今日のチェックインがまだです。先に tanren checkin を実行することをおすすめします。[/yellow]")
        if not typer.confirm("このまま続けますか？", default=False):
            return

    today = date.today()
    if period == "week":
        since = today - timedelta(days=7)
        period_label = "週次"
    elif period == "month":
        since = today.replace(day=1)
        period_label = "月次"
    else:
        console.print("[red]period は week または month を指定してください[/red]")
        return

    conn = db.get_connection()
    checkins = conn.execute(
        """SELECT date, work_summary, learnings, blockers, energy_level
           FROM checkins WHERE date >= ? ORDER BY date ASC""",
        (since.isoformat(),),
    ).fetchall()
    goals = conn.execute(
        "SELECT title, category, status FROM goals WHERE status = 'active'"
    ).fetchall()
    conn.close()

    if not checkins:
        console.print(f"[yellow]{since} 以降のチェックインがありません[/yellow]")
        return

    checkin_text = "\n".join(
        f"[{c['date']}] エネルギー:{c['energy_level']}/5\n  作業: {c['work_summary']}\n  学び: {c['learnings']}"
        + (f"\n  詰まり: {c['blockers']}" if c["blockers"] else "")
        for c in checkins
    )

    goal_text = "\n".join(f"- [{g['category']}] {g['title']}" for g in goals) if goals else "なし"

    prompt = f"""以下の{period_label}チェックイン記録（{since} 〜 {today}、{len(checkins)}件）を振り返り、以下の観点でまとめてください。

## チェックイン記録
{checkin_text}

## 現在の目標
{goal_text}

---

以下の構成でサマリーを作成してください：

### 主な取り組みと成果
### 重要な学び
### 繰り返し出た詰まりポイント（あれば）
### エネルギートレンド
### 次の期間に向けた提案（具体的なアクション）
"""

    console.print(Panel(
        f"[bold cyan]{period_label}振り返り[/bold cyan]  [dim]{since} 〜 {today}  ({len(checkins)}件)[/dim]",
        expand=False,
    ))
    console.print()

    full_response = ""
    usage = None
    gen = client.chat_stream(prompt, max_output_tokens=2048)
    try:
        while True:
            chunk = next(gen)
            console.print(chunk, end="")
            full_response += chunk
    except StopIteration as e:
        usage = e.value
    except (RuntimeError, Exception) as e:
        console.print(f"\n[red]エラー: {e}[/red]")
        return

    console.print("\n")

    if usage:
        console.print(f"[dim]トークン使用: {usage.total_tokens}[/dim]")
        budget.record(usage)

        conn = db.get_connection()
        with conn:
            conn.execute(
                """INSERT INTO sessions (command, prompt, response, input_tokens, output_tokens, cached_tokens, cost_usd)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"review_{period}",
                    prompt,
                    full_response,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.cached_tokens,
                    0.0,
                ),
            )
        conn.close()

from rich.console import Console
from rich.panel import Panel
from tanren import config
from tanren.ai import client
from tanren.storage import budget, db

console = Console()


def ask(question: str):
    """コーチに質問する（過去の記録が文脈として使われる）"""
    if not config.is_configured():
        console.print("[red]先に tanren setup を実行してください[/red]")
        return

    status = budget.check()
    if status == "blocked":
        console.print("[red]今月の予算上限に達しました。tanren budget status で確認してください。[/red]")
        return
    if status == "warning":
        usage = budget.get_usage()
        spent_yen = usage["cost_usd"] * config.get("usd_to_jpy", 150)
        limit_yen = config.get("budget_limit_yen", 300)
        console.print(f"[yellow]⚠ 予算警告: 今月 ¥{spent_yen:.0f} / ¥{limit_yen}[/yellow]")

    console.print(Panel(f"[dim]{question}[/dim]", title="[cyan]質問[/cyan]", expand=False))
    console.print("\n[cyan bold]コーチ:[/cyan bold]\n")

    full_response = ""
    usage = None

    gen = client.chat_stream(question)
    try:
        while True:
            chunk = next(gen)
            console.print(chunk, end="")
            full_response += chunk
    except StopIteration as e:
        usage = e.value

    console.print("\n")

    if usage:
        cost_usd = client.calculate_cost(usage)
        cost_yen = cost_usd * config.get("usd_to_jpy", 150)
        console.print(f"[dim]今回のコスト: ¥{cost_yen:.2f}[/dim]")

        budget.record(usage, cost_usd)

        conn = db.get_connection()
        with conn:
            conn.execute(
                """INSERT INTO sessions (command, prompt, response, input_tokens, output_tokens, cached_tokens, cost_usd)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    "ask",
                    question,
                    full_response,
                    getattr(usage, "input_tokens", 0),
                    getattr(usage, "output_tokens", 0),
                    getattr(usage, "cache_read_input_tokens", 0),
                    cost_usd,
                ),
            )
        conn.close()

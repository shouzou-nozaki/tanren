import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from tanren import config
from tanren.storage import db

console = Console()


def history(
    n: int = typer.Option(10, "--num", "-n", help="表示件数"),
    session_id: int = typer.Option(None, "--id", "-i", help="指定IDの内容を全文表示"),
):
    """過去のコーチとのやり取りを確認する"""
    conn = db.get_connection()

    if session_id is not None:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        conn.close()
        if not row:
            console.print(f"[red]ID {session_id} のセッションが見つかりません[/red]")
            return
        console.print(Panel(row["prompt"], title=f"[cyan]質問 (#{row['id']} / {row['created_at'][:10]})[/cyan]"))
        console.print()
        console.print(Panel(Markdown(row["response"]), title="[cyan]コーチの回答[/cyan]"))
        usd_to_jpy = config.get("usd_to_jpy", 150)
        console.print(f"\n[dim]コスト: ¥{row['cost_usd'] * usd_to_jpy:.2f}[/dim]")
        return

    rows = conn.execute(
        "SELECT id, command, prompt, created_at FROM sessions ORDER BY created_at DESC LIMIT ?",
        (n,),
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[dim]履歴がありません[/dim]")
        return

    table = Table(title=f"コーチング履歴（直近{n}件）")
    table.add_column("ID", style="dim", width=5)
    table.add_column("日時", width=12)
    table.add_column("コマンド", width=10)
    table.add_column("内容（先頭50字）")

    for r in rows:
        preview = r["prompt"].replace("\n", " ")[:50]
        if len(r["prompt"]) > 50:
            preview += "…"
        table.add_row(str(r["id"]), r["created_at"][:10], r["command"], preview)

    console.print(table)
    console.print("[dim]全文を見るには: tanren history --id <ID>[/dim]")

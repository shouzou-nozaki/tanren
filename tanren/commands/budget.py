import typer
from rich.console import Console
from rich.table import Table
from tanren.storage import budget as budget_store

app = typer.Typer(help="API使用量の確認")
console = Console()


@app.command("status")
def status():
    """今月のトークン使用量を表示する"""
    usage = budget_store.get_usage()

    table = Table(title=f"今月の使用状況 ({usage['year_month']})")
    table.add_column("項目", style="cyan")
    table.add_column("値", justify="right")

    table.add_row("入力トークン", str(usage["input_tokens"]))
    table.add_row("出力トークン", str(usage["output_tokens"]))
    table.add_row("キャッシュトークン", str(usage["cached_tokens"]))

    console.print(table)

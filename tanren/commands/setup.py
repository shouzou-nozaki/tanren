import typer
from rich.console import Console
from rich.panel import Panel
from tanren import config
from tanren.storage import db

console = Console()

def setup():
    """初回セットアップ（APIキーの設定）"""
    console.print(Panel("[bold cyan]tanren セットアップ[/bold cyan]", expand=False))

    console.print("\n[yellow]Gemini APIキーを入力してください[/yellow]")
    console.print("[dim]aistudio.google.com で無料取得できます[/dim]")
    api_key = typer.prompt("APIキー", hide_input=True)

    cfg = config.load()
    cfg["api_key"] = api_key
    config.save(cfg)

    db.init_db()

    console.print(f"\n[green]✓ セットアップ完了[/green]")
    console.print("\n[dim]tanren checkin で今日の記録を始めましょう[/dim]")

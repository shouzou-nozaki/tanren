import typer
from rich.console import Console
from rich.panel import Panel
from tanren import config
from tanren.storage import db

console = Console()

def setup():
    """初回セットアップ（APIキー・予算上限の設定）"""
    console.print(Panel("[bold cyan]tanren セットアップ[/bold cyan]", expand=False))

    console.print("\n[yellow]Anthropic APIキーを入力してください[/yellow]")
    console.print("[dim]console.anthropic.com で取得できます[/dim]")
    api_key = typer.prompt("APIキー", hide_input=True)

    console.print("\n[yellow]月の予算上限を設定してください（円）[/yellow]")
    budget = typer.prompt("予算上限", default="300")
    budget = int(budget)

    cfg = config.load()
    cfg["api_key"] = api_key
    cfg["budget_limit_yen"] = budget
    cfg["warning_threshold"] = 0.8
    cfg["usd_to_jpy"] = 150
    config.save(cfg)

    db.init_db()

    warn_yen = int(budget * 0.8)
    console.print(f"\n[green]✓ セットアップ完了[/green]")
    console.print(f"  予算上限: {budget}円/月")
    console.print(f"  警告ライン: {warn_yen}円 / ブロック: {budget}円")
    console.print("\n[dim]tanren checkin で今日の記録を始めましょう[/dim]")

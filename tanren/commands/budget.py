import typer
from rich.console import Console
from rich.table import Table
from tanren import config
from tanren.storage import budget as budget_store

app = typer.Typer(help="予算・使用量の管理")
console = Console()


@app.command("status")
def status():
    """今月のAPI使用量と残予算を表示する"""
    usage = budget_store.get_usage()
    limit_yen = config.get("budget_limit_yen", 300)
    usd_to_jpy = config.get("usd_to_jpy", 150)
    threshold = config.get("warning_threshold", 0.8)

    cost_usd = usage["cost_usd"]
    cost_yen = cost_usd * usd_to_jpy
    limit_usd = limit_yen / usd_to_jpy
    remaining_yen = limit_yen - cost_yen
    percent = (cost_usd / limit_usd * 100) if limit_usd > 0 else 0

    if percent >= 100:
        color = "red"
    elif percent >= threshold * 100:
        color = "yellow"
    else:
        color = "green"

    table = Table(title=f"今月の使用状況 ({usage['year_month']})")
    table.add_column("項目", style="cyan")
    table.add_column("値", justify="right")

    table.add_row("使用額", f"[{color}]¥{cost_yen:.1f}[/{color}]")
    table.add_row("残り予算", f"¥{remaining_yen:.1f}")
    table.add_row("予算上限", f"¥{limit_yen}")
    table.add_row("使用率", f"[{color}]{percent:.1f}%[/{color}]")
    table.add_row("入力トークン", str(usage["input_tokens"]))
    table.add_row("出力トークン", str(usage["output_tokens"]))
    table.add_row("キャッシュヒット", str(usage["cached_tokens"]))

    console.print(table)


@app.command("set")
def set_budget(limit: int = typer.Argument(..., help="月の予算上限（円）")):
    """月の予算上限を変更する"""
    config.set_value("budget_limit_yen", limit)
    warn_yen = int(limit * config.get("warning_threshold", 0.8))
    console.print(f"[green]✓ 予算上限を ¥{limit}/月 に設定しました[/green]")
    console.print(f"  警告ライン: ¥{warn_yen} / ブロック: ¥{limit}")

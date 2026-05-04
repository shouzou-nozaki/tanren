from datetime import date
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from tanren.storage import db

console = Console()

_ENERGY_LABELS = {1: "消耗", 2: "低め", 3: "普通", 4: "良好", 5: "絶好調"}

def checkin():
    """今日の作業・学び・詰まったことを記録する"""
    today = date.today()
    console.print(Panel(
        f"[bold cyan]今日のチェックイン[/bold cyan]  [dim]{today}[/dim]",
        expand=False,
    ))

    work = Prompt.ask("\n[yellow]今日やったこと[/yellow]")
    learnings = Prompt.ask("[yellow]学んだこと[/yellow]")
    blockers = Prompt.ask("[yellow]詰まったこと[/yellow] [dim](なければEnter)[/dim]", default="")
    energy = IntPrompt.ask(
        "[yellow]エネルギーレベル[/yellow] [dim]1=消耗 2=低め 3=普通 4=良好 5=絶好調[/dim]",
    )
    while energy not in range(1, 6):
        console.print("[red]1〜5 で入力してください[/red]")
        energy = IntPrompt.ask("[yellow]エネルギーレベル[/yellow]")

    conn = db.get_connection()
    with conn:
        conn.execute(
            """INSERT INTO checkins (date, work_summary, learnings, blockers, energy_level)
               VALUES (?, ?, ?, ?, ?)""",
            (today.isoformat(), work, learnings, blockers or None, energy),
        )
    conn.close()

    console.print(f"\n[green]✓ 記録しました[/green]  エネルギー: {_ENERGY_LABELS[energy]}")

    from tanren.commands.skills import assess_skills_if_needed
    assess_skills_if_needed()

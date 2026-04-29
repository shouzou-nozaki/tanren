import typer
from datetime import date
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from tanren.storage import db

app = typer.Typer(help="目標の管理")
console = Console()

_CATEGORIES = ["technical", "career", "mindset"]
_STATUSES = ["active", "completed", "paused"]


@app.command("add")
def add():
    """目標を追加する"""
    title = Prompt.ask("[yellow]目標のタイトル[/yellow]")
    description = Prompt.ask("[yellow]詳細[/yellow] [dim](なければEnter)[/dim]", default="")

    console.print(f"[yellow]カテゴリ[/yellow] [dim]{' / '.join(_CATEGORIES)}[/dim]")
    category = Prompt.ask("", default="technical")
    while category not in _CATEGORIES:
        console.print(f"[red]{'/'.join(_CATEGORIES)} のいずれかを入力してください[/red]")
        category = Prompt.ask("カテゴリ", default="technical")

    target_date = Prompt.ask("[yellow]期限[/yellow] [dim](YYYY-MM-DD, なければEnter)[/dim]", default="")

    conn = db.get_connection()
    with conn:
        conn.execute(
            """INSERT INTO goals (title, description, category, target_date)
               VALUES (?, ?, ?, ?)""",
            (title, description or None, category, target_date or None),
        )
    conn.close()

    console.print(f"\n[green]✓ 目標を追加しました:[/green] {title}")


@app.command("list")
def list_goals(
    status: str = typer.Option("active", "--status", "-s", help="active / completed / paused / all"),
):
    """目標一覧を表示する"""
    conn = db.get_connection()
    if status == "all":
        rows = conn.execute("SELECT * FROM goals ORDER BY created_at DESC").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM goals WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    conn.close()

    if not rows:
        console.print("[dim]目標はありません[/dim]")
        return

    table = Table(title=f"目標一覧 [{status}]")
    table.add_column("ID", style="dim", width=4)
    table.add_column("タイトル")
    table.add_column("カテゴリ", width=10)
    table.add_column("期限", width=12)
    table.add_column("ステータス", width=10)

    status_colors = {"active": "green", "completed": "blue", "paused": "yellow"}
    for r in rows:
        color = status_colors.get(r["status"], "white")
        table.add_row(
            str(r["id"]),
            r["title"],
            r["category"],
            r["target_date"] or "-",
            f"[{color}]{r['status']}[/{color}]",
        )

    console.print(table)


@app.command("update")
def update(goal_id: int = typer.Argument(..., help="目標のID（tanren goal list で確認）")):
    """目標の内容・ステータスを更新する"""
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not row:
        console.print(f"[red]ID {goal_id} の目標が見つかりません[/red]")
        conn.close()
        return

    console.print(f"[cyan]{row['title']}[/cyan] を更新します [dim](Enterで変更なし)[/dim]\n")

    new_title = Prompt.ask("[yellow]タイトル[/yellow]", default=row["title"])
    new_desc = Prompt.ask("[yellow]詳細[/yellow]", default=row["description"] or "")

    console.print(f"[yellow]カテゴリ[/yellow] [dim]{' / '.join(_CATEGORIES)}[/dim]")
    new_category = Prompt.ask("", default=row["category"])
    while new_category not in _CATEGORIES:
        console.print(f"[red]{'/'.join(_CATEGORIES)} のいずれかを入力してください[/red]")
        new_category = Prompt.ask("カテゴリ", default=row["category"])

    new_target = Prompt.ask("[yellow]期限[/yellow] [dim](YYYY-MM-DD)[/dim]", default=row["target_date"] or "")

    console.print(f"[yellow]ステータス[/yellow] [dim]{' / '.join(_STATUSES)}[/dim]")
    new_status = Prompt.ask("", default=row["status"])
    while new_status not in _STATUSES:
        console.print(f"[red]{'/'.join(_STATUSES)} のいずれかを入力してください[/red]")
        new_status = Prompt.ask("ステータス", default=row["status"])

    note = Prompt.ask("[yellow]進捗メモ[/yellow] [dim](なければEnter)[/dim]", default="")

    with conn:
        conn.execute(
            """UPDATE goals SET title = ?, description = ?, category = ?, target_date = ?,
               status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (new_title, new_desc or None, new_category, new_target or None, new_status, goal_id),
        )
        if note:
            conn.execute("INSERT INTO goal_notes (goal_id, note) VALUES (?, ?)", (goal_id, note))
    conn.close()

    console.print(f"[green]✓ 更新しました[/green]")


@app.command("delete")
def delete(goal_id: int = typer.Argument(..., help="目標のID（tanren goal list で確認）")):
    """目標を削除する"""
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not row:
        console.print(f"[red]ID {goal_id} の目標が見つかりません[/red]")
        conn.close()
        return

    console.print(f"[cyan]{row['title']}[/cyan] を削除しますか？ [dim](y/N)[/dim]", end=" ")
    confirm = Prompt.ask("", default="N")
    if confirm.lower() != "y":
        console.print("[dim]キャンセルしました[/dim]")
        conn.close()
        return

    with conn:
        conn.execute("DELETE FROM goal_notes WHERE goal_id = ?", (goal_id,))
        conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    conn.close()

    console.print(f"[green]✓ 削除しました[/green]")

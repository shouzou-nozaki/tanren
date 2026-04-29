import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from tanren.storage import db

console = Console()

_CATEGORIES = ["language", "framework", "infrastructure", "database", "soft", "other"]


def skills(
    action: str = typer.Argument("list", help="list / add / update / delete"),
    name: str = typer.Argument(None, help="スキル名（update / delete 時）"),
):
    """スキルマップの表示・更新"""
    if action == "list":
        _list_skills()
    elif action == "add":
        _add_skill()
    elif action == "update":
        if not name:
            _list_skills()
            name = Prompt.ask("\n[yellow]更新するスキル名を入力[/yellow]")
        _update_skill(name)
    elif action == "delete":
        if not name:
            _list_skills()
            name = Prompt.ask("\n[yellow]削除するスキル名を入力[/yellow]")
        _delete_skill(name)
    else:
        console.print(f"[red]不明なアクション: {action}[/red]  list / add / update / delete のいずれかを指定してください")


def _list_skills():
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM skills ORDER BY category, level DESC"
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[dim]スキルが登録されていません。tanren skills add で追加してください。[/dim]")
        return

    table = Table(title="スキルマップ")
    table.add_column("スキル名")
    table.add_column("カテゴリ", width=14)
    table.add_column("レベル", width=10)
    table.add_column("メモ")

    for r in rows:
        level = r["level"] or 0
        bar = "█" * level + "░" * (5 - level)
        table.add_row(r["name"], r["category"] or "-", f"{bar} {level}/5", r["notes"] or "")

    console.print(table)


def _add_skill():
    name = Prompt.ask("[yellow]スキル名[/yellow]")

    console.print(f"[yellow]カテゴリ[/yellow] [dim]{' / '.join(_CATEGORIES)}[/dim]")
    category = Prompt.ask("", default="other")

    level = IntPrompt.ask("[yellow]現在のレベル[/yellow] [dim](1=入門 〜 5=エキスパート)[/dim]")
    while level not in range(1, 6):
        console.print("[red]1〜5 で入力してください[/red]")
        level = IntPrompt.ask("[yellow]レベル[/yellow]")

    notes = Prompt.ask("[yellow]メモ[/yellow] [dim](なければEnter)[/dim]", default="")

    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO skills (name, category, level, notes) VALUES (?, ?, ?, ?)",
            (name, category, level, notes or None),
        )
    conn.close()

    console.print(f"[green]✓ {name} を追加しました (Lv.{level})[/green]")


def _update_skill(name: str):
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM skills WHERE name = ?", (name,)).fetchone()
    if not row:
        # 名前が一致しない場合、部分一致で候補を表示
        candidates = conn.execute(
            "SELECT name FROM skills WHERE name LIKE ?", (f"%{name}%",)
        ).fetchall()
        conn.close()
        if candidates:
            console.print(f"[red]'{name}' が見つかりません。候補:[/red]")
            for c in candidates:
                console.print(f"  - {c['name']}")
        else:
            console.print(f"[red]'{name}' が見つかりません。tanren skills で一覧を確認してください。[/red]")
        return

    console.print(f"[cyan]{name}[/cyan] を更新します")
    console.print(f"  現在: カテゴリ={row['category']}  Lv.{row['level']}")

    console.print(f"\n[yellow]カテゴリ[/yellow] [dim]{' / '.join(_CATEGORIES)}[/dim]")
    new_category = Prompt.ask("", default=row["category"] or "other")
    while new_category not in _CATEGORIES:
        console.print(f"[red]{'/'.join(_CATEGORIES)} のいずれかを入力してください[/red]")
        new_category = Prompt.ask("カテゴリ", default=row["category"] or "other")

    new_level = IntPrompt.ask("[yellow]新しいレベル[/yellow] [dim](1〜5, Enterで変更なし)[/dim]", default=row["level"])
    while new_level not in range(1, 6):
        console.print("[red]1〜5 で入力してください[/red]")
        new_level = IntPrompt.ask("[yellow]レベル[/yellow]")

    notes = Prompt.ask("[yellow]メモ[/yellow] [dim](なければEnter)[/dim]", default=row["notes"] or "")

    with conn:
        conn.execute(
            "INSERT INTO skill_history (skill_id, level, notes) VALUES (?, ?, ?)",
            (row["id"], row["level"], row["notes"]),
        )
        conn.execute(
            "UPDATE skills SET category = ?, level = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_category, new_level, notes or None, row["id"]),
        )
    conn.close()

    arrow = "↑" if new_level > row["level"] else ("↓" if new_level < row["level"] else "→")
    console.print(f"[green]✓ {name}: Lv.{row['level']} {arrow} Lv.{new_level}  カテゴリ: {new_category}[/green]")


def _delete_skill(name: str):
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM skills WHERE name = ?", (name,)).fetchone()
    if not row:
        candidates = conn.execute(
            "SELECT name FROM skills WHERE name LIKE ?", (f"%{name}%",)
        ).fetchall()
        conn.close()
        if candidates:
            console.print(f"[red]'{name}' が見つかりません。候補:[/red]")
            for c in candidates:
                console.print(f"  - {c['name']}")
        else:
            console.print(f"[red]'{name}' が見つかりません。[/red]")
        return

    confirm = Prompt.ask(f"[red]{name}[/red] を削除しますか？ [dim](y/N)[/dim]", default="N")
    if confirm.lower() != "y":
        console.print("[dim]キャンセルしました[/dim]")
        conn.close()
        return

    with conn:
        conn.execute("DELETE FROM skill_history WHERE skill_id = ?", (row["id"],))
        conn.execute("DELETE FROM skills WHERE id = ?", (row["id"],))
    conn.close()

    console.print(f"[green]✓ {name} を削除しました[/green]")

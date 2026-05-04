import typer
from datetime import date, timedelta
from collections import Counter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from tanren import config
from tanren.ai import client
from tanren.storage import budget, db

console = Console()


def report():
    """成長レポートを生成する"""
    if not config.is_configured():
        console.print("[red]先に tanren setup を実行してください[/red]")
        return

    if not db.has_checkin_today():
        console.print("[yellow]⚠ 今日のチェックインがまだです。先に tanren checkin を実行することをおすすめします。[/yellow]")
        if not typer.confirm("このまま続けますか？", default=False):
            return

    conn = db.get_connection()

    checkins = conn.execute(
        "SELECT date, energy_level, learnings, blockers FROM checkins ORDER BY date ASC"
    ).fetchall()
    goals_all = conn.execute("SELECT * FROM goals ORDER BY created_at ASC").fetchall()
    skills = conn.execute(
        "SELECT name, category, level FROM skills ORDER BY category, level DESC"
    ).fetchall()
    skill_history = conn.execute(
        """SELECT s.name, sh.level, sh.recorded_at
           FROM skill_history sh JOIN skills s ON sh.skill_id = s.id
           ORDER BY sh.recorded_at ASC"""
    ).fetchall()
    conn.close()

    console.print(Panel("[bold cyan]成長レポート[/bold cyan]", expand=False))
    console.print()

    # ── チェックイン統計 ──
    _print_checkin_stats(checkins)

    # ── スキルマップ ──
    _print_skill_map(skills, skill_history)

    # ── 目標サマリー ──
    _print_goal_summary(goals_all)

    # ── AI による総合コメント ──
    if checkins:
        _print_ai_insight(checkins, skills, goals_all)


def _print_checkin_stats(checkins):
    if not checkins:
        return

    total = len(checkins)
    avg_energy = sum(c["energy_level"] or 0 for c in checkins) / total
    last_30 = [c for c in checkins if c["date"] >= (date.today() - timedelta(days=30)).isoformat()]
    blocker_count = sum(1 for c in checkins if c["blockers"])

    # 直近30日のエネルギー推移（簡易グラフ）
    energy_bar = ""
    for c in last_30[-20:]:
        e = c["energy_level"] or 0
        colors = {1: "red", 2: "yellow", 3: "white", 4: "cyan", 5: "green"}
        energy_bar += f"[{colors.get(e, 'white')}]{'█' * e}{'░' * (5-e)}[/{colors.get(e, 'white')}] "

    table = Table(title="チェックイン統計", show_header=False)
    table.add_column("項目", style="cyan")
    table.add_column("値")
    table.add_row("総記録日数", f"{total} 日")
    table.add_row("平均エネルギー", f"{avg_energy:.1f} / 5")
    table.add_row("詰まり記録", f"{blocker_count} 件")
    table.add_row("直近30日", f"{len(last_30)} 件")
    console.print(table)

    if last_30:
        console.print(f"\n[dim]直近エネルギー推移（左が古い）[/dim]")
        console.print(energy_bar)
    console.print()


def _print_skill_map(skills, history):
    if not skills:
        return

    table = Table(title="スキルマップ")
    table.add_column("スキル名")
    table.add_column("カテゴリ", width=14)
    table.add_column("レベル", width=12)
    table.add_column("成長履歴")

    growth_map: dict[str, list] = {}
    for h in history:
        growth_map.setdefault(h["name"], []).append(h["level"])

    for s in skills:
        level = s["level"] or 0
        bar = "█" * level + "░" * (5 - level)
        past = growth_map.get(s["name"], [])
        if past:
            growth = " → ".join(str(l) for l in past[-3:]) + f" → {level}"
        else:
            growth = f"{level}"
        table.add_row(s["name"], s["category"] or "-", f"{bar} {level}/5", growth)

    console.print(table)
    console.print()


def _print_goal_summary(goals):
    if not goals:
        return

    counts = Counter(g["status"] for g in goals)
    table = Table(title="目標サマリー", show_header=False)
    table.add_column("ステータス", style="cyan")
    table.add_column("件数", justify="right")
    for status, label, color in [
        ("active", "進行中", "green"),
        ("completed", "完了", "blue"),
        ("paused", "一時停止", "yellow"),
    ]:
        if counts.get(status):
            table.add_row(f"[{color}]{label}[/{color}]", str(counts[status]))

    console.print(table)
    console.print()



def _print_ai_insight(checkins, skills, goals):
    checkin_summary = "\n".join(
        f"[{c['date']}] エネルギー:{c['energy_level']}/5  学び:{c['learnings']}"
        + (f"  詰まり:{c['blockers']}" if c["blockers"] else "")
        for c in checkins[-20:]
    )
    skill_summary = "\n".join(f"- {s['name']} Lv.{s['level']}" for s in skills)
    goal_summary = "\n".join(f"- [{g['status']}] {g['title']}" for g in goals)

    prompt = f"""以下はエンジニアの成長記録です。全体を通じた洞察とアドバイスを200字程度で端的にまとめてください。

【直近のチェックイン（最新20件）】
{checkin_summary}

【スキルマップ】
{skill_summary}

【目標】
{goal_summary}

総合的なコメントと、今後注力すべき点を具体的に伝えてください。"""

    console.print("[cyan bold]AIコーチからの総評:[/cyan bold]\n")

    full_response = ""
    usage = None
    gen = client.chat_stream(prompt)
    try:
        while True:
            chunk = next(gen)
            console.print(chunk, end="")
            full_response += chunk
    except StopIteration as e:
        usage = e.value
    except RuntimeError as e:
        console.print(f"\n[red]エラー: {e}[/red]")
        return

    console.print("\n")

    if usage:
        console.print(f"[dim]トークン使用: {usage.total_tokens}[/dim]")
        budget.record(usage)

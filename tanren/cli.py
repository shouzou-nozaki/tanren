import sys
import readline  # noqa: F401 — enables arrow keys and line editing in input()
import typer
from tanren.commands import checkin, ask, review, skills, report, setup, compact, history
from tanren.commands import goal, budget

# WSL環境での日本語入力エンコーディング問題を修正
for _s in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(
    name="tanren",
    help="エンジニアリングコーチ CLI — 毎日の鍛錬を記録し、成長を導く",
    no_args_is_help=True,
)

app.add_typer(goal.app, name="goal")
app.add_typer(budget.app, name="budget")

app.command()(setup.setup)
app.command()(checkin.checkin)
app.command()(review.review)
app.command()(skills.skills)
app.command()(report.report)
app.command()(compact.compact)
app.command()(history.history)

@app.command()
def ask(question: str = typer.Argument(None, help="コーチへの質問（省略すると対話入力モード）")):
    """コーチに質問する（過去の記録が文脈として使われる）"""
    from tanren.commands.ask import ask as _ask
    _ask(question)

if __name__ == "__main__":
    app()

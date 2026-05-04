import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import IntPrompt, Prompt
from tanren import config
from tanren.ai.providers import REGISTRY, PROVIDER_LIST

app = typer.Typer(help="プロバイダー・モデル・言語などの設定変更")
console = Console()

AVAILABLE_LANGUAGES: list[tuple[str, str]] = [
    ("日本語", "日本語"),
    ("English", "English"),
    ("中文",   "中文（简体）"),
    ("한국어",  "한국어"),
]


@app.command("show")
def show():
    """現在の設定を表示する"""
    provider_id = config.get("provider", "gemini")
    provider_cls = REGISTRY.get(provider_id)
    table = Table(title="現在の設定", show_header=False)
    table.add_column("項目", style="cyan")
    table.add_column("値")
    table.add_row("プロバイダー", provider_cls.display_name if provider_cls else provider_id)
    table.add_row("モデル",       config.get("model", "（未設定）"))
    table.add_row("応答言語",     config.get("language", "日本語"))
    table.add_row("GitHub",       config.get("github_username", "（未設定）"))
    console.print(table)


@app.command("provider")
def set_provider():
    """使用するAIプロバイダーを変更する"""
    current = config.get("provider", "gemini")
    console.print("\n[yellow]プロバイダーを選択してください:[/yellow]")
    for i, (pid, label) in enumerate(PROVIDER_LIST, 1):
        marker = " [green]←現在[/green]" if pid == current else ""
        console.print(f"  {i}. {label}{marker}")
    idx = IntPrompt.ask("番号", default=next(
        (i for i, (p, _) in enumerate(PROVIDER_LIST, 1) if p == current), 1
    ))
    idx = max(1, min(idx, len(PROVIDER_LIST)))
    provider_id, _ = PROVIDER_LIST[idx - 1]

    # そのプロバイダーのAPIキーがなければ入力を求める
    if not config.get(f"{provider_id}_api_key"):
        key_hints = {
            "gemini": "aistudio.google.com で無料取得できます",
            "claude": "console.anthropic.com で取得できます（有料）",
        }
        console.print(f"\n[yellow]{REGISTRY[provider_id].display_name} のAPIキーを入力してください[/yellow]")
        console.print(f"[dim]{key_hints.get(provider_id, '')}[/dim]")
        api_key = typer.prompt("APIキー", hide_input=True)
        config.set_value(f"{provider_id}_api_key", api_key)

    # デフォルトモデルに切り替え
    default_model = REGISTRY[provider_id].default_model
    config.set_value("provider", provider_id)
    config.set_value("model", default_model)

    console.print(f"\n[green]✓ プロバイダーを {REGISTRY[provider_id].display_name} に変更しました[/green]")
    console.print(f"  モデル: {default_model}（デフォルト）")
    console.print("  [dim]tanren config model でモデルを変更できます[/dim]")


@app.command("model")
def set_model():
    """使用するモデルを変更する"""
    provider_id = config.get("provider", "gemini")
    current = config.get("model", "")
    models = REGISTRY[provider_id].models

    console.print(f"\n[yellow]モデルを選択してください（{REGISTRY[provider_id].display_name}）:[/yellow]")
    for i, (mid, desc) in enumerate(models, 1):
        marker = " [green]←現在[/green]" if mid == current else ""
        console.print(f"  {i}. {desc}{marker}")
    idx = IntPrompt.ask("番号", default=next(
        (i for i, (m, _) in enumerate(models, 1) if m == current), 1
    ))
    idx = max(1, min(idx, len(models)))
    model_id, _ = models[idx - 1]
    config.set_value("model", model_id)
    console.print(f"\n[green]✓ モデルを {model_id} に変更しました[/green]")


@app.command("language")
def set_language():
    """応答言語を変更する"""
    current = config.get("language", "日本語")
    console.print("\n[yellow]応答言語を選択してください:[/yellow]")
    for i, (lang, label) in enumerate(AVAILABLE_LANGUAGES, 1):
        marker = " [green]←現在[/green]" if lang == current else ""
        console.print(f"  {i}. {label}{marker}")
    idx = IntPrompt.ask("番号", default=next(
        (i for i, (l, _) in enumerate(AVAILABLE_LANGUAGES, 1) if l == current), 1
    ))
    idx = max(1, min(idx, len(AVAILABLE_LANGUAGES)))
    language, _ = AVAILABLE_LANGUAGES[idx - 1]
    config.set_value("language", language)
    console.print(f"\n[green]✓ 応答言語を {language} に変更しました[/green]")


@app.command("github")
def set_github():
    """GitHubユーザー名を設定する（スキル査定の精度向上）"""
    current = config.get("github_username", "")
    if current:
        console.print(f"\n現在の設定: [cyan]{current}[/cyan]")
    username = Prompt.ask("\n[yellow]GitHubユーザー名[/yellow]", default=current)
    if username:
        config.set_value("github_username", username)
        console.print(f"\n[green]✓ GitHubユーザー名を {username} に設定しました[/green]")
    else:
        console.print("[dim]変更なし[/dim]")


@app.command("api-key")
def set_api_key():
    """現在のプロバイダーのAPIキーを更新する"""
    provider_id = config.get("provider", "gemini")
    console.print(f"\n[yellow]{REGISTRY[provider_id].display_name} のAPIキーを入力してください:[/yellow]")
    api_key = typer.prompt("APIキー", hide_input=True)
    config.set_value(f"{provider_id}_api_key", api_key)
    console.print(f"\n[green]✓ APIキーを更新しました[/green]")

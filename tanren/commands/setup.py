import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from tanren import config
from tanren.storage import db
from tanren.ai.providers import REGISTRY, PROVIDER_LIST

console = Console()


def setup():
    """初回セットアップ（プロバイダー・APIキー・言語の設定）"""
    console.print(Panel("[bold cyan]tanren セットアップ[/bold cyan]", expand=False))

    # プロバイダー選択
    console.print("\n[yellow]使用するAIプロバイダーを選択してください:[/yellow]")
    for i, (_, label) in enumerate(PROVIDER_LIST, 1):
        console.print(f"  {i}. {label}")
    provider_idx = IntPrompt.ask("番号", default=1)
    provider_idx = max(1, min(provider_idx, len(PROVIDER_LIST)))
    provider_id, _ = PROVIDER_LIST[provider_idx - 1]

    # APIキー入力
    key_hints = {
        "gemini": "aistudio.google.com で無料取得できます",
        "claude": "console.anthropic.com で取得できます（有料）",
    }
    console.print(f"\n[yellow]{REGISTRY[provider_id].display_name} のAPIキーを入力してください[/yellow]")
    console.print(f"[dim]{key_hints.get(provider_id, '')}[/dim]")
    api_key = typer.prompt("APIキー", hide_input=True)

    # モデル選択
    models = REGISTRY[provider_id].models
    console.print("\n[yellow]使用するモデルを選択してください:[/yellow]")
    for i, (_, desc) in enumerate(models, 1):
        console.print(f"  {i}. {desc}")
    model_idx = IntPrompt.ask("番号", default=1)
    model_idx = max(1, min(model_idx, len(models)))
    model_id, _ = models[model_idx - 1]

    # 言語選択
    from tanren.commands.config_cmd import AVAILABLE_LANGUAGES
    console.print("\n[yellow]応答言語を選択してください:[/yellow]")
    for i, (_, label) in enumerate(AVAILABLE_LANGUAGES, 1):
        console.print(f"  {i}. {label}")
    lang_idx = IntPrompt.ask("番号", default=1)
    lang_idx = max(1, min(lang_idx, len(AVAILABLE_LANGUAGES)))
    language, _ = AVAILABLE_LANGUAGES[lang_idx - 1]

    # GitHubユーザー名（任意）
    console.print("\n[yellow]GitHubユーザー名を入力してください[/yellow] [dim](スキル査定の精度が上がります。スキップはEnter)[/dim]")
    github_username = Prompt.ask("GitHubユーザー名", default="")

    # 保存
    cfg = config.load()
    cfg["provider"] = provider_id
    cfg[f"{provider_id}_api_key"] = api_key
    cfg["model"] = model_id
    cfg["language"] = language
    if github_username:
        cfg["github_username"] = github_username
    config.save(cfg)

    db.init_db()

    console.print(f"\n[green]✓ セットアップ完了[/green]")
    console.print(f"  プロバイダー: {REGISTRY[provider_id].display_name}")
    console.print(f"  モデル: {model_id}")
    console.print(f"  言語: {language}")
    if github_username:
        console.print(f"  GitHub: {github_username}")
    console.print("\n[dim]tanren checkin で今日の記録を始めましょう[/dim]")

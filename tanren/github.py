import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from tanren import config

_CACHE_KEY = "github_cache"
_CACHE_TTL_HOURS = 24
_API_BASE = "https://api.github.com"


def _fetch_json(url: str) -> list | dict:
    req = urllib.request.Request(url, headers={"User-Agent": "tanren-cli"})
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode())


def fetch_language_stats(username: str) -> dict:
    """GitHubのリポジトリから言語使用統計を返す。結果は24時間キャッシュ。"""
    cache = config.get(_CACHE_KEY) or {}
    cached_user = cache.get("username")
    cached_at = cache.get("cached_at")

    if (
        cached_user == username
        and cached_at
        and datetime.fromisoformat(cached_at) > datetime.now(timezone.utc) - timedelta(hours=_CACHE_TTL_HOURS)
    ):
        return cache.get("data", {})

    data = _fetch_and_aggregate(username)

    config.set_value(_CACHE_KEY, {
        "username": username,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    })
    return data


def _fetch_and_aggregate(username: str) -> dict:
    url = f"{_API_BASE}/users/{username}/repos?per_page=100&type=owner&sort=pushed"
    repos = _fetch_json(url)

    if not isinstance(repos, list):
        return {}

    language_counts: dict[str, int] = {}
    recent_repos: list[dict] = []

    for repo in repos:
        if repo.get("fork"):
            continue
        lang = repo.get("language")
        if lang:
            language_counts[lang] = language_counts.get(lang, 0) + 1

        pushed = repo.get("pushed_at", "")
        if pushed:
            recent_repos.append({
                "name": repo["name"],
                "language": lang or "不明",
                "pushed_at": pushed[:10],
            })

    recent_repos = sorted(recent_repos, key=lambda r: r["pushed_at"], reverse=True)[:5]

    return {
        "language_counts": dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True)),
        "recent_repos": recent_repos,
        "total_repos": len([r for r in repos if not r.get("fork")]),
    }


def build_github_context(username: str) -> str:
    """スキル査定プロンプトに追加するGitHub情報テキストを返す。"""
    try:
        data = fetch_language_stats(username)
    except Exception:
        return ""

    if not data:
        return ""

    lang_text = ", ".join(
        f"{lang}({count}リポジトリ)"
        for lang, count in list(data["language_counts"].items())[:8]
    ) or "なし"

    recent_text = "\n".join(
        f"  - {r['name']} ({r['language']}, {r['pushed_at']})"
        for r in data["recent_repos"]
    ) or "  なし"

    return f"""【GitHubリポジトリ情報（{username}）】
総リポジトリ数: {data['total_repos']}
使用言語: {lang_text}
最近更新したリポジトリ:
{recent_text}"""

import json
from pathlib import Path

DATA_DIR = Path.home() / ".tanren"
CONFIG_FILE = DATA_DIR / "config.json"
DB_FILE = DATA_DIR / "tanren.db"

_DEFAULTS = {
    "budget_limit_yen": 300,
    "warning_threshold": 0.8,
    "usd_to_jpy": 150,
}

def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)

def load() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save(config: dict):
    ensure_data_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get(key: str, default=None):
    return load().get(key, _DEFAULTS.get(key, default))

def set_value(key: str, value):
    config = load()
    config[key] = value
    save(config)

def is_configured() -> bool:
    return "api_key" in load()

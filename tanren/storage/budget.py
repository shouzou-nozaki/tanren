from datetime import datetime
from tanren.storage import db


def current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def check() -> str:
    return "ok"


def get_usage() -> dict:
    row = _get_row()
    if not row:
        return {
            "year_month": current_month(),
            "cost_usd": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
        }
    return dict(row)


def record(usage, cost_usd: float = 0.0):
    ym = current_month()
    input_tokens = getattr(usage, "prompt_token_count", 0)
    output_tokens = getattr(usage, "candidates_token_count", 0)
    cached_tokens = getattr(usage, "cached_content_token_count", 0)

    conn = db.get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO budget_usage (year_month, input_tokens, output_tokens, cached_tokens, cost_usd)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(year_month) DO UPDATE SET
                input_tokens  = input_tokens  + excluded.input_tokens,
                output_tokens = output_tokens + excluded.output_tokens,
                cached_tokens = cached_tokens + excluded.cached_tokens,
                cost_usd      = cost_usd      + excluded.cost_usd,
                updated_at    = CURRENT_TIMESTAMP
            """,
            (ym, input_tokens, output_tokens, cached_tokens, 0.0),
        )
    conn.close()


def _get_row():
    conn = db.get_connection()
    row = conn.execute(
        "SELECT * FROM budget_usage WHERE year_month = ?", (current_month(),)
    ).fetchone()
    conn.close()
    return row

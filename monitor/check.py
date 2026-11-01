"""Decide what changed for one product and whether it deserves an alert. Pure logic, no I/O."""
from dataclasses import dataclass
from html import escape

from .prices import PageInfo
from .sheet import Row


@dataclass
class Result:
    fields: dict          # Products-tab columns to update
    alert: str | None     # Telegram message, or None


def evaluate(row: Row, page: PageInfo, checked_at: str) -> Result:
    old, new = row.current, page.price
    lowest = min(x for x in (row.lowest, new) if x is not None)
    change = round((new - old) / old * 100, 2) if old else ""
    fields = {
        "Product": row.name or page.name,
        "Current price": new,
        "Lowest price": lowest,
        "Currency": page.currency,
        "Last checked": checked_at,
        "Status": "OK",
    }
    if old is not None and new != old:
        fields["Previous price"] = old
        fields["Change %"] = change

    name = escape(fields["Product"])
    reasons = []
    if old is not None and new < old:
        reasons.append(f"dropped from {page.currency}{old:.2f} ({change:+.2f}%)")
    if row.target is not None and new <= row.target and (old is None or old > row.target):
        reasons.append(f"reached your target {page.currency}{row.target:.2f}")
    if row.lowest is not None and new < row.lowest:
        reasons.append("lowest price ever tracked")

    alert = None
    if reasons:
        alert = (
            f"📉 <b>{name}</b>\n"
            f"Now <b>{page.currency}{new:.2f}</b>: " + "; ".join(reasons) + "\n"
            f'<a href="{escape(row.url)}">Open product</a>'
        )
    return Result(fields, alert)


def failed(error: Exception, checked_at: str) -> dict:
    return {"Last checked": checked_at, "Status": f"Error: {error}"[:200]}

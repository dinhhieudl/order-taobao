"""Local buffer for orders when Google Sheets API is unavailable."""
import json
from pathlib import Path
from datetime import datetime
from ..config import DATA_DIR

BUFFER_FILE = DATA_DIR / "pending_orders.json"


def save_to_buffer(order_data: dict, error: str = ""):
    """Save order to local buffer when Sheets API fails."""
    pending = load_buffer()
    buffered = dict(order_data)
    buffered["_buffered_at"] = datetime.now().isoformat()
    buffered["_error"] = error
    pending.append(buffered)
    BUFFER_FILE.parent.mkdir(exist_ok=True)
    BUFFER_FILE.write_text(json.dumps(pending, ensure_ascii=False, indent=2))


def load_buffer() -> list:
    """Load pending orders from buffer."""
    if BUFFER_FILE.exists():
        try:
            return json.loads(BUFFER_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return []
    return []


def get_buffer_count() -> int:
    """Get number of pending orders in buffer."""
    return len(load_buffer())


async def flush_buffer() -> tuple:
    """Retry sending buffered orders to Sheets. Returns (sent, failed)."""
    from .sheets import append_order_to_sheet

    pending = load_buffer()
    if not pending:
        return 0, 0

    sent = 0
    remaining = []
    for order in pending:
        sheet_type = order.pop("sheet_type", "DON")
        order.pop("_buffered_at", None)
        order.pop("_error", None)
        try:
            append_order_to_sheet(sheet_type, order)
            sent += 1
        except Exception as e:
            order["_error"] = str(e)
            remaining.append(order)

    if remaining:
        BUFFER_FILE.write_text(json.dumps(remaining, ensure_ascii=False, indent=2))
    else:
        BUFFER_FILE.unlink(missing_ok=True)

    return sent, len(remaining)

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from src.models import Deal

HISTORY_PATH = Path(__file__).parent.parent / "data" / "history.json"


def load_history() -> dict:
    if not HISTORY_PATH.exists():
        return {"runs": []}
    return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))


def save_run(deals: list[Deal]) -> None:
    history = load_history()
    history["runs"].append({
        "run_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "deals": [d.to_dict() for d in deals],
    })
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_latest_deals() -> list[Deal]:
    history = load_history()
    if not history["runs"]:
        return []
    return [Deal.from_dict(d) for d in history["runs"][-1]["deals"]]

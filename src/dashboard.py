from __future__ import annotations
from pathlib import Path
from datetime import date
from jinja2 import Environment, FileSystemLoader
from src.models import Deal

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "index.html"

_NEXT_RUN_DATES = {
    range(1, 15): "15th of this month at 00:05 SGT",
    range(15, 22): "22nd of this month at 09:00 SGT",
    range(22, 32): "1st of next month at 09:00 SGT",
}


def _next_run_label() -> str:
    day = date.today().day
    for r, label in _NEXT_RUN_DATES.items():
        if day in r:
            return label
    return "1st of next month at 09:00 SGT"


def generate_dashboard(deals: list[Deal], run_at: str = "") -> None:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("dashboard.html.j2")

    good_deals = sorted(
        [d for d in deals if d.is_good_deal],
        key=lambda d: d.cpm_kf or d.cpm_flair or 0,
        reverse=True,
    )

    html = template.render(
        run_at=run_at or date.today().isoformat(),
        next_run=_next_run_label(),
        good_deals=good_deals,
        all_deals=deals,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")

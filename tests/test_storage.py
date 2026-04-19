import pytest
from src.models import Deal
from src import storage


@pytest.fixture(autouse=True)
def tmp_history(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "HISTORY_PATH", tmp_path / "history.json")


def _deal() -> Deal:
    return Deal(
        airline="SIA", origin="SIN", destination="BKK",
        destination_city="Bangkok", destination_country="TH",
        cabin="Economy", travel_date="2026-05-10", book_by="2026-04-20",
        cash_total=180.0, tax=42.0, cash_base=138.0,
        scraped_at="2026-04-15T00:05:00+00:00",
        kf_miles=7500, cpm_kf=1.84, is_good_deal=True,
    )


def test_save_and_load_latest():
    storage.save_run([_deal()])
    deals = storage.get_latest_deals()
    assert len(deals) == 1
    assert deals[0].destination == "BKK"


def test_history_accumulates():
    storage.save_run([_deal()])
    storage.save_run([_deal()])
    history = storage.load_history()
    assert len(history["runs"]) == 2


def test_empty_history_returns_empty():
    assert storage.get_latest_deals() == []

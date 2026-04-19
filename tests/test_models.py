# tests/test_models.py
from src.models import Deal

def test_deal_roundtrip():
    d = Deal(
        airline="SIA", origin="SIN", destination="BKK",
        destination_city="Bangkok", destination_country="TH",
        cabin="Economy", travel_date="2026-05-10", book_by="2026-04-20",
        cash_total=180.0, tax=42.0, cash_base=138.0,
        scraped_at="2026-04-15T00:05:00+00:00",
    )
    assert Deal.from_dict(d.to_dict()) == d

def test_deal_defaults():
    d = Deal(
        airline="SIA", origin="SIN", destination="BKK",
        destination_city="Bangkok", destination_country="TH",
        cabin="Economy", travel_date="2026-05-10", book_by="2026-04-20",
        cash_total=180.0, tax=42.0, cash_base=138.0,
        scraped_at="2026-04-15T00:05:00+00:00",
    )
    assert d.kf_miles is None
    assert d.is_good_deal is False

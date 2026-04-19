from src.models import Deal
from src.notifier import build_message

def _deal(is_good=True, airline="SIA", dest="BKK", cpm_kf=1.84, kf_miles=7500):
    return Deal(
        airline=airline, origin="SIN", destination=dest,
        destination_city="Bangkok", destination_country="TH",
        cabin="Economy", travel_date="2026-05-10", book_by="2026-04-20",
        cash_total=180.0, tax=42.0, cash_base=138.0,
        scraped_at="2026-04-15T00:00:00+00:00",
        kf_miles=kf_miles, cpm_kf=cpm_kf, is_good_deal=is_good,
    )

def test_no_good_deals_message():
    msg = build_message([_deal(is_good=False)])
    assert "no deals above threshold" in msg.lower()

def test_good_deals_message_contains_dest():
    msg = build_message([_deal(is_good=True)])
    assert "BKK" in msg

def test_good_deals_message_contains_cpm():
    msg = build_message([_deal(is_good=True, cpm_kf=1.84)])
    assert "1.84" in msg

def test_scoot_deal_shows_flair():
    d = Deal(
        airline="Scoot", origin="SIN", destination="BKK",
        destination_city="Bangkok", destination_country="TH",
        cabin="Economy", travel_date="2026-05-10", book_by="2026-04-20",
        cash_total=95.0, tax=28.0, cash_base=67.0,
        scraped_at="2026-04-15T00:00:00+00:00",
        flair_miles=6700, cpm_flair=1.0, is_good_deal=True,
    )
    msg = build_message([d])
    assert "Flair" in msg
    assert "6,700" in msg

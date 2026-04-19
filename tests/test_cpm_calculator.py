from src.models import Deal
from src.cpm_calculator import calculate_cpm, enrich_deal, filter_excluded


def _make_deal(airline="SIA", destination="BKK", country="TH",
               cabin="Economy", cash_total=180.0, tax=42.0) -> Deal:
    return Deal(
        airline=airline, origin="SIN", destination=destination,
        destination_city="City", destination_country=country,
        cabin=cabin, travel_date="2026-05-10", book_by="2026-04-20",
        cash_total=cash_total, tax=tax, cash_base=round(cash_total - tax, 2),
        scraped_at="2026-04-15T00:00:00+00:00",
    )


def test_calculate_cpm():
    assert calculate_cpm(138.0, 7500) == round((138.0 / 7500) * 100, 4)


def test_calculate_cpm_zero_miles():
    assert calculate_cpm(100.0, 0) == 0.0


def test_enrich_sia_good_deal():
    deal = _make_deal(airline="SIA", destination="BKK", cash_total=180.0, tax=42.0)
    enrich_deal(deal)
    assert deal.kf_miles == 7500
    assert deal.cpm_kf == round((138.0 / 7500) * 100, 4)
    assert deal.is_good_deal is True  # 1.84 >= 1.5


def test_enrich_sia_bad_deal():
    deal = _make_deal(airline="SIA", destination="BKK", cash_total=80.0, tax=42.0)
    enrich_deal(deal)
    assert deal.is_good_deal is False  # (38/7500)*100 = 0.5 < 1.5


def test_enrich_scoot():
    deal = _make_deal(airline="Scoot", destination="BKK", cash_total=100.0, tax=20.0)
    enrich_deal(deal)
    assert deal.flair_miles == 8000  # 80 * 100
    assert deal.cpm_flair == round((80.0 / 8000) * 100, 4)  # 1.0
    assert deal.is_good_deal is True  # 1.0 >= 0.8


def test_filter_excluded_removes_india():
    deals = [
        _make_deal(country="TH"),
        _make_deal(country="IN"),
        _make_deal(country="AE"),
    ]
    result = filter_excluded(deals)
    assert len(result) == 1
    assert result[0].destination_country == "TH"

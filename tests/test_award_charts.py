# tests/test_award_charts.py
from src.award_charts import get_kf_miles, is_excluded

def test_kf_zone1_economy():
    assert get_kf_miles("BKK", "Economy") == 7500

def test_kf_zone2b_economy():
    assert get_kf_miles("NRT", "Economy") == 22500

def test_kf_zone3_business():
    assert get_kf_miles("SYD", "Business") == 57000

def test_kf_unknown_iata():
    assert get_kf_miles("ZZZ", "Economy") is None

def test_excluded_middle_east():
    assert is_excluded("AE") is True
    assert is_excluded("SA") is True

def test_excluded_india():
    assert is_excluded("IN") is True

def test_excluded_africa():
    assert is_excluded("NG") is True
    assert is_excluded("ZA") is True

def test_not_excluded_thailand():
    assert is_excluded("TH") is False

def test_not_excluded_japan():
    assert is_excluded("JP") is False

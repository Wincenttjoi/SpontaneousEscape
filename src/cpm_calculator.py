from __future__ import annotations
from src.models import Deal
from src.award_charts import get_kf_miles, is_excluded

KF_GOOD_DEAL_THRESHOLD = 1.5
FLAIR_GOOD_DEAL_THRESHOLD = 0.8


def calculate_cpm(cash_base: float, miles: int) -> float:
    if miles <= 0:
        return 0.0
    return round((cash_base / miles) * 100, 4)


def enrich_deal(deal: Deal) -> Deal:
    if deal.airline == "SIA":
        miles = get_kf_miles(deal.destination, deal.cabin)
        deal.kf_miles = miles
        if miles:
            deal.cpm_kf = calculate_cpm(deal.cash_base, miles)
            deal.is_good_deal = deal.cpm_kf >= KF_GOOD_DEAL_THRESHOLD

    elif deal.airline == "Scoot":
        flair_miles = int(deal.cash_base * 100)
        deal.flair_miles = flair_miles
        if flair_miles:
            deal.cpm_flair = calculate_cpm(deal.cash_base, flair_miles)
            deal.is_good_deal = deal.cpm_flair >= FLAIR_GOOD_DEAL_THRESHOLD

    return deal


def filter_excluded(deals: list[Deal]) -> list[Deal]:
    return [d for d in deals if not is_excluded(d.destination_country)]

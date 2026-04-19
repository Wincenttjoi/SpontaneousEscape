from __future__ import annotations
from src.models import Deal
from src.award_charts import get_kf_miles, is_excluded


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

    elif deal.airline == "Scoot":
        flair_miles = int(deal.cash_base * 100)
        deal.flair_miles = flair_miles
        if flair_miles:
            deal.cpm_flair = calculate_cpm(deal.cash_base, flair_miles)

    return deal


def flag_top_percentile(deals: list[Deal], percentile: int = 75) -> list[Deal]:
    cpms = [d.cpm_kf or d.cpm_flair or 0.0 for d in deals]
    if not cpms:
        return deals
    sorted_cpms = sorted(cpms)
    cutoff_index = int(len(sorted_cpms) * percentile / 100)
    threshold = sorted_cpms[cutoff_index] if cutoff_index < len(sorted_cpms) else sorted_cpms[-1]
    for deal in deals:
        cpm = deal.cpm_kf or deal.cpm_flair or 0.0
        deal.is_good_deal = cpm >= threshold and cpm > 0
    return deals


def filter_excluded(deals: list[Deal]) -> list[Deal]:
    return [d for d in deals if not is_excluded(d.destination_country)]

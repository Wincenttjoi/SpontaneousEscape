from __future__ import annotations
from typing import Optional, Union

_KF_ZONE_MILES: dict[Union[int, str], int] = {
    1:    7_500,
    "2a": 17_500,
    "2b": 22_500,
    3:    28_500,
    4:    62_500,
}

_KF_BUSINESS_MULTIPLIER = 2.0

_KF_IATA_ZONE: dict[str, Union[int, str]] = {
    # Zone 1 — SE Asia
    "KUL": 1, "PEN": 1, "LGK": 1, "JHB": 1, "BKI": 1, "KCH": 1,
    "BKK": 1, "DMK": 1, "CNX": 1, "HKT": 1, "USM": 1, "HDY": 1,
    "CGK": 1, "DPS": 1, "SUB": 1, "JOG": 1, "SRG": 1, "PLM": 1, "BDO": 1,
    "MNL": 1, "CEB": 1, "CRK": 1, "DVO": 1,
    "SGN": 1, "HAN": 1, "DAD": 1, "CXR": 1,
    "RGN": 1,
    "PNH": 1, "REP": 1,
    "VTE": 1,
    "BWN": 1,
    # Zone 2a — HKG / TPE / MFM
    "HKG": "2a", "TPE": "2a", "MFM": "2a",
    # Zone 2b — Japan / Korea / China
    "NRT": "2b", "HND": "2b", "KIX": "2b", "NGO": "2b",
    "FUK": "2b", "OKA": "2b", "ITM": "2b", "CTS": "2b",
    "ICN": "2b", "GMP": "2b", "PUS": "2b",
    "PEK": "2b", "PKX": "2b", "PVG": "2b", "SHA": "2b",
    "CAN": "2b", "CTU": "2b", "XIY": "2b", "SZX": "2b", "WUH": "2b",
    # Zone 3 — Australia / NZ
    "SYD": 3, "MEL": 3, "BNE": 3, "PER": 3, "ADL": 3, "CBR": 3, "OOL": 3,
    "AKL": 3, "CHC": 3, "WLG": 3,
    # Zone 4 — Europe / Americas
    "LHR": 4, "LGW": 4, "MAN": 4, "CDG": 4, "FRA": 4, "MUC": 4,
    "AMS": 4, "ZRH": 4, "FCO": 4, "MAD": 4, "BCN": 4, "VIE": 4,
    "LAX": 4, "SFO": 4, "JFK": 4, "EWR": 4, "YVR": 4, "YYZ": 4,
}


def get_kf_miles(iata: str, cabin: str) -> Optional[int]:
    zone = _KF_IATA_ZONE.get(iata.upper())
    if zone is None:
        return None
    base = _KF_ZONE_MILES[zone]
    if cabin == "Business":
        return int(base * _KF_BUSINESS_MULTIPLIER)
    return base


EXCLUDED_COUNTRIES: frozenset[str] = frozenset({
    # Middle East
    "AE", "SA", "QA", "BH", "KW", "OM", "YE", "JO", "IQ", "IR", "IL", "SY", "LB",
    # India
    "IN",
    # Africa
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "CD", "TD", "KM", "CG",
    "CI", "DJ", "EG", "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE",
    "LS", "LR", "LY", "MG", "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG",
    "RW", "ST", "SN", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "EH",
    "ZM", "ZW",
})


def is_excluded(country_code: str) -> bool:
    return country_code.upper() in EXCLUDED_COUNTRIES

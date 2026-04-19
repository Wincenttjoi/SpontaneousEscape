# Spontaneous Escape Scraper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrape SIA and Scoot Spontaneous Escape deals 3× per month, calculate KrisFlyer/Scoot Flair cents-per-mile value, and deliver results via Telegram and a static HTML dashboard hosted on GitHub Pages.

**Architecture:** All logic lives in a plain Python app (`src/`). GitHub Actions triggers `python -m src.main` on a cron schedule and commits the updated `data/history.json` and `docs/index.html` back to the repo. The `docs/` folder is served as GitHub Pages.

**Tech Stack:** Python 3.11, Playwright, Amadeus SDK, python-telegram-bot 21, Jinja2, pytest

---

## File Map

```
SpontaneousEscape/
├── .github/workflows/scrape.yml     — cron schedule + CI
├── src/
│   ├── __init__.py
│   ├── models.py                    — Deal dataclass
│   ├── award_charts.py              — KrisFlyer zones + Scoot Flair rates + excluded regions
│   ├── cpm_calculator.py            — CPM formula, deal enrichment, region filter
│   ├── amadeus_client.py            — cheapest-date lookup via Amadeus API
│   ├── storage.py                   — history.json read/write
│   ├── dashboard.py                 — renders Jinja2 template → docs/index.html
│   ├── notifier.py                  — Telegram message builder + sender
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── sia.py                   — SIA Spontaneous Escapes Playwright scraper
│   │   └── scoot.py                 — Scoot Spontaneous Escapes Playwright scraper
│   └── main.py                      — orchestrator
├── templates/
│   └── dashboard.html.j2            — Jinja2 HTML template
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── sia_page.html            — minimal SIA deal card HTML for scraper tests
│   │   └── scoot_page.html          — minimal Scoot deal card HTML for scraper tests
│   ├── test_award_charts.py
│   ├── test_cpm_calculator.py
│   ├── test_storage.py
│   └── test_notifier.py
├── data/
│   └── history.json                 — persisted deal history (committed by CI)
├── docs/
│   └── index.html                   — generated dashboard (committed by CI)
├── requirements.txt
└── .env.example
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/scrapers/__init__.py`
- Create: `tests/__init__.py`
- Create: `data/history.json`
- Create: `.gitignore`

- [ ] **Step 1: Create `requirements.txt`**

```
playwright==1.44.0
python-telegram-bot==21.3
amadeus==9.0.0
python-dotenv==1.0.1
jinja2==3.1.4
pytest==8.2.2
```

- [ ] **Step 2: Create `.env.example`**

```
AMADEUS_CLIENT_ID=your_client_id_here
AMADEUS_CLIENT_SECRET=your_client_secret_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

- [ ] **Step 3: Create empty init files**

```bash
touch src/__init__.py src/scrapers/__init__.py tests/__init__.py
mkdir -p templates data docs tests/fixtures
```

- [ ] **Step 4: Create `data/history.json`**

```json
{"runs": []}
```

- [ ] **Step 5: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
.playwright/
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

Expected: no errors, `playwright install` downloads Chromium (~150MB).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example src/__init__.py src/scrapers/__init__.py tests/__init__.py data/history.json .gitignore templates/ docs/
git commit -m "chore: project scaffold"
```

---

## Task 2: Data Model

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```
Expected: `ImportError: cannot import name 'Deal'`

- [ ] **Step 3: Create `src/models.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Deal:
    airline: str
    origin: str
    destination: str
    destination_city: str
    destination_country: str
    cabin: str
    travel_date: str
    book_by: str
    cash_total: float
    tax: float
    cash_base: float
    scraped_at: str
    kf_miles: Optional[int] = None
    flair_miles: Optional[int] = None
    cpm_kf: Optional[float] = None
    cpm_flair: Optional[float] = None
    amadeus_cheapest_date: Optional[str] = None
    amadeus_cheapest_price: Optional[float] = None
    is_good_deal: bool = False

    def to_dict(self) -> dict:
        return {
            "airline": self.airline,
            "origin": self.origin,
            "destination": self.destination,
            "destination_city": self.destination_city,
            "destination_country": self.destination_country,
            "cabin": self.cabin,
            "travel_date": self.travel_date,
            "book_by": self.book_by,
            "cash_total": self.cash_total,
            "tax": self.tax,
            "cash_base": self.cash_base,
            "scraped_at": self.scraped_at,
            "kf_miles": self.kf_miles,
            "flair_miles": self.flair_miles,
            "cpm_kf": self.cpm_kf,
            "cpm_flair": self.cpm_flair,
            "amadeus_cheapest_date": self.amadeus_cheapest_date,
            "amadeus_cheapest_price": self.amadeus_cheapest_price,
            "is_good_deal": self.is_good_deal,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Deal:
        return cls(**d)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add Deal dataclass"
```

---

## Task 3: Award Charts & Region Filter

**Files:**
- Create: `src/award_charts.py`
- Create: `tests/test_award_charts.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_award_charts.py -v
```
Expected: `ImportError: cannot import name 'get_kf_miles'`

- [ ] **Step 3: Create `src/award_charts.py`**

```python
from __future__ import annotations
from typing import Optional, Union

# KrisFlyer Economy Saver miles one-way from SIN
_KF_ZONE_MILES: dict[Union[int, str], int] = {
    1:    7_500,
    "2a": 17_500,
    "2b": 22_500,
    3:    28_500,
    4:    62_500,
}

_KF_BUSINESS_MULTIPLIER = 2.0  # Business = 2× Economy Saver

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
    """Return KrisFlyer Saver miles for a one-way SIN→iata flight."""
    zone = _KF_IATA_ZONE.get(iata.upper())
    if zone is None:
        return None
    base = _KF_ZONE_MILES[zone]
    if cabin == "Business":
        return int(base * _KF_BUSINESS_MULTIPLIER)
    return base


# Excluded destination country codes
EXCLUDED_COUNTRIES: frozenset[str] = frozenset({
    # Middle East
    "AE", "SA", "QA", "BH", "KW", "OM", "YE", "JO", "IQ", "IR", "IL", "SY", "LB",
    # India
    "IN",
    # Africa
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD", "KM", "CG", "CD",
    "CI", "DJ", "EG", "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE",
    "LS", "LR", "LY", "MG", "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG",
    "RW", "ST", "SN", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "EH",
    "ZM", "ZW",
})


def is_excluded(country_code: str) -> bool:
    return country_code.upper() in EXCLUDED_COUNTRIES
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_award_charts.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/award_charts.py tests/test_award_charts.py
git commit -m "feat: add KrisFlyer award chart and region exclusion list"
```

---

## Task 4: CPM Calculator

**Files:**
- Create: `src/cpm_calculator.py`
- Create: `tests/test_cpm_calculator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cpm_calculator.py
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
    # (138 / 7500) * 100 = 1.84
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
    # Low base fare → low CPM
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_cpm_calculator.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `src/cpm_calculator.py`**

```python
from __future__ import annotations
from src.models import Deal
from src.award_charts import get_kf_miles, is_excluded

KF_GOOD_DEAL_THRESHOLD = 1.5    # SGD cents/mile
FLAIR_GOOD_DEAL_THRESHOLD = 0.8  # SGD cents/mile


def calculate_cpm(cash_base: float, miles: int) -> float:
    if miles <= 0:
        return 0.0
    return round((cash_base / miles) * 100, 4)


def enrich_deal(deal: Deal) -> Deal:
    """Populate miles, CPM, and is_good_deal on a Deal in place. Returns the same deal."""
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_cpm_calculator.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/cpm_calculator.py tests/test_cpm_calculator.py
git commit -m "feat: add CPM calculator and deal enrichment"
```

---

## Task 5: Storage

**Files:**
- Create: `src/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_storage.py
import json
import pytest
from pathlib import Path
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_storage.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `src/storage.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_storage.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/storage.py tests/test_storage.py
git commit -m "feat: add history storage"
```

---

## Task 6: SIA Scraper

**Files:**
- Create: `src/scrapers/sia.py`
- Create: `tests/fixtures/sia_page.html`

> **Note:** The real SIA page structure must be verified by running the scraper once with `DEBUG_SAVE_HTML=1` (see Step 3) and inspecting the saved HTML. The selectors below are based on common SIA page patterns and will likely need tuning.

- [ ] **Step 1: Create `tests/fixtures/sia_page.html`** (minimal fixture for unit tests)

```html
<!DOCTYPE html>
<html>
<body>
  <div class="se-card" data-iata="BKK" data-country="TH">
    <div class="se-city">Bangkok</div>
    <div class="se-country">Thailand</div>
    <div class="se-price">SGD 180</div>
    <div class="se-tax">SGD 42</div>
    <div class="se-travel-date">10 May 2026</div>
    <div class="se-book-by">20 Apr 2026</div>
    <div class="se-cabin">Economy</div>
  </div>
  <div class="se-card" data-iata="NRT" data-country="JP">
    <div class="se-city">Tokyo</div>
    <div class="se-country">Japan</div>
    <div class="se-price">SGD 520</div>
    <div class="se-tax">SGD 88</div>
    <div class="se-travel-date">15 May 2026</div>
    <div class="se-book-by">20 Apr 2026</div>
    <div class="se-cabin">Economy</div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Create `src/scrapers/sia.py`**

```python
from __future__ import annotations
import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, ElementHandle
from src.models import Deal

logger = logging.getLogger(__name__)

SIA_URL = "https://www.singaporeair.com/en_UK/sg/promotions/spontaneous-escapes/"

# Selector groups — tried in order, first match wins
_CARD_SELECTORS = [
    ".se-card",
    ".spontaneous-escape-card",
    "[data-testid='deal-card']",
    ".deal-card",
    ".promo-card",
]
_CITY_SELECTORS = [".se-city", ".city-name", ".destination-name", "h3", "h4"]
_COUNTRY_SELECTORS = [".se-country", ".country-name", ".destination-country"]
_PRICE_SELECTORS = [".se-price", ".fare-price", ".from-price", ".price"]
_TAX_SELECTORS = [".se-tax", ".tax-amount", ".taxes-fees"]
_TRAVEL_DATE_SELECTORS = [".se-travel-date", ".travel-date", ".departure-date"]
_BOOK_BY_SELECTORS = [".se-book-by", ".book-by", ".offer-ends", ".sale-ends"]
_CABIN_SELECTORS = [".se-cabin", ".cabin-class"]


def scrape_sia() -> list[Deal]:
    deals: list[Deal] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })
        try:
            page.goto(SIA_URL, wait_until="networkidle", timeout=60_000)
            if os.environ.get("DEBUG_SAVE_HTML"):
                Path("debug_sia.html").write_text(page.content(), encoding="utf-8")
                logger.info("Saved SIA page HTML to debug_sia.html")
            selector = _first_matching(page, _CARD_SELECTORS)
            if not selector:
                logger.warning("SIA: no deal cards found — page structure may have changed")
                return []
            page.wait_for_selector(selector, timeout=15_000)
            for card in page.query_selector_all(selector):
                deal = _parse_card(card)
                if deal:
                    deals.append(deal)
        except Exception as e:
            logger.error(f"SIA scrape failed: {e}")
        finally:
            browser.close()
    logger.info(f"SIA: scraped {len(deals)} deals")
    return deals


def _parse_card(card: ElementHandle) -> Deal | None:
    try:
        city = _text(card, _CITY_SELECTORS) or ""
        country_name = _text(card, _COUNTRY_SELECTORS) or ""
        price_text = _text(card, _PRICE_SELECTORS) or "0"
        tax_text = _text(card, _TAX_SELECTORS) or "0"
        travel_date = _text(card, _TRAVEL_DATE_SELECTORS) or ""
        book_by = _text(card, _BOOK_BY_SELECTORS) or ""
        cabin_text = _text(card, _CABIN_SELECTORS) or ""
        cabin = "Business" if "business" in cabin_text.lower() else "Economy"

        iata = (
            card.get_attribute("data-iata")
            or card.get_attribute("data-airport")
            or _city_to_iata(city)
            or ""
        )
        country_code = (
            card.get_attribute("data-country")
            or _country_to_code(country_name)
            or ""
        )

        cash_total = _parse_price(price_text)
        tax = _parse_price(tax_text)

        if not city or cash_total == 0:
            return None

        return Deal(
            airline="SIA",
            origin="SIN",
            destination=iata.upper(),
            destination_city=city,
            destination_country=country_code.upper(),
            cabin=cabin,
            travel_date=_parse_date(travel_date),
            book_by=_parse_date(book_by),
            cash_total=cash_total,
            tax=tax,
            cash_base=round(cash_total - tax, 2),
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.warning(f"SIA: failed to parse card — {e}")
        return None


def _first_matching(page, selectors: list[str]) -> str | None:
    for sel in selectors:
        try:
            if page.query_selector(sel):
                return sel
        except Exception:
            pass
    return None


def _text(card: ElementHandle, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = card.query_selector(sel)
        if el:
            return el.inner_text().strip()
    return None


def _parse_price(text: str) -> float:
    digits = re.sub(r"[^\d.]", "", text)
    return float(digits) if digits else 0.0


def _parse_date(text: str) -> str:
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text.strip()


_CITY_IATA: dict[str, str] = {
    "Bangkok": "BKK", "Tokyo": "NRT", "Osaka": "KIX", "Seoul": "ICN",
    "Hong Kong": "HKG", "Taipei": "TPE", "Sydney": "SYD", "Melbourne": "MEL",
    "Perth": "PER", "Brisbane": "BNE", "Auckland": "AKL", "London": "LHR",
    "Paris": "CDG", "Frankfurt": "FRA", "Los Angeles": "LAX",
    "Kuala Lumpur": "KUL", "Jakarta": "CGK", "Bali": "DPS",
    "Manila": "MNL", "Ho Chi Minh City": "SGN", "Hanoi": "HAN",
    "Yangon": "RGN", "Phnom Penh": "PNH", "Vientiane": "VTE",
    "Fukuoka": "FUK", "Sapporo": "CTS", "Okinawa": "OKA",
    "Busan": "PUS", "Shanghai": "PVG", "Beijing": "PEK",
}

_COUNTRY_CODES: dict[str, str] = {
    "Thailand": "TH", "Japan": "JP", "South Korea": "KR", "Korea": "KR",
    "Hong Kong": "HK", "Taiwan": "TW", "Australia": "AU", "New Zealand": "NZ",
    "United Kingdom": "GB", "France": "FR", "Germany": "DE", "United States": "US",
    "Malaysia": "MY", "Indonesia": "ID", "Philippines": "PH",
    "Vietnam": "VN", "Myanmar": "MM", "Cambodia": "KH", "Laos": "LA",
    "Brunei": "BN", "Macau": "MO", "China": "CN",
}


def _city_to_iata(city: str) -> str | None:
    return _CITY_IATA.get(city)


def _country_to_code(country: str) -> str:
    return _COUNTRY_CODES.get(country, "")
```

- [ ] **Step 3: Run a debug scrape to verify selectors (requires internet)**

```bash
DEBUG_SAVE_HTML=1 python -c "from src.scrapers.sia import scrape_sia; deals = scrape_sia(); print(f'{len(deals)} deals')"
```

Open `debug_sia.html` in a browser. If `0 deals` returned, inspect the HTML to find the correct card/field selectors and update `_CARD_SELECTORS` and field selectors in `sia.py` to match.

- [ ] **Step 4: Commit**

```bash
git add src/scrapers/sia.py tests/fixtures/sia_page.html
git commit -m "feat: add SIA Spontaneous Escapes scraper"
```

---

## Task 7: Scoot Scraper

**Files:**
- Create: `src/scrapers/scoot.py`
- Create: `tests/fixtures/scoot_page.html`

- [ ] **Step 1: Create `tests/fixtures/scoot_page.html`**

```html
<!DOCTYPE html>
<html>
<body>
  <div class="se-card" data-iata="BKK" data-country="TH">
    <div class="se-city">Bangkok</div>
    <div class="se-country">Thailand</div>
    <div class="se-price">SGD 95</div>
    <div class="se-tax">SGD 28</div>
    <div class="se-travel-date">12 May 2026</div>
    <div class="se-book-by">20 Apr 2026</div>
  </div>
  <div class="se-card" data-iata="NRT" data-country="JP">
    <div class="se-city">Tokyo</div>
    <div class="se-country">Japan</div>
    <div class="se-price">SGD 310</div>
    <div class="se-tax">SGD 55</div>
    <div class="se-travel-date">18 May 2026</div>
    <div class="se-book-by">20 Apr 2026</div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Create `src/scrapers/scoot.py`**

```python
from __future__ import annotations
import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, ElementHandle
from src.models import Deal

logger = logging.getLogger(__name__)

SCOOT_URL = "https://www.flyscoot.com/en/spontaneous-escape"

_CARD_SELECTORS = [
    ".se-card",
    ".spontaneous-escape-card",
    ".deal-card",
    "[data-testid='deal-card']",
    ".flight-deal",
    ".promo-tile",
]
_CITY_SELECTORS = [".se-city", ".city-name", ".destination", "h3", "h4"]
_COUNTRY_SELECTORS = [".se-country", ".country-name", ".destination-country"]
_PRICE_SELECTORS = [".se-price", ".price", ".fare", ".from-price"]
_TAX_SELECTORS = [".se-tax", ".tax", ".taxes"]
_TRAVEL_DATE_SELECTORS = [".se-travel-date", ".travel-date", ".dates", ".departure"]
_BOOK_BY_SELECTORS = [".se-book-by", ".book-by", ".offer-ends", ".sale-ends"]


def scrape_scoot() -> list[Deal]:
    deals: list[Deal] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })
        try:
            page.goto(SCOOT_URL, wait_until="networkidle", timeout=60_000)
            if os.environ.get("DEBUG_SAVE_HTML"):
                Path("debug_scoot.html").write_text(page.content(), encoding="utf-8")
                logger.info("Saved Scoot page HTML to debug_scoot.html")
            selector = _first_matching(page, _CARD_SELECTORS)
            if not selector:
                logger.warning("Scoot: no deal cards found — page structure may have changed")
                return []
            page.wait_for_selector(selector, timeout=15_000)
            for card in page.query_selector_all(selector):
                deal = _parse_card(card)
                if deal:
                    deals.append(deal)
        except Exception as e:
            logger.error(f"Scoot scrape failed: {e}")
        finally:
            browser.close()
    logger.info(f"Scoot: scraped {len(deals)} deals")
    return deals


def _parse_card(card: ElementHandle) -> Deal | None:
    try:
        city = _text(card, _CITY_SELECTORS) or ""
        country_name = _text(card, _COUNTRY_SELECTORS) or ""
        price_text = _text(card, _PRICE_SELECTORS) or "0"
        tax_text = _text(card, _TAX_SELECTORS) or "0"
        travel_date = _text(card, _TRAVEL_DATE_SELECTORS) or ""
        book_by = _text(card, _BOOK_BY_SELECTORS) or ""

        iata = (
            card.get_attribute("data-iata")
            or card.get_attribute("data-airport")
            or _city_to_iata(city)
            or ""
        )
        country_code = (
            card.get_attribute("data-country")
            or _country_to_code(country_name)
            or ""
        )

        cash_total = _parse_price(price_text)
        tax = _parse_price(tax_text)

        if not city or cash_total == 0:
            return None

        return Deal(
            airline="Scoot",
            origin="SIN",
            destination=iata.upper(),
            destination_city=city,
            destination_country=country_code.upper(),
            cabin="Economy",
            travel_date=_parse_date(travel_date),
            book_by=_parse_date(book_by),
            cash_total=cash_total,
            tax=tax,
            cash_base=round(cash_total - tax, 2),
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.warning(f"Scoot: failed to parse card — {e}")
        return None


def _first_matching(page, selectors: list[str]) -> str | None:
    for sel in selectors:
        try:
            if page.query_selector(sel):
                return sel
        except Exception:
            pass
    return None


def _text(card: ElementHandle, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = card.query_selector(sel)
        if el:
            return el.inner_text().strip()
    return None


def _parse_price(text: str) -> float:
    digits = re.sub(r"[^\d.]", "", text)
    return float(digits) if digits else 0.0


def _parse_date(text: str) -> str:
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text.strip()


_CITY_IATA: dict[str, str] = {
    "Bangkok": "BKK", "Tokyo": "NRT", "Osaka": "KIX", "Seoul": "ICN",
    "Hong Kong": "HKG", "Taipei": "TPE", "Sydney": "SYD", "Melbourne": "MEL",
    "Perth": "PER", "Brisbane": "BNE", "Auckland": "AKL",
    "Kuala Lumpur": "KUL", "Jakarta": "CGK", "Bali": "DPS",
    "Manila": "MNL", "Ho Chi Minh City": "SGN", "Hanoi": "HAN",
    "Yangon": "RGN", "Phnom Penh": "PNH", "Vientiane": "VTE",
    "Fukuoka": "FUK", "Sapporo": "CTS", "Okinawa": "OKA",
    "Busan": "PUS", "Shanghai": "PVG", "Beijing": "PEK",
    "Gold Coast": "OOL", "Taipei": "TPE",
}

_COUNTRY_CODES: dict[str, str] = {
    "Thailand": "TH", "Japan": "JP", "South Korea": "KR", "Korea": "KR",
    "Hong Kong": "HK", "Taiwan": "TW", "Australia": "AU", "New Zealand": "NZ",
    "Malaysia": "MY", "Indonesia": "ID", "Philippines": "PH",
    "Vietnam": "VN", "Myanmar": "MM", "Cambodia": "KH", "Laos": "LA",
    "Brunei": "BN", "Macau": "MO", "China": "CN",
}


def _city_to_iata(city: str) -> str | None:
    return _CITY_IATA.get(city)


def _country_to_code(country: str) -> str:
    return _COUNTRY_CODES.get(country, "")
```

- [ ] **Step 3: Run a debug scrape**

```bash
DEBUG_SAVE_HTML=1 python -c "from src.scrapers.scoot import scrape_scoot; deals = scrape_scoot(); print(f'{len(deals)} deals')"
```

Open `debug_scoot.html`. If `0 deals`, inspect HTML and update `_CARD_SELECTORS` and field selectors.

- [ ] **Step 4: Commit**

```bash
git add src/scrapers/scoot.py tests/fixtures/scoot_page.html
git commit -m "feat: add Scoot Spontaneous Escapes scraper"
```

---

## Task 8: Amadeus Client

**Files:**
- Create: `src/amadeus_client.py`

> **Note:** Amadeus integration is **optional**. If `AMADEUS_CLIENT_ID` is not set, the client returns `(None, None)` for all calls — nothing breaks. Add credentials later when available.

- [ ] **Step 1: Create `src/amadeus_client.py`**

```python
from __future__ import annotations
import os
import logging
from datetime import datetime, timedelta
from amadeus import Client, ResponseError

logger = logging.getLogger(__name__)


def get_cheapest_date(
    origin: str, destination: str, around_date: str
) -> tuple[str, float] | tuple[None, None]:
    """Return (cheapest_date, price_SGD) within ±15 days of around_date, or (None, None) if credentials absent or on failure."""
    if not os.environ.get("AMADEUS_CLIENT_ID") or not origin or not destination:
        return None, None
    try:
        client = Client(
            client_id=os.environ["AMADEUS_CLIENT_ID"],
            client_secret=os.environ["AMADEUS_CLIENT_SECRET"],
        )
        base = datetime.strptime(around_date, "%Y-%m-%d")
        start = (base - timedelta(days=15)).strftime("%Y-%m-%d")
        end = (base + timedelta(days=15)).strftime("%Y-%m-%d")

        response = client.shopping.flight_dates.get(
            origin=origin,
            destination=destination,
            departureDate=f"{start},{end}",
            oneWay=True,
            currency="SGD",
        )
        data = response.data
        if not data:
            return None, None
        cheapest = min(data, key=lambda x: float(x["price"]["total"]))
        return cheapest["departureDate"], round(float(cheapest["price"]["total"]), 2)

    except ResponseError as e:
        logger.warning(f"Amadeus error {origin}→{destination}: {e}")
        return None, None
    except Exception as e:
        logger.warning(f"Amadeus unexpected error {origin}→{destination}: {e}")
        return None, None
```

- [ ] **Step 2: Smoke test (requires valid Amadeus credentials in `.env`)**

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from src.amadeus_client import get_cheapest_date
date, price = get_cheapest_date('SIN', 'BKK', '2026-05-15')
print(date, price)
"
```
Expected: a date string and float price, or `None None` if credentials are test-tier.

- [ ] **Step 3: Commit**

```bash
git add src/amadeus_client.py
git commit -m "feat: add Amadeus cheapest-date client"
```

---

## Task 9: HTML Dashboard

**Files:**
- Create: `templates/dashboard.html.j2`
- Create: `src/dashboard.py`

- [ ] **Step 1: Create `templates/dashboard.html.j2`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Spontaneous Escape Deals</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f6fa; color: #2d3436; padding: 24px; }
  header { margin-bottom: 24px; }
  header h1 { font-size: 1.8rem; font-weight: 700; }
  header p { color: #636e72; margin-top: 4px; font-size: 0.9rem; }
  .section-title { font-size: 1.1rem; font-weight: 600; margin: 24px 0 12px; }
  .cards { display: flex; flex-wrap: wrap; gap: 16px; }
  .card { background: #fff; border-radius: 12px; padding: 16px;
          min-width: 220px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .card.good { border-left: 4px solid #00b894; }
  .card .dest { font-size: 1.1rem; font-weight: 600; }
  .card .meta { font-size: 0.8rem; color: #636e72; margin: 4px 0 8px; }
  .card .price { font-size: 1rem; margin-bottom: 4px; }
  .card .cpm { font-size: 0.9rem; color: #00b894; font-weight: 600; }
  .card .amadeus { font-size: 0.75rem; color: #636e72; margin-top: 6px; }
  .filters { margin: 12px 0; display: flex; gap: 8px; }
  .filters button { padding: 6px 16px; border: 1px solid #dfe6e9; border-radius: 20px;
                    background: #fff; cursor: pointer; font-size: 0.85rem; }
  .filters button.active { background: #0984e3; color: #fff; border-color: #0984e3; }
  table { width: 100%; border-collapse: collapse; background: #fff;
          border-radius: 12px; overflow: hidden;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-size: 0.85rem; }
  th { background: #f8f9fa; padding: 10px 12px; text-align: left;
       font-weight: 600; border-bottom: 1px solid #dfe6e9; }
  td { padding: 10px 12px; border-bottom: 1px solid #f1f2f6; }
  tr:last-child td { border-bottom: none; }
  tr.good td:first-child { border-left: 3px solid #00b894; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
           font-size: 0.75rem; font-weight: 600; }
  .badge.sia { background: #dfe6e9; color: #2d3436; }
  .badge.scoot { background: #ffeaa7; color: #2d3436; }
  .badge.good { background: #55efc4; color: #00695c; }
  .hidden { display: none; }
</style>
</head>
<body>
<header>
  <h1>✈️ Spontaneous Escape Deals</h1>
  <p>Last scraped: {{ run_at }} &nbsp;|&nbsp; Next run: {{ next_run }}</p>
</header>

{% if good_deals %}
<div class="section-title">✅ Good Deals ({{ good_deals|length }})</div>
<div class="cards">
  {% for d in good_deals %}
  <div class="card good">
    <div class="dest">SIN → {{ d.destination }} <span class="badge {{ d.airline|lower }}">{{ d.airline }}</span></div>
    <div class="meta">{{ d.destination_city }} &nbsp;|&nbsp; {{ d.cabin }} &nbsp;|&nbsp; Travel: {{ d.travel_date }} &nbsp;|&nbsp; Book by: {{ d.book_by }}</div>
    <div class="price">SGD {{ "%.0f"|format(d.cash_total) }} (tax: SGD {{ "%.0f"|format(d.tax) }}, base: SGD {{ "%.0f"|format(d.cash_base) }})</div>
    {% if d.cpm_kf %}
    <div class="cpm">KF: {{ "{:,}".format(d.kf_miles) }} miles &rarr; {{ "%.2f"|format(d.cpm_kf) }}¢/mile ✅</div>
    {% endif %}
    {% if d.cpm_flair %}
    <div class="cpm">Flair: {{ "{:,}".format(d.flair_miles) }} pts &rarr; {{ "%.2f"|format(d.cpm_flair) }}¢/mile</div>
    {% endif %}
    {% if d.amadeus_cheapest_date %}
    <div class="amadeus">💡 Cheapest nearby: {{ d.amadeus_cheapest_date }} @ SGD {{ "%.0f"|format(d.amadeus_cheapest_price) }}</div>
    {% endif %}
  </div>
  {% endfor %}
</div>
{% else %}
<p style="color:#636e72;margin:16px 0">No deals above threshold this run.</p>
{% endif %}

<div class="section-title">All Deals ({{ all_deals|length }})</div>
<div class="filters">
  <button class="active" onclick="filter('all', this)">All</button>
  <button onclick="filter('SIA', this)">SIA</button>
  <button onclick="filter('Scoot', this)">Scoot</button>
</div>
<table>
  <thead>
    <tr>
      <th>Airline</th><th>Route</th><th>City</th><th>Cabin</th>
      <th>Travel Date</th><th>Book By</th>
      <th>Total (SGD)</th><th>Tax</th><th>Base</th>
      <th>Miles</th><th>CPM (¢)</th><th>Deal?</th>
      <th>Amadeus Alt</th>
    </tr>
  </thead>
  <tbody>
    {% for d in all_deals %}
    <tr class="{% if d.is_good_deal %}good{% endif %} row-{{ d.airline }}">
      <td><span class="badge {{ d.airline|lower }}">{{ d.airline }}</span></td>
      <td>SIN → {{ d.destination }}</td>
      <td>{{ d.destination_city }}</td>
      <td>{{ d.cabin }}</td>
      <td>{{ d.travel_date }}</td>
      <td>{{ d.book_by }}</td>
      <td>{{ "%.0f"|format(d.cash_total) }}</td>
      <td>{{ "%.0f"|format(d.tax) }}</td>
      <td>{{ "%.0f"|format(d.cash_base) }}</td>
      <td>
        {% if d.kf_miles %}KF {{ "{:,}".format(d.kf_miles) }}{% endif %}
        {% if d.flair_miles %}Flair {{ "{:,}".format(d.flair_miles) }}{% endif %}
      </td>
      <td>
        {% if d.cpm_kf %}{{ "%.2f"|format(d.cpm_kf) }}{% endif %}
        {% if d.cpm_flair %}{{ "%.2f"|format(d.cpm_flair) }}{% endif %}
      </td>
      <td>{% if d.is_good_deal %}<span class="badge good">✅</span>{% endif %}</td>
      <td>
        {% if d.amadeus_cheapest_date %}{{ d.amadeus_cheapest_date }} @ {{ "%.0f"|format(d.amadeus_cheapest_price) }}{% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<script>
function filter(airline, btn) {
  document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('tbody tr').forEach(row => {
    row.classList.toggle('hidden',
      airline !== 'all' && !row.classList.contains('row-' + airline)
    );
  });
}
</script>
</body>
</html>
```

- [ ] **Step 2: Create `src/dashboard.py`**

```python
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
```

- [ ] **Step 3: Smoke test dashboard generation**

```bash
python -c "
from src.models import Deal
from src.dashboard import generate_dashboard
d = Deal(airline='SIA', origin='SIN', destination='BKK', destination_city='Bangkok',
         destination_country='TH', cabin='Economy', travel_date='2026-05-10',
         book_by='2026-04-20', cash_total=180.0, tax=42.0, cash_base=138.0,
         scraped_at='2026-04-15T00:05:00+00:00', kf_miles=7500, cpm_kf=1.84, is_good_deal=True)
generate_dashboard([d], run_at='2026-04-15 00:05 SGT')
print('Dashboard written to docs/index.html')
"
```

Open `docs/index.html` in a browser and verify the card and table render correctly.

- [ ] **Step 4: Commit**

```bash
git add templates/dashboard.html.j2 src/dashboard.py docs/index.html
git commit -m "feat: add HTML dashboard generator"
```

---

## Task 10: Telegram Notifier

**Files:**
- Create: `src/notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_notifier.py
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_notifier.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `src/notifier.py`**

```python
from __future__ import annotations
import asyncio
import logging
import os
from datetime import date
from telegram import Bot
from src.models import Deal

logger = logging.getLogger(__name__)


def build_message(deals: list[Deal]) -> str:
    today = date.today().strftime("%d %b %Y")
    good = sorted(
        [d for d in deals if d.is_good_deal],
        key=lambda d: d.cpm_kf or d.cpm_flair or 0,
        reverse=True,
    )

    if not good:
        return f"✈️ Spontaneous Escape scraped ({today}) — no deals above threshold this run."

    lines = [f"🛫 <b>Spontaneous Escape — {today}</b>\n"]
    lines.append(f"✅ GOOD DEALS ({len(good)} found)")
    lines.append("─" * 22)

    for d in good:
        lines.append(f"\n<b>{d.airline}</b> | SIN→{d.destination} | {d.travel_date}")
        lines.append(f"{d.cabin} | SGD {d.cash_total:.0f} (tax: SGD {d.tax:.0f})")
        if d.cpm_kf:
            lines.append(f"KF: {d.kf_miles:,} miles → {d.cpm_kf:.2f}¢/mile ✅")
        if d.cpm_flair:
            lines.append(f"Flair: {d.flair_miles:,} pts → {d.cpm_flair:.2f}¢/mile")
        if d.amadeus_cheapest_date:
            lines.append(f"💡 Cheapest nearby: {d.amadeus_cheapest_date} @ SGD {d.amadeus_cheapest_price:.0f}")

    return "\n".join(lines)


def send_telegram(deals: list[Deal]) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    message = build_message(deals)
    asyncio.run(_send(token, chat_id, message))


async def _send(token: str, chat_id: str, text: str) -> None:
    bot = Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    logger.info("Telegram notification sent")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_notifier.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/notifier.py tests/test_notifier.py
git commit -m "feat: add Telegram notifier"
```

---

## Task 11: Main Orchestrator

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: Create `src/main.py`**

```python
from __future__ import annotations
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from src.scrapers.sia import scrape_sia
from src.scrapers.scoot import scrape_scoot
from src.cpm_calculator import enrich_deal, filter_excluded
from src.amadeus_client import get_cheapest_date
from src.storage import save_run
from src.dashboard import generate_dashboard
from src.notifier import send_telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    run_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M SGT")

    logger.info("Scraping SIA Spontaneous Escapes...")
    sia_deals = scrape_sia()

    logger.info("Scraping Scoot Spontaneous Escapes...")
    scoot_deals = scrape_scoot()

    all_deals = sia_deals + scoot_deals
    logger.info(f"Total scraped: {len(all_deals)}")

    filtered = filter_excluded(all_deals)
    logger.info(f"After region filter: {len(filtered)}")

    enriched = [enrich_deal(d) for d in filtered]
    good_count = sum(1 for d in enriched if d.is_good_deal)
    logger.info(f"Good deals: {good_count}")

    logger.info("Fetching Amadeus cheapest dates...")
    for deal in enriched:
        cheapest_date, cheapest_price = get_cheapest_date(
            deal.origin, deal.destination, deal.travel_date
        )
        deal.amadeus_cheapest_date = cheapest_date
        deal.amadeus_cheapest_price = cheapest_price

    save_run(enriched)
    logger.info("Saved to history.json")

    generate_dashboard(enriched, run_at=run_at)
    logger.info("Dashboard regenerated at docs/index.html")

    send_telegram(enriched)
    logger.info("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run full suite**

```bash
pytest -v
```
Expected: all tests pass.

- [ ] **Step 3: Local end-to-end test (requires `.env` with real credentials)**

```bash
cp .env.example .env
# Fill in AMADEUS_CLIENT_ID, AMADEUS_CLIENT_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
python -m src.main
```

Expected: scraper runs, dashboard written to `docs/index.html`, Telegram message received.

- [ ] **Step 4: Commit**

```bash
git add src/main.py
git commit -m "feat: add main orchestrator"
```

---

## Task 12: GitHub Actions & GitHub Pages

**Files:**
- Create: `.github/workflows/scrape.yml`
- Create: `docs/.nojekyll`

- [ ] **Step 1: Create `docs/.nojekyll`** (tells GitHub Pages to serve raw HTML, not Jekyll)

```bash
touch docs/.nojekyll
```

- [ ] **Step 2: Create `.github/workflows/scrape.yml`**

```yaml
name: Scrape Spontaneous Escapes

on:
  schedule:
    - cron: "5 16 14 * *"   # 15th 00:05 SGT (16:05 UTC on 14th)
    - cron: "0 1 22 * *"    # 22nd 09:00 SGT (01:00 UTC)
    - cron: "0 1 1 * *"     # 1st 09:00 SGT  (01:00 UTC)
  workflow_dispatch:          # allow manual trigger from GitHub UI

jobs:
  scrape:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium --with-deps

      - name: Run scraper
        env:
          AMADEUS_CLIENT_ID: ${{ secrets.AMADEUS_CLIENT_ID }}
          AMADEUS_CLIENT_SECRET: ${{ secrets.AMADEUS_CLIENT_SECRET }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -m src.main

      - name: Commit updated data and dashboard
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/history.json docs/index.html
          git diff --staged --quiet || git commit -m "chore: update deals $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/scrape.yml docs/.nojekyll
git commit -m "ci: add GitHub Actions cron workflow"
```

- [ ] **Step 4: Create GitHub repo and push**

```bash
# Option A — if gh CLI is installed:
gh repo create SpontaneousEscape --private --source=. --push

# Option B — manual:
# 1. Go to github.com → New repository → name: SpontaneousEscape → Create
# 2. Then run:
git remote add origin https://github.com/<your-username>/SpontaneousEscape.git
git push -u origin master
```

- [ ] **Step 5: Add secrets to GitHub repo**

Go to: `github.com/<username>/SpontaneousEscape` → Settings → Secrets and variables → Actions → New repository secret.

Add all four:
- `AMADEUS_CLIENT_ID`
- `AMADEUS_CLIENT_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

- [ ] **Step 6: Enable GitHub Pages**

Go to: `github.com/<username>/SpontaneousEscape` → Settings → Pages → Source: **Deploy from a branch** → Branch: `master` → Folder: `/docs` → Save.

Dashboard will be live at: `https://<username>.github.io/SpontaneousEscape/`

- [ ] **Step 7: Trigger a manual run to verify the workflow works**

Go to: Actions tab → "Scrape Spontaneous Escapes" → Run workflow → Run workflow.

Watch the logs. If it passes, check your Telegram for the notification and visit the GitHub Pages URL for the dashboard.

---

## Self-Review

**Spec coverage check:**
- ✅ SIA + Scoot scrapers (Tasks 6, 7)
- ✅ Excluded regions: Middle East, Africa, India (Task 3)
- ✅ CPM = (cash - tax) / miles (Task 4)
- ✅ KrisFlyer award chart, zone-based (Task 3)
- ✅ Scoot Flair 100pts = SGD 1 (Task 4)
- ✅ KF threshold ≥ 1.5¢, Flair ≥ 0.8¢ (Task 4)
- ✅ Amadeus cheapest-date lookup (Task 8)
- ✅ history.json storage (Task 5)
- ✅ HTML dashboard (Task 9)
- ✅ Telegram notification (Task 10)
- ✅ GitHub Actions cron: 15th 00:05, 22nd 09:00, 1st 09:00 SGT (Task 12)
- ✅ GitHub Pages hosting (Task 12)

# Spontaneous Escape Scraper — Design Spec

**Date:** 2026-04-19
**Status:** Approved

---

## Goal

Scrape SIA and Scoot Spontaneous Escape deals 3× per month, calculate cents-per-mile value against KrisFlyer and Scoot Flair award rates, flag good deals, and deliver results via Telegram notification and a local HTML dashboard.

---

## Section 1 — Architecture

All logic lives in a plain Python application. GitHub Actions is the scheduler and runner only — it executes `python main.py` on a cron schedule with secrets injected as environment variables.

```
ClaudeProjects/SpontaneousEscape/
└── Python app (all logic)

GitHub Actions
└── runs: python main.py
    └── on cron schedule (3× per month)
        with secrets as env vars
```

**Project location:** `ClaudeProjects/SpontaneousEscape/` — own git repository for GitHub Actions.

---

## Section 2 — Data Model & Scraping

Each scraped deal produces one `Deal` record:

```python
@dataclass
class Deal:
    airline: str                     # "SIA" | "Scoot"
    origin: str                      # always "SIN"
    destination: str                 # IATA code e.g. "BKK"
    destination_city: str
    destination_country: str
    cabin: str                       # "Economy" | "Business"
    travel_date: str                 # "2026-05-10"
    book_by: str                     # "2026-04-20"
    cash_total: float                # SGD incl. tax
    tax: float                       # SGD
    cash_base: float                 # cash_total - tax
    kf_miles: int | None             # KrisFlyer miles required (SIA only)
    flair_miles: int | None          # Scoot Flair miles required (Scoot only)
    cpm_kf: float | None             # SGD cents per KF mile
    cpm_flair: float | None          # SGD cents per Flair mile
    amadeus_cheapest_date: str | None
    amadeus_cheapest_price: float | None
    is_good_deal: bool
    scraped_at: str                  # ISO timestamp
```

**Scraping strategy:** Playwright (headless Chromium) renders JS-heavy pages and extracts deal cards. Both SIA and Scoot Spontaneous Escapes are single-page listings — no pagination.

**Excluded regions** (filtered before any processing):
- Middle East: AE, SA, QA, BH, KW, OM, YE, JO, IQ, IR, IL, SY, LB
- Africa: all 54 country codes
- India: IN

**Source URLs:**
- SIA: `https://www.singaporeair.com/en_UK/sg/promotions/spontaneous-escapes/`
- Scoot: `https://www.flyscoot.com/en/spontaneous-escape`

---

## Section 3 — CPM Calculation & Deal Flagging

**Formula:**
```
CPM = (cash_total - tax) / miles_required × 100   [SGD cents per mile]
```
Higher CPM = each mile is worth more = better deal to redeem miles.

### KrisFlyer Award Chart (Economy Saver, one-way from SIN)

| Zone | Destinations (examples) | Miles |
|------|--------------------------|-------|
| 1 | KUL, BKK, CGK, MNL, SGN, HAN, RGN, PNH | 7,500 |
| 2a | HKG, TPE, MFM | 17,500 |
| 2b | NRT, HND, KIX, ICN, GMP, PEK, PVG, CTU | 22,500 |
| 3 | SYD, MEL, BNE, PER, AKL | 28,500 |
| 4 | LHR, CDG, FRA, MUC, AMS, LAX, SFO, JFK | 62,500 |

Business class: 2× the Economy Saver miles (e.g. Zone 1 Business = 15,000 miles one-way).

### Scoot Flair Redemption

Fixed rate: 100 Flair points = SGD 1.00.
`flair_miles = cash_base × 100` (derived). CPM is always 1.0¢ at standard rate — all Scoot deals pass the 0.8¢ threshold. The Flair column is shown for budgeting (how many points this deal costs), not for filtering.

### Deal Thresholds

| Program | Good Deal Threshold |
|---------|---------------------|
| KrisFlyer | CPM ≥ 1.5 SGD cents/mile |
| Scoot Flair | CPM ≥ 0.8 SGD cents/mile |

### Amadeus Integration

Queries `flight-offers-search` for ±15 days around each deal's travel date to surface a cheaper alternative date. Free tier: 2,000 calls/month (well within budget for 3× monthly runs). Uses test environment credentials.

---

## Section 4 — Storage & Dashboard

### Storage

Single `data/history.json` committed to the repo after each run:

```json
{
  "runs": [
    {
      "run_at": "2026-04-15T00:05:00+08:00",
      "deals": []
    }
  ]
}
```

Latest run is always `runs[-1]`. Full history preserved across all runs.

### HTML Dashboard

`docs/index.html` — Jinja2 template, regenerated each run, single self-contained file (all CSS/JS inline, no external dependencies). Matches ExpenseTracker pattern.

**Layout:**
- **Header:** last scraped timestamp, next scheduled run date
- **Good Deals panel:** highlighted cards for `is_good_deal = True`, sorted by CPM descending
- **Full deals table:** all deals with JS toggle buttons to filter by airline (SIA / Scoot)
- **Each deal shows:** destination, travel date, book-by date, cash total, tax, base fare, miles required, CPM, Amadeus cheapest-date alternative
- **Color coding:** green = good deal, grey = below threshold

---

## Section 5 — Notifications & Scheduling

### Telegram Notification

Sent after each run. If good deals exist:

```
🛫 Spontaneous Escape — 15 Apr 2026

✅ GOOD DEALS (3 found)
──────────────────────
SIA | SIN→BKK | 10 May
Economy | SGD 180 (tax: SGD 42)
KF: 7,500 miles → 1.84¢/mile ✅

Scoot | SIN→NRT | 12 May
Economy | SGD 310 (tax: SGD 55)
Flair: 25,500 pts → 1.00¢/mile ⚠️

📊 Full dashboard: https://<username>.github.io/SpontaneousEscape/
```

If no good deals: single message — `"Spontaneous Escape scraped — no deals above threshold this run."`

### GitHub Actions Schedule

| Run | Purpose | SGT | UTC Cron |
|-----|---------|-----|----------|
| 1st | Right after release | 15th 00:05 | `5 16 14 * *` |
| 2nd | Follow-up check | 22nd 09:00 | `0 1 22 * *` |
| 3rd | Pre-release check | 1st 09:00 | `0 1 1 * *` |

### Secrets (stored in GitHub repo secrets)

| Secret | Purpose |
|--------|---------|
| `AMADEUS_CLIENT_ID` | Amadeus API auth |
| `AMADEUS_CLIENT_SECRET` | Amadeus API auth |
| `TELEGRAM_BOT_TOKEN` | Telegram bot |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

---

## Tech Stack

| Library | Purpose |
|---------|---------|
| `playwright` | JS-rendered page scraping |
| `amadeus` | Flight search API |
| `python-telegram-bot` | Telegram notifications |
| `jinja2` | HTML dashboard templating |
| `pytest` | Tests |
| `python-dotenv` | Local env var loading |

---

## File Structure

```
SpontaneousEscape/
├── .github/workflows/scrape.yml   — GitHub Actions cron
├── src/
│   ├── scrapers/
│   │   ├── sia.py                 — SIA page scraper
│   │   └── scoot.py               — Scoot page scraper
│   ├── award_charts.py            — KrisFlyer + Flair static data
│   ├── cpm_calculator.py          — CPM formula + deal flagging
│   ├── amadeus_client.py          — Amadeus API wrapper
│   ├── storage.py                 — history.json read/write
│   ├── dashboard.py               — HTML generation
│   ├── notifier.py                — Telegram message builder + sender
│   └── main.py                    — orchestrator
├── templates/dashboard.html.j2    — Jinja2 dashboard template
├── data/history.json              — persisted deal history
├── docs/index.html                — generated dashboard
├── tests/
│   ├── test_award_charts.py
│   ├── test_cpm_calculator.py
│   ├── test_storage.py
│   └── fixtures/
├── requirements.txt
├── .env.example
└── docs/superpowers/specs/2026-04-19-spontaneous-escape-design.md
```

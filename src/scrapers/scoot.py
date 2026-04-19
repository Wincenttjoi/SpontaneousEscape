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
    "Gold Coast": "OOL",
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

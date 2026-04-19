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

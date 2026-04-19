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

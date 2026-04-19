from __future__ import annotations
from dataclasses import dataclass
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

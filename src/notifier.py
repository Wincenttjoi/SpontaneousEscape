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
        return f"Spontaneous Escape scraped ({today}) — no deals above threshold this run."

    lines = [f"<b>Spontaneous Escape — {today}</b>\n"]
    lines.append(f"GOOD DEALS ({len(good)} found)")
    lines.append("─" * 22)

    for d in good:
        lines.append(f"\n<b>{d.airline}</b> | SIN→{d.destination} | {d.travel_date}")
        lines.append(f"{d.cabin} | SGD {d.cash_total:.0f} (tax: SGD {d.tax:.0f})")
        if d.cpm_kf:
            lines.append(f"KF: {d.kf_miles:,} miles → {d.cpm_kf:.2f}c/mile")
        if d.cpm_flair:
            lines.append(f"Flair: {d.flair_miles:,} pts → {d.cpm_flair:.2f}c/mile")
        if d.amadeus_cheapest_date:
            lines.append(f"Cheapest nearby: {d.amadeus_cheapest_date} @ SGD {d.amadeus_cheapest_price:.0f}")

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

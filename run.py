"""Check prices of every product listed in the Google Sheet, log them and send Telegram alerts.

    python run.py                 # one check (for Task Scheduler / cron)
    python run.py --every 60      # keep running, check every 60 minutes
    python run.py --demo-discount 15   # pretend prices fell 15% (to try alerts on a static site)
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

from monitor import prices, telegram
from monitor.check import evaluate, failed
from monitor.sheet import PriceSheet

log = logging.getLogger("monitor")


def check_all(sheet: PriceSheet, token: str, chat_ids: list[str], demo_discount: float) -> None:
    rows = sheet.rows()
    if not rows:
        log.warning("No product URLs in the Products tab yet")
        return
    session = prices.make_session()
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    updates, history, alerts = [], [], []
    for row in rows:
        try:
            page = prices.fetch(session, row.url, row.selector)
        except Exception as exc:  # one broken page must not stop the rest
            log.warning("%s: %s", row.url, exc)
            updates.append((row, failed(exc, checked_at)))
            continue
        if demo_discount:
            page.price = round(page.price * (1 - demo_discount / 100), 2)
        result = evaluate(row, page, checked_at)
        updates.append((row, result.fields))
        history.append([checked_at, result.fields["Product"], row.url, page.price, page.currency])
        if result.alert:
            alerts.append(result.alert)
        log.info("%s: %s%.2f", result.fields["Product"][:50], page.currency, page.price)
        time.sleep(0.5)  # be gentle with the shop

    sheet.save(updates, history)
    if alerts:
        telegram.send(token, chat_ids, "\n\n".join(alerts))
    log.info("Checked %d products, %d alerts", len(rows), len(alerts))


def main() -> int:
    ap = argparse.ArgumentParser(description="Price monitor: Google Sheets + Telegram alerts")
    ap.add_argument("--every", type=float, help="repeat every N minutes instead of running once")
    ap.add_argument("--demo-discount", type=float, default=0,
                    help="DEMO ONLY: lower every scraped price by this percent")
    args = ap.parse_args()

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    sheet_id = os.getenv("SHEET_ID", "")
    if not sheet_id:
        log.error("Set SHEET_ID in .env (the long id from the Google Sheet URL)")
        return 2
    sheet = PriceSheet(os.getenv("GOOGLE_CREDENTIALS", "service_account.json"), sheet_id)
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_ids = [c for c in os.getenv("TELEGRAM_CHAT_IDS", "").replace(" ", "").split(",") if c]

    while True:
        try:
            check_all(sheet, token, chat_ids, args.demo_discount)
        except Exception:
            if not args.every:
                raise
            log.exception("Check failed, will retry next round")
        if not args.every:
            return 0
        time.sleep(args.every * 60)


if __name__ == "__main__":
    sys.exit(main())

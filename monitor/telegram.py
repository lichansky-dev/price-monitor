"""Minimal Telegram Bot API client for price alerts."""
import logging

import requests

log = logging.getLogger(__name__)


def send(token: str, chat_ids: list[str], text: str) -> None:
    if not token or not chat_ids:
        log.info("Telegram is not configured, alert not sent:\n%s", text)
        return
    for chat_id in chat_ids:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                      "disable_web_page_preview": True},
                timeout=20,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            # Don't let a Telegram outage stop the price check
            # The token is part of the URL, keep it out of the logs
            log.error("Telegram alert to %s failed: %s", chat_id, str(exc).replace(token, "***"))

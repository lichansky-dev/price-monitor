# Price Monitor: Google Sheets + Telegram Alerts

Tracks product prices on any online store, keeps the full price history in a **Google Sheet**, and sends a **Telegram alert** the moment a price drops, reaches your target, or hits an all-time low.

Built for shop owners watching competitors, resellers hunting deals, and procurement teams waiting for the right price.

## How it works

1. You paste product links into the **Products** tab of a Google Sheet and, optionally, a target price.
2. The script visits every link on a schedule and reads the current price.
3. The sheet updates itself: current, previous and lowest price, change in %, last check time and status. Every check is also logged to the **History** tab.
4. If something interesting happens, you get one Telegram message:

```
📉 Sharp Objects
Now £42.08: dropped from £47.82 (-12.00%); reached your target £45.00; lowest price ever tracked
Open product
```

No code is needed to add or remove products: the client manages everything from the sheet.

## Features

- **Google Sheet as the control panel**: add a URL and a target price, and it is monitored from the next run
- Price drops shown in green, rises in red; prices at or below target in bold; a chart compares current, lowest and target prices
- Full **price history** for analysis or your own charts
- **Telegram alerts** to one or many chats, combined into a single message per run; no spam when nothing changed
- Works on most shops out of the box (schema.org `itemprop=price`, Open Graph price tags, common price classes). For unusual sites, put a CSS selector in the **CSS selector** column
- Understands `£51.77`, `$1,299.00`, `1 299,00 грн`, `1.299,50 €`
- Robust: retries on network errors, one broken page never stops the run, errors are written to the **Status** column
- Efficient: all sheet updates are sent in two API calls per run, well inside Google's free quota

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Linux/macOS: cp .env.example .env
```

1. **Google access.** In Google Cloud, create a project, enable the *Google Sheets API* and *Google Drive API*, create a service account and download its JSON key as `service_account.json`.
2. **Sheet.** Create a Google Sheet and share it with the service account's `client_email` as **Editor**. Put the sheet id (the long part of its URL) into `.env` as `SHEET_ID`.
3. **Telegram.** Create a bot with [@BotFather](https://t.me/BotFather), put its token into `TELEGRAM_TOKEN`, press **Start** in the bot, and put your chat id into `TELEGRAM_CHAT_IDS` (several ids separated by commas).
4. Run `python setup_sheet.py` once. It creates the tabs, formatting and chart.
5. Optional: `python seed_demo.py` adds 8 demo products from books.toscrape.com.

## Running

```bash
python run.py                     # one check
python run.py --every 60          # keep running, check every hour
python run.py --demo-discount 15  # DEMO: pretend prices fell 15% to see the alerts
```

**On a schedule** (recommended):

- Windows Task Scheduler:
  `schtasks /Create /SC HOURLY /TN "Price Monitor" /TR "C:\path\to\.venv\Scripts\python.exe C:\path\to\run.py"`
- Linux/macOS cron (every hour):
  `0 * * * * cd /path/to/price-monitor && .venv/bin/python run.py >> monitor.log 2>&1`

Tests: `python -m pytest`

## Project structure

```
run.py               entry point: one check or a loop
setup_sheet.py       one-time sheet formatting and chart
seed_demo.py         demo products
monitor/prices.py    page download and price/name extraction
monitor/check.py     what changed and whether to alert (pure logic, fully tested)
monitor/sheet.py     Google Sheets read/write (gspread)
monitor/telegram.py  Telegram Bot API alerts
tests/               price parsing and alert rules
```

## Tech stack

Python 3.12 · gspread + Google service account · requests · BeautifulSoup4 + lxml · Telegram Bot API · pytest

## Need it for your store?

The same setup works for competitor price tracking, marketplace listings, stock availability checks or any other "watch a page and tell me when it changes" task, with alerts to Telegram, email or Slack.

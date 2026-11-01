"""Fill the Products tab with demo products from books.toscrape.com (safe to re-run)."""
import os

from dotenv import load_dotenv

from monitor.sheet import COL, HEADERS, PriceSheet

BASE = "https://books.toscrape.com/catalogue/"
DEMO = [  # (url slug, target price)
    ("a-light-in-the-attic_1000", 45),
    ("tipping-the-velvet_999", 50),
    ("soumission_998", ""),
    ("sharp-objects_997", 45),
    ("sapiens-a-brief-history-of-humankind_996", 50),
    ("the-requiem-red_995", ""),
    ("the-black-maria_991", 48),
    ("libertarianism-for-beginners_982", ""),
]

load_dotenv()
sheet = PriceSheet(os.getenv("GOOGLE_CREDENTIALS", "service_account.json"), os.environ["SHEET_ID"])
existing = {r.url for r in sheet.rows()}
new_rows = []
for slug, target in DEMO:
    url = f"{BASE}{slug}/index.html"
    if url not in existing:
        row = [""] * len(HEADERS)
        row[COL["URL"]], row[COL["Target price"]] = url, target
        new_rows.append(row)
if new_rows:
    sheet.products.append_rows(new_rows, value_input_option="USER_ENTERED")
print(f"Added {len(new_rows)} demo products")

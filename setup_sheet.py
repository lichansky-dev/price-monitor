"""Create the tabs and apply formatting and the chart. Run once after sharing the sheet."""
import os

from dotenv import load_dotenv

from monitor.sheet import PriceSheet, style

load_dotenv()
sheet = PriceSheet(os.getenv("GOOGLE_CREDENTIALS", "service_account.json"), os.environ["SHEET_ID"])
style(sheet)
print("Sheet is ready:", sheet.book.url)

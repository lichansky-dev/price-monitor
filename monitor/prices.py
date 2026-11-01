"""Fetch a product page and pull out its name and price."""
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

# Tried in order when the sheet gives no selector for a product
PRICE_SELECTORS = [
    "[itemprop=price]",
    "meta[property='product:price:amount']",
    ".product_main .price_color",
    ".price_color",
    ".price",
    "[class*=price]",
]
NAME_SELECTORS = ["[itemprop=name]", ".product_main h1", "h1", "title"]


@dataclass
class PageInfo:
    name: str
    price: float
    currency: str


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def parse_money(text: str) -> tuple[float, str]:
    """'£51.77' -> (51.77, '£'); '1 299,00 грн' -> (1299.0, 'грн')"""
    text = text.replace("\xa0", " ").strip()
    m = re.search(r"\d[\d\s.,]*", text)
    if not m:
        raise ValueError(f"No price in {text!r}")
    number = m.group().strip().replace(" ", "")
    # "1.299,00" or "1299,00" -> decimal comma; "1,299.00" -> thousands comma
    if "," in number and ("." not in number or number.rfind(",") > number.rfind(".")):
        number = number.replace(".", "").replace(",", ".")
    else:
        number = number.replace(",", "")
    currency = (text[: m.start()] + text[m.end():]).strip()
    return float(number), currency


def _text(el) -> str:
    return (el.get("content") or el.get_text(" ", strip=True)) if el else ""


def parse_page(html: str, price_selector: str = "") -> PageInfo:
    soup = BeautifulSoup(html, "lxml")
    selectors = [price_selector] if price_selector else PRICE_SELECTORS
    for sel in selectors:
        for el in soup.select(sel):
            try:
                price, currency = parse_money(_text(el))
            except ValueError:
                continue
            name = next((_text(soup.select_one(s)) for s in NAME_SELECTORS if soup.select_one(s)), "")
            return PageInfo(name=name.strip(), price=price, currency=currency)
    raise ValueError("Price not found on the page" + (f" with selector {price_selector!r}" if price_selector else ""))


def fetch(session: requests.Session, url: str, price_selector: str = "") -> PageInfo:
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return parse_page(resp.text, price_selector)

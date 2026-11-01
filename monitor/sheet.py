"""Google Sheets storage: a 'Products' tab the client edits, and a 'History' log of every check."""
from dataclasses import dataclass

import gspread

PRODUCTS = "Products"
HISTORY = "History"

# Columns of the Products tab. The client fills URL and optionally Target price / CSS selector.
HEADERS = ["URL", "Product", "Current price", "Previous price", "Change %",
           "Lowest price", "Target price", "Currency", "Last checked", "Status", "CSS selector"]
COL = {name: i for i, name in enumerate(HEADERS)}
HISTORY_HEADERS = ["Checked at", "Product", "URL", "Price", "Currency"]


@dataclass
class Row:
    number: int  # 1-based row number in the sheet
    url: str
    name: str
    current: float | None
    lowest: float | None
    target: float | None
    selector: str


def _num(value) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def _bold_header(ws, ncols: int) -> None:
    last = gspread.utils.rowcol_to_a1(1, ncols)
    ws.format(f"A1:{last}", {
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "backgroundColor": {"red": 0.12, "green": 0.31, "blue": 0.47},
    })
    ws.freeze(rows=1)


class PriceSheet:
    def __init__(self, credentials_file: str, sheet_id: str):
        self.book = gspread.service_account(filename=credentials_file).open_by_key(sheet_id)
        self.products = self._tab(PRODUCTS, HEADERS)
        self.history = self._tab(HISTORY, HISTORY_HEADERS)

    def _tab(self, title: str, headers: list[str]):
        try:
            ws = self.book.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = self.book.add_worksheet(title, rows=200, cols=len(headers))
        if ws.row_values(1) != headers:
            ws.update([headers], "A1")
            _bold_header(ws, len(headers))
        return ws

    def rows(self) -> list[Row]:
        result = []
        for i, values in enumerate(self.products.get_all_values()[1:], start=2):
            values += [""] * (len(HEADERS) - len(values))
            url = values[COL["URL"]].strip()
            if not url.startswith("http"):
                continue
            result.append(Row(
                number=i, url=url, name=values[COL["Product"]],
                current=_num(values[COL["Current price"]]),
                lowest=_num(values[COL["Lowest price"]]),
                target=_num(values[COL["Target price"]]),
                selector=values[COL["CSS selector"]].strip(),
            ))
        return result

    def save(self, updates: list[tuple[Row, dict]], history: list[list]) -> None:
        """Write all results in two API calls (Sheets has a per-minute request quota)."""
        data = []
        for row, fields in updates:
            for name, value in fields.items():
                data.append({
                    "range": gspread.utils.rowcol_to_a1(row.number, COL[name] + 1),
                    "values": [[value]],
                })
        if data:
            self.products.batch_update(data, value_input_option="USER_ENTERED")
        if history:
            self.history.append_rows(history, value_input_option="USER_ENTERED")


def style(sheet: "PriceSheet") -> None:
    """One-time cosmetics: widths, number formats, red/green change colours and a price chart."""
    ws = sheet.products
    sid = ws.id
    widths = [320, 260, 110, 110, 90, 110, 110, 80, 140, 160, 140]
    money = {"type": "NUMBER", "pattern": "#,##0.00"}
    reqs = [
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": w}, "fields": "pixelSize"}}
        for i, w in enumerate(widths)
    ]
    for name in ("Current price", "Previous price", "Lowest price", "Target price"):
        reqs.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "startColumnIndex": COL[name], "endColumnIndex": COL[name] + 1},
            "cell": {"userEnteredFormat": {"numberFormat": money}}, "fields": "userEnteredFormat.numberFormat"}})
    change = {"sheetId": sid, "startRowIndex": 1, "startColumnIndex": COL["Change %"], "endColumnIndex": COL["Change %"] + 1}
    for op, color in (("NUMBER_LESS", {"red": 0.8, "green": 0.94, "blue": 0.8}),
                      ("NUMBER_GREATER", {"red": 0.98, "green": 0.8, "blue": 0.8})):
        reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [change],
            "booleanRule": {"condition": {"type": op, "values": [{"userEnteredValue": "0"}]},
                            "format": {"backgroundColor": color}}}}})
    # Price at or below target -> bold green. No commas in the formula: sheets in many locales use ";"
    current = gspread.utils.rowcol_to_a1(2, COL["Current price"] + 1)
    target = gspread.utils.rowcol_to_a1(2, COL["Target price"] + 1)
    reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
        "ranges": [{"sheetId": sid, "startRowIndex": 1, "startColumnIndex": COL["Current price"], "endColumnIndex": COL["Current price"] + 1}],
        "booleanRule": {"condition": {"type": "CUSTOM_FORMULA",
                                      "values": [{"userEnteredValue": f"=({current}<={target})*({target}<>\"\")"}]},
                        "format": {"textFormat": {"bold": True, "foregroundColor": {"red": 0, "green": 0.5, "blue": 0}}}}}}})
    rows = max(len(sheet.rows()) + 1, 2)

    def series(name):
        return {"series": {"sourceRange": {"sources": [{"sheetId": sid, "startRowIndex": 0, "endRowIndex": rows,
                                                        "startColumnIndex": COL[name], "endColumnIndex": COL[name] + 1}]}},
                "targetAxis": "LEFT_AXIS"}
    reqs.append({"addChart": {"chart": {
        "spec": {"title": "Current vs lowest vs target price",
                 "basicChart": {"chartType": "COLUMN", "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
                                "domains": [{"domain": {"sourceRange": {"sources": [{
                                    "sheetId": sid, "startRowIndex": 0, "endRowIndex": rows,
                                    "startColumnIndex": COL["Product"], "endColumnIndex": COL["Product"] + 1}]}}}],
                                "series": [series("Current price"), series("Lowest price"), series("Target price")]}},
        "position": {"overlayPosition": {"anchorCell": {"sheetId": sid, "rowIndex": rows + 2, "columnIndex": 1},
                                         "widthPixels": 800, "heightPixels": 360}}}}})
    hist = sheet.history
    reqs += [
        {"updateDimensionProperties": {
            "range": {"sheetId": hist.id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": w}, "fields": "pixelSize"}}
        for i, w in enumerate([140, 260, 320, 90, 80])
    ]
    sheet.book.batch_update({"requests": reqs})

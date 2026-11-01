import pytest

from monitor.check import evaluate
from monitor.prices import PageInfo, parse_money, parse_page
from monitor.sheet import Row


def row(current=None, lowest=None, target=None):
    return Row(2, "https://shop.test/p/1", "", current, lowest, target, "")


@pytest.mark.parametrize("text, expected", [
    ("£51.77", (51.77, "£")),
    ("$1,299.00", (1299.0, "$")),
    ("1 299,00 грн", (1299.0, "грн")),
    ("1.299,50 €", (1299.5, "€")),
])
def test_parse_money(text, expected):
    assert parse_money(text) == expected


def test_parse_page_finds_price_and_name():
    html = '<h1>Desk Lamp</h1><p class="price">$24.90</p>'
    assert parse_page(html) == PageInfo("Desk Lamp", 24.9, "$")


def test_custom_selector():
    html = '<span class="old">$30</span><b id="now">$25</b><h1>X</h1>'
    assert parse_page(html, "#now").price == 25


def test_first_check_no_alert():
    r = evaluate(row(), PageInfo("Lamp", 20, "$"), "t")
    assert r.alert is None
    assert r.fields["Current price"] == 20 and r.fields["Lowest price"] == 20
    assert "Previous price" not in r.fields


def test_price_drop_alerts():
    r = evaluate(row(current=20, lowest=18), PageInfo("Lamp", 19, "$"), "t")
    assert r.fields["Previous price"] == 20 and r.fields["Change %"] == -5.0
    assert "dropped from $20.00 (-5.00%)" in r.alert
    assert "lowest" not in r.alert


def test_new_low_and_target():
    r = evaluate(row(current=20, lowest=18, target=17), PageInfo("Lamp", 16.5, "$"), "t")
    assert "reached your target" in r.alert and "lowest price ever" in r.alert
    assert r.fields["Lowest price"] == 16.5


def test_price_rise_no_alert():
    r = evaluate(row(current=20, lowest=20), PageInfo("Lamp", 22, "$"), "t")
    assert r.alert is None and r.fields["Change %"] == 10.0


def test_target_alert_only_once():
    r = evaluate(row(current=15, lowest=15, target=17), PageInfo("Lamp", 15, "$"), "t")
    assert r.alert is None

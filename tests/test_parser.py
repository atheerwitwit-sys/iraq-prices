import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))
from parser import parse_post, find_prices


def one(text):
    items = parse_post(text)
    assert len(items) == 1, items
    return items[0]


def test_iphone_iqd_full():
    i = one("ايفون 15 برو 256 كيكا السعر 1,150,000 دينار")
    assert i.brand == "iPhone" and "15 Pro" in i.device
    assert i.price == 1_150_000 and i.currency == "IQD"
    assert "256GB" in i.specs


def test_thousand_arabic_digits():
    i = one("Galaxy A55 8/256 بسعر ٤٢٥ الف")
    assert i.brand == "Samsung" and "A55" in i.device
    assert i.price == 425_000 and i.currency == "IQD"
    assert "RAM 8GB" in i.specs and "256GB" in i.specs


def test_usd():
    i = one("Redmi Note 13 بسعر 210$")
    assert i.brand == "Redmi" and i.currency == "USD" and i.price == 210


def test_router():
    i = one("راوتر TP-Link Archer C6 AC1200 بـ 55 الف دينار")
    assert i.kind == "router" and i.brand == "TP-Link"
    assert i.price == 55_000 and i.currency == "IQD"
    assert "AC1200" in i.specs


def test_waraqa_used():
    i = one("ايفون 13 مستعمل نظيف 3 ورقة ونص")
    assert i.price == 350 and i.currency == "USD" and i.condition == "مستعمل"


def test_multi_line_post():
    post = """🔥 عروض اليوم 🔥
    Samsung Galaxy S24 Ultra 12/256
    السعر 1,400,000
    Xiaomi Redmi 13C 4/128 - 145 الف
    ايفون 16 برو ماكس 256 كيكا 1650$
    للاستفسار 07701234567"""
    items = parse_post(post)
    assert len(items) == 3, items
    assert items[0].brand == "Samsung" and items[0].price == 1_400_000
    assert items[1].brand in ("Redmi", "Xiaomi") and items[1].price == 145_000
    assert items[2].currency == "USD" and items[2].price == 1650


def test_phone_number_not_price():
    assert parse_post("سامسونج A15 للاستفسار 07801234567") == []


def test_million():
    p = find_prices("السعر مليون و250")
    assert p == [] or p[0].amount == 1_250_000
    p = find_prices("1 مليون و 250 الف")
    assert p[0].amount == 1_250_000 and p[0].currency == "IQD"


def test_bare_ambiguous():
    i = one("ايفون 14 السعر 850")
    assert i.currency == "?" and i.price == 850


def test_condition_not_leaking():
    items = parse_post("ايفون 13 مستعمل نظيف 3 ورقة ونص\nGalaxy A55 8/256 بسعر ٤٢٥ الف")
    assert items[0].condition == "مستعمل" and items[1].condition == ""
    assert items[1].device == "Samsung Galaxy A55"


def test_single_device_condition_other_line():
    i = one("ايفون 15 برو 256 السعر 900$\nالجهاز مستعمل بطارية 90")
    assert i.condition == "مستعمل"


def test_accessories_ignored():
    assert parse_post("HUAWEI FreeBuds Pro 5 السعر 210,000 دينار") == []
    assert parse_post("Galaxy Watch8 Classic 525,000 د.ع") == []
    assert len(parse_post("راوتر هواوي AX3 بسعر 75 الف")) == 1


def test_ocr_poster():
    txt = """TR
Samsung Galaxy A57 5G
12GB - 512GB 899,000 IQD 1,071,000 IQD
12GB - 256GB 749,000 IQD 870,000 IQD
8GB - 256GB 679,000 IQD 767,000 IQD"""
    items = parse_post(txt, ocr=True)
    assert [i.price for i in items] == [899000, 749000, 679000]
    assert items[0].device == "Samsung Galaxy A57 5G" and items[2].device == "Samsung Galaxy A57 5G"
    assert items[0].specs[:2] == ["RAM 12GB", "512GB"] and items[2].specs[:2] == ["RAM 8GB", "256GB"]

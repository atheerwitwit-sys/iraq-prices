"""سحب الأسعار من المواقع والمتاجر الإلكترونية العراقية.

يجرب بالترتيب:
  1. متاجر Shopify        -> /products.json
  2. متاجر WooCommerce    -> /wp-json/wc/store/v1/products
  3. بيانات JSON-LD (Product/Offer) داخل الصفحة
  4. قراءة نص الصفحة بنفس قارئ المنشورات (parser.parse_post)
"""
from __future__ import annotations

import html
import json
import re
import urllib.request
from urllib.parse import urljoin, urlsplit

from parser import Item, valid_name, price_ok, detect_brand, extract_model, extract_specs, detect_condition, parse_post, normalize

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch(url: str, timeout=30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def _currency(code: str, amount: float) -> str:
    code = (code or "").upper()
    if code in ("USD", "$"):
        return "USD"
    if code in ("IQD", "د.ع", "دينار"):
        return "IQD"
    return "IQD" if amount >= 10_000 else "?"


def _img(src) -> str:
    """نقبل بس روابط صور كاملة https (مو base64 ولا صور محلية)."""
    if isinstance(src, list):
        src = src[0] if src else ""
    if isinstance(src, dict):
        src = src.get("url") or src.get("src") or src.get("contentUrl") or ""
    src = (src or "").strip()
    if src.startswith("//"):
        src = "https:" + src
    return src if re.match(r"https?://", src) and len(src) < 600 else ""


def _make_item(title: str, desc: str, amount: float, currency: str, url: str, image: str = ""):
    m, brand, kind = detect_brand(title)
    if not kind:
        return None
    if not (10 <= amount <= 7_000_000):
        return None
    from parser import NON_DEVICE_RE, STRONG_NON_DEVICE_RE, ROUTER_WORDS
    t_norm = normalize(title)
    # عنوان منتج كامل: أي كلمة إكسسوار بالعنوان = مو جهاز
    if STRONG_NON_DEVICE_RE.search(t_norm) or (NON_DEVICE_RE.search(t_norm) and not ROUTER_WORDS.search(t_norm)):
        return None
    full = f"{title} {desc}"
    device = extract_model(title, m, brand) if brand else normalize(title)[:60]
    if not brand or not valid_name(device, brand):
        return None
    if currency == "?" or not price_ok(kind, amount, currency):
        return None
    return Item(
        device=device,
        brand=brand, kind=kind, specs=extract_specs(full, kind),
        condition=detect_condition(full), price=amount, currency=currency,
        price_text=f"{amount:,.0f} {currency}" if amount == int(amount) else f"{amount:,.2f} {currency}", line=normalize(title)[:300],
        image=_img(image),
    ), url


def shopify(base: str):
    out = []
    for page in range(1, 6):
        try:
            data = json.loads(fetch(urljoin(base, f"/products.json?limit=250&page={page}")))
        except Exception:
            return out
        products = data.get("products") or []
        if not products:
            break
        for p in products:
            v = (p.get("variants") or [{}])[0]
            try:
                amount = float(v.get("price") or 0)
            except ValueError:
                continue
            r = _make_item(p.get("title", ""), re.sub("<[^>]+>", " ", p.get("body_html") or "")[:300],
                           amount, _currency("", amount), urljoin(base, f"/products/{p.get('handle')}"),
                           ((p.get("images") or [{}])[0] or {}).get("src", ""))
            if r:
                out.append(r)
    return out


def woocommerce(base: str):
    out = []
    for page in range(1, 6):
        try:
            data = json.loads(fetch(urljoin(base, f"/wp-json/wc/store/v1/products?per_page=100&page={page}")))
        except Exception:
            return out
        if not isinstance(data, list) or not data:
            break
        for p in data:
            pr = p.get("prices") or {}
            try:
                minor = int(pr.get("currency_minor_unit", 0))
                amount = int(pr.get("price") or 0) / (10 ** minor)
            except (ValueError, TypeError):
                continue
            r = _make_item(html.unescape(p.get("name", "")), re.sub("<[^>]+>", " ", p.get("short_description") or "")[:300],
                           amount, _currency(pr.get("currency_code"), amount), p.get("permalink") or base,
                           ((p.get("images") or [{}])[0] or {}).get("src", ""))
            if r:
                out.append(r)
    return out


def trendmiq(base: str = "https://trendmiq.com"):
    """متجر ترند موبايل: عندهم API عام يرجع كل المنتجات (10 بكل صفحة)."""
    import time
    out, page, total = [], 1, None
    while page <= 200:
        try:
            data = json.loads(fetch(f"https://api.trendmiq.com/user/products?page={page}&limit=10"))
        except Exception as e:
            if not out:
                raise
            print("  ! ترند: توقف عند الصفحة", page, e)
            break
        total = data.get("total", total)
        rows = data.get("data") or []
        if not rows:
            break
        for p in rows:
            amount = float(p.get("price") or 0)
            cat = (p.get("category") or {}).get("name", "")
            key = (p.get("preview") or {}).get("key")
            img = f"https://nbg1.your-objectstorage.com/trend/{key}" if key else ""
            r = _make_item(p.get("title", ""), cat, amount, "IQD", f"https://trendmiq.com/products/{p.get('id')}", img)
            if r:
                out.append(r)
        if total and page * 10 >= total:
            break
        page += 1
        time.sleep(0.7)
    return out


SPECIAL_SITES = {"trendmiq.com": trendmiq}


def json_ld(page_html: str, url: str):
    out = []
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page_html, re.S | re.I):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if "@graph" in d:
                    stack.extend(d["@graph"])
                t = d.get("@type")
                if t == "Product" or (isinstance(t, list) and "Product" in t):
                    offers = d.get("offers") or {}
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    try:
                        amount = float(offers.get("price") or offers.get("lowPrice") or 0)
                    except (ValueError, TypeError):
                        continue
                    r = _make_item(d.get("name", ""), str(d.get("description", ""))[:300], amount,
                                   _currency(offers.get("priceCurrency"), amount), d.get("url") or url, d.get("image"))
                    if r:
                        out.append(r)
                if t == "ItemList":
                    stack.extend(e.get("item", e) for e in d.get("itemListElement", []) if isinstance(e, dict))
            elif isinstance(d, list):
                stack.extend(d)
    return out


OLD_PRICE_RE = re.compile(r"old|original|regular|was|compare|before|strike|line-through|crossed", re.I)


def product_tiles(page_html: str, url: str):
    """قراءة بطاقات المنتجات العامة: عنصر اسم (class فيه product+name/title)
    وعنصر سعر (class فيه price) داخل نفس البطاقة."""
    from bs4 import BeautifulSoup
    from parser import find_prices
    soup = BeautifulSoup(page_html, "html.parser")
    name_els = soup.find_all(class_=re.compile(r"(product|item|card)[-_]*(name|title)|^(name|title)$", re.I))
    out, seen = [], set()
    for ne in name_els:
        title = ne.get_text(" ", strip=True)
        if len(title) < 4:
            continue
        tile = ne
        price_el = None
        for _ in range(6):
            tile = tile.parent
            if tile is None:
                break
            cands = [e for e in tile.find_all(class_=re.compile("price", re.I))
                     if not OLD_PRICE_RE.search(" ".join(e.get("class", []))) and not e.find_parent(["del", "s"])
                     and e.name not in ("del", "s") and re.search(r"\d", e.get_text())]
            if cands:
                # أعمق عنصر سعر (مو الحاوية)
                price_el = min(cands, key=lambda e: len(e.get_text()))
                break
        if not price_el:
            continue
        ptxt = price_el.get_text(" ", strip=True)
        prices = find_prices(ptxt)
        if prices:
            amount, cur = prices[0].amount, prices[0].currency
        else:
            digits = re.sub(r"[^0-9]", "", normalize(ptxt))
            if not digits:
                continue
            amount = float(digits)
            cur = _currency("", amount)
        if cur == "?":
            continue
        a = ne if ne.name == "a" else (ne.find_parent("a") or tile.find("a", href=True))
        link = urljoin(url, a["href"]) if a and a.get("href") else url
        key = (title, amount)
        if key in seen:
            continue
        seen.add(key)
        img_el = tile.find("img")
        img = ""
        if img_el:
            img = img_el.get("data-src") or img_el.get("data-lazy-src") or img_el.get("src") or ""
            img = urljoin(url, img) if img and not img.startswith("data:") else ""
        r = _make_item(title, "", amount, cur, link, img)
        if r:
            out.append(r)
    return out


def page_text(page_html: str) -> str:
    t = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", page_html, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</(p|div|li|h\d|tr|span)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(t)


def scrape_site(url: str):
    """يرجع [(Item, link)]"""
    base = "{0.scheme}://{0.netloc}".format(urlsplit(url))
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    if host in SPECIAL_SITES:
        return SPECIAL_SITES[host](base)
    for fn in (shopify, woocommerce):
        res = fn(base)
        if res:
            return res
    page_html = fetch(url)
    res = json_ld(page_html, url)
    if res:
        return res
    res = product_tiles(page_html, url)
    if res:
        return res
    # من نص الصفحة ناخذ بس الأجهزة اللي بيها اسم شركة (عناوين الأقسام تنترك)
    return [(i, url) for i in parse_post(page_text(page_html), strict=True) if i.brand]

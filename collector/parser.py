"""قراءة اسم الجهاز والمواصفات والسعر من نص منشور أو صفحة.

يدعم الكتابة العراقية الشائعة مثل:
  "ايفون 15 برو 256 كيكا السعر 1,150,000"
  "Galaxy A55 8/256  ٤٢٥ الف"
  "Redmi Note 13 بسعر 210$"
  "راوتر TP-Link Archer C6 بـ 55 الف دينار"
  "ايفون 13 مستعمل نظيف 3 ورقة ونص"   (ورقة = 100 دولار)
العملة تبقى مثل ما مكتوبة بالمنشور (IQD أو USD).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬", "01234567890123456789.,")

# ---------------------------------------------------------------- brands
# (regex, canonical brand, kind)
BRANDS = [
    (r"i\s?phone|ايفون|آيفون|أيفون|ايفن", "iPhone", "phone"),
    (r"samsung|سامسونج|سامسونك|سامسونغ|galaxy|كالكسي|جالكسي|غالاكسي|كلاكسي", "Samsung", "phone"),
    (r"redmi|ريدمي|ردمي", "Redmi", "phone"),
    (r"poco|بوكو", "Poco", "phone"),
    (r"xiaomi|شاومي|شومي|mi\s", "Xiaomi", "phone"),
    (r"huawei|هواوي|هواوى", "Huawei", "phone"),
    (r"honor|هونر|هونور", "Honor", "phone"),
    (r"oppo|اوبو|أوبو", "Oppo", "phone"),
    (r"realme|ريلمي|ريل مي", "Realme", "phone"),
    (r"vivo|فيفو", "Vivo", "phone"),
    (r"infinix|انفنكس|انفينكس|إنفينكس", "Infinix", "phone"),
    (r"tecno|تكنو|تيكنو", "Tecno", "phone"),
    (r"itel|ايتل", "itel", "phone"),
    (r"nokia|نوكيا", "Nokia", "phone"),
    (r"pixel|بكسل|بيكسل", "Google Pixel", "phone"),
    (r"one\s?plus|ون بلس|وان بلس", "OnePlus", "phone"),
    (r"motorola|موتورولا|moto\s", "Motorola", "phone"),
    (r"nothing\s+phone|ناثنك", "Nothing", "phone"),
    (r"ipad|ايباد|آيباد", "iPad", "tablet"),
    # routers
    (r"tp-?link|تي ?بي ?لي?نك", "TP-Link", "router"),
    (r"tenda|تيندا|تندا", "Tenda", "router"),
    (r"d-?link|دي ?لي?نك", "D-Link", "router"),
    (r"mercusys|ميركوسس|مركوسس", "Mercusys", "router"),
    (r"\bzte\b|زد تي اي", "ZTE", "router"),
    (r"netgear|نت كير", "Netgear", "router"),
    (r"mikrotik|مايكروتك|ميكروتك", "MikroTik", "router"),
    (r"ubiquiti|unifi|يوبكويتي", "Ubiquiti", "router"),
    (r"asus|اسوس|أسوس", "ASUS", "router"),
]
BRAND_RES = [(re.compile(r"(?<![\w\u0600-\u06FF])(?:" + p + r")(?![\u0600-\u06FF])", re.I), b, k) for p, b, k in BRANDS]

ROUTER_WORDS = re.compile(r"راوتر|روتر|رواتر|مودم|router|modem|access\s?point|اكسس|mesh|ميش|wi-?fi\s?6|اكستندر|extender|مقوي", re.I)

# Words that should never be treated as part of a model name
STOP_WORDS = re.compile(
    r"^(سعة|السعة|بسعة|السعر|سعر|بسعر|ب|بـ|الف|ألف|دينار|دولار|\$|مستعمل|جديد|نظيف|كفالة|مكفول|ضمان|متوفر|متوفره|"
    r"للبيع|عرض|عروض|خصم|كيكا|جيجا|جيكا|gb|tb|رام|ram|ذاكرة|ذاكره|لون|الوان|اللون|مع|و|نسخة|"
    r"price|new|used|for|sale|only|فقط|ورقة|ورقه|اوراق|مليون|كاش|اقساط|تقسيط)$",
    re.I,
)

# ---------------------------------------------------------------- price
NUM = r"\d{1,3}(?:[.,]\d{3})+|\d+(?:\.\d+)?"
PRICE_PATTERNS = [
    # 1,250,000 دينار / 1250000 IQD / 450 الف
    (re.compile(rf"(?P<n>{NUM})\s*(?P<u>مليون)(?:\s*و\s*(?P<rest>\d{{1,3}})\s*(?:الف|ألف)?)?", re.I), "million"),
    (re.compile(rf"(?P<n>{NUM})\s*(?P<u>الف|ألف|آلاف|k\b)\s*(?:دينار|د\.ع|iqd)?", re.I), "thousand"),
    (re.compile(rf"(?P<n>{NUM})\s*(?P<u>دينار|د\.ع|iqd|ع\.د)", re.I), "iqd"),
    (re.compile(rf"(?P<u>iqd)\s*(?P<n>{NUM})", re.I), "iqd"),
    # dollars
    (re.compile(rf"(?P<n>{NUM})\s*(?P<u>\$|دولار|usd|dollar|﹩)", re.I), "usd"),
    (re.compile(rf"(?P<u>\$|usd)\s*(?P<n>{NUM})", re.I), "usd"),
    # 3 ورقة ونص  (ورقة = 100$)
    (re.compile(rf"(?P<n>{NUM})\s*(?P<u>ورقة|ورقه|اوراق|أوراق|ورقات)(?P<half>\s*و\s*نص|\s*ونص)?", re.I), "waraqa"),
    # السعر 850  / السعر: 1,150,000 (no unit)
    (re.compile(rf"(?:السعر|سعره|سعرها|بسعر|price|السعر\s*:|ب\s*سعر)\s*[:\-=]?\s*(?P<n>{NUM})", re.I), "bare"),
]

STORAGE_RE = re.compile(r"(?<![\d/])(\d{2,4})\s*(?:gb|g\b|جيجا|جيكا|كيكا|كيگا|غيغا|giga)|(\d)\s*(?:tb|تيرا)", re.I)
RAM_STORAGE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*(?:gb|جيجا|كيكا)?\s*[/+\-–]\s*(\d{2,4})(?!\d)", re.I)
RAM_RE = re.compile(r"(?:رام|ram)\s*(\d{1,2})|(\d{1,2})\s*(?:gb)?\s*(?:رام|ram)", re.I)
ROUTER_SPEED_RE = re.compile(r"(?<![a-z])(?:ax|ac|n|be)\s?\d{3,5}|\d{3,5}\s?mbps|wi-?fi\s?[4567]|dual\s?band|دوال باند|ثنائي الموجة", re.I)
CONDITION_USED = re.compile(r"(?<![\w\u0600-\u06FF])(?:مستعمل|مستعمله|مستعملة|مستخدم|used|شبه جديد|اوبن بوكس|open box)(?![\u0600-\u06FF])|بطارية\s*\d{2}\s*%|صحة البطارية", re.I)
CONDITION_NEW = re.compile(r"جديد|new|مسكر|سيل|sealed|كارتونة|بالكارتون", re.I)
# منتجات مو موبايل ولا راوتر (حتى لو بيها اسم شركة مثل Huawei FreeBuds)
NON_DEVICE_RE = re.compile(
    r"watch|ساعة|ساعه|buds|airpods|ايربودز|سماعة|سماعه|earphone|headphone|headset|كفر|cover|case\b|جراب|"
    r"شاحن|charger|كيبل|cable|ماوس|mouse|سكرين|حماية شاشة|screen protector|power ?bank|باور بانك|band\b|سوار|"
    r"speaker|سبيكر|مكبر صوت|ستاند|\bstand\b|holder|vacuum|مكنسة|purifier|\btv\b|تلفزيون|laptop|لابتوب|"
    r"keyboard|كيبورد|pencil|قلم|glasses|نظارات|\bhub\b|موزع|adapter|محول|free ?(?:lace|clip|arc|buds)|fryer|قلاية|"
    r"kettle|غلاية|الغليان|mijia|ميجيا|switch|سويچ|سويج|سويتش|\bnvr\b|\bdvr\b|\bups\b|motherboard|ماذربورد|cooler|liquid|"
    r"monitor|\btuf\b|prime z|zenbook|vivobook|\bssd\b|\bhdd\b|scooter|سكوتر|robot|روبوت|trimmer|shaver|ماكنة حلاقة|"
    r"مقاوم للكسر|لاصق|protector|tempered|زجاج|\bglass\b|انج|inch|بوصة|grooming|"
    r"لجهاز|للجهاز|للايفون|للآيفون|for iphone|for samsung|for galaxy|compatible|متوافق|حافظة|باوربنك|باور بانك|"
    r"backpack|حقيبة|حقيبه|\bbag\b|projector|بروجكتر|بروجيكتر|"
    r"blender|خلاط|\bscale\b|ميزان|\blamp\b|\bbulb\b",
    re.I,
)
# كلمات تأكد إن المنتج مو جهاز حتى لو بيه "WIFI" (لوحات أم، شاشات، ...)
STRONG_NON_DEVICE_RE = re.compile(
    r"pixels|tapo c\d|camera|كاميرا|novastar|led display|ethernet ports|motherboard|ماذربورد|\b[bhzx][4-9]\d0[a-z]?\b|hdmi|monitor|odyssey|\bls\d{2}|\bte[gf]\d|magsafe|بطارية خارجية|kvm|geforce|rtx|splitter|cooler|creator|\brog\b|\btuf\b",
    re.I,
)
TABLET_RE = re.compile(r"\bpad\b|megapad|\btab\b|tablet|تابلت|ايباد|ipad", re.I)
WARRANTY_RE = re.compile(r"كفالة|مكفول|ضمان|warranty", re.I)


@dataclass
class Price:
    amount: float
    currency: str  # "IQD" | "USD" | "?" (غير محدد بالمنشور)
    raw: str


@dataclass
class Item:
    device: str
    brand: str
    kind: str  # phone | router | tablet
    specs: list[str] = field(default_factory=list)
    condition: str = ""  # جديد | مستعمل | ""
    price: float = 0
    currency: str = ""
    price_text: str = ""
    line: str = ""

    def to_dict(self):
        return asdict(self)


def normalize(text: str) -> str:
    text = text.translate(ARABIC_DIGITS)
    text = text.replace("‏", " ").replace("‎", " ").replace("\xa0", " ")
    text = re.sub(r"[ـ]", "", text)  # tatweel
    return text


def _num(s: str) -> float:
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
        return float(re.sub(r"[.,]", "", s))
    return float(s.replace(",", "."))


def find_prices(line: str) -> list[Price]:
    """Return all prices in a line, in IQD or USD as written."""
    line = normalize(line)
    found: list[tuple[int, int, Price]] = []

    def overlaps(a, b):
        return any(not (b <= s or a >= e) for s, e, _ in found)

    for rx, kind in PRICE_PATTERNS:
        for m in rx.finditer(line):
            if overlaps(m.start(), m.end()):
                continue
            n = _num(m.group("n"))
            raw = m.group(0).strip()
            if kind == "million":
                amount = n * 1_000_000
                if m.group("rest"):
                    amount += int(m.group("rest")) * 1000
                p = Price(amount, "IQD", raw)
            elif kind == "thousand":
                p = Price(n * 1000, "IQD", raw)
            elif kind == "iqd":
                p = Price(n * 1000 if n < 5000 else n, "IQD", raw)
            elif kind == "usd":
                p = Price(n, "USD", raw)
            elif kind == "waraqa":
                amount = n * 100 + (50 if m.group("half") else 0)
                p = Price(amount, "USD", raw)
            else:  # bare number after "السعر"
                if n >= 10_000:
                    p = Price(n, "IQD", raw)
                elif 30 <= n < 5000:
                    # "السعر 850" بدون عملة: ممكن 850 الف دينار أو 850 دولار.
                    # ما نخمن: نخلي الرقم مثل ما هو والعملة "غير محددة".
                    p = Price(n, "?", raw)
                else:
                    continue
            if not plausible(p):
                continue
            found.append((m.start(), m.end(), p))
    found.sort(key=lambda t: t[0])
    return [p for _, _, p in found]


def plausible(p: Price) -> bool:
    if p.currency in ("USD", "?"):
        return 10 <= p.amount <= 5000
    return 10_000 <= p.amount <= 7_000_000


def detect_brand(text: str):
    t = normalize(text)
    for rx, brand, kind in BRAND_RES:
        m = rx.search(t)
        if m:
            # كلمة إكسسوار قريبة من اسم الشركة (مثل Galaxy Watch أو Huawei FreeBuds) = مو موبايل
            window = t[max(0, m.start() - 25): m.end() + 35]
            if STRONG_NON_DEVICE_RE.search(window) or (NON_DEVICE_RE.search(window) and not ROUTER_WORDS.search(window)):
                return None, "", ""
            if kind == "phone" and TABLET_RE.search(window):
                return m, brand, "tablet"
            if ROUTER_WORDS.search(t) and brand in ("Huawei", "Xiaomi", "ZTE", "ASUS", "Honor"):
                return m, brand, "router"
            if brand == "ASUS" and not re.search(r"rt-|zenwifi|wifi|wi-fi", t, re.I):
                continue  # ASUS بدون كلمة راوتر = لابتوب أو قطع حاسبة
            return m, brand, kind
    if ROUTER_WORDS.search(t):
        return None, "", "router"
    return None, "", ""


def extract_model(line: str, m: re.Match | None, brand: str) -> str:
    """Build a readable device name: brand + following model tokens."""
    t = normalize(line)
    start = m.end() if m else 0
    tail = t[start:]
    cuts = [m_.start() for rx in (STORAGE_RE, RAM_STORAGE_RE, ROUTER_SPEED_RE, RAM_RE) for m_ in [rx.search(tail)] if m_]
    if cuts:
        tail = tail[:min(cuts)]
    tail = re.split(r"[\n|،,؛;:\-–—(){}\[\]]|السعر|بسعر|سعر", tail)[0]
    tokens = []
    for tok in tail.split():
        tok_clean = tok.strip(".*•✅🔥⭐️💥📱👇")
        if not tok_clean:
            continue
        if STOP_WORDS.match(tok_clean) or STORAGE_RE.fullmatch(tok_clean) or RAM_STORAGE_RE.fullmatch(tok_clean):
            break
        if re.fullmatch(rf"{NUM}", tok_clean) and len(tokens) >= 1 and len(tok_clean) >= 3 and int(float(tok_clean.replace(",", "")) or 0) > 2100:
            break  # a long number is probably a price, not a model
        tokens.append(tok_clean)
        if len(tokens) >= 4:
            break
    model = " ".join(tokens)
    model = translate_model_words(model)
    if brand == "Samsung" and m and not re.match(r"samsung|سامسون", m.group(0), re.I) and not model.lower().startswith("galaxy"):
        model = "Galaxy " + model
    name = f"{brand} {model}".strip() if brand else model
    return re.sub(r"\s+", " ", name)


MODEL_WORDS = {
    "برو": "Pro", "بروماكس": "Pro Max", "ماكس": "Max", "بلس": "Plus", "الترا": "Ultra", "ألترا": "Ultra",
    "نوت": "Note", "ميني": "mini", "لايت": "Lite", "فولد": "Fold", "فلب": "Flip", "فليب": "Flip",
    "كالكسي": "Galaxy", "جالكسي": "Galaxy", "ارتشر": "Archer", "اكس": "X", "اس": "S", "اي": "A",
}


def price_ok(kind: str, amount: float, currency: str) -> bool:
    """أسعار أقل من هذا الحد غالباً إكسسوار (كفر، لاصق) مو جهاز."""
    if currency == "USD":
        return amount >= (15 if kind == "router" else 40)
    if currency == "IQD":
        return amount >= (10_000 if kind == "router" else 50_000)
    return True


def valid_name(device: str, brand: str) -> bool:
    """لازم بعد اسم الشركة يكون موديل (مثل 15 Pro أو A55 أو Archer)."""
    model = device[len(brand):].strip() if brand and device.startswith(brand) else device
    first = model.split()[0] if model.split() else ""
    return bool(re.search(r"[A-Za-z0-9]", first))


def translate_model_words(s: str) -> str:
    out = []
    for tok in s.split():
        out.append(MODEL_WORDS.get(tok, tok))
    return " ".join(out)


def extract_specs(text: str, kind: str) -> list[str]:
    t = normalize(text)
    specs = []
    rs = RAM_STORAGE_RE.search(t)
    if rs and int(rs.group(1)) <= 24 and int(rs.group(2)) in (16, 32, 64, 128, 256, 512, 1024):
        specs += [f"RAM {rs.group(1)}GB", f"{rs.group(2)}GB"]
    else:
        ram = RAM_RE.search(t)
        if ram:
            specs.append(f"RAM {ram.group(1) or ram.group(2)}GB")
        for sm in STORAGE_RE.finditer(t):
            if sm.group(1) and int(sm.group(1)) in (16, 32, 64, 128, 256, 512):
                specs.append(f"{sm.group(1)}GB")
                break
            if sm.group(2):
                specs.append(f"{sm.group(2)}TB")
                break
    if kind == "router":
        for sm in ROUTER_SPEED_RE.finditer(t):
            specs.append(sm.group(0).upper().replace(" ", ""))
    if WARRANTY_RE.search(t):
        specs.append("كفالة")
    # de-dup keep order
    seen, res = set(), []
    for s in specs:
        if s not in seen:
            seen.add(s)
            res.append(s)
    return res


def detect_condition(text: str) -> str:
    t = normalize(text)
    if CONDITION_USED.search(t):
        return "مستعمل"
    if CONDITION_NEW.search(t):
        return "جديد"
    return ""

GRID_PRICE_RE = re.compile(r"(?<![\d,.])(\d{1,3}(?:[,.]\d{3}){1,2})(?![\d])\s*(iqd|د\.?\s?ع|\$|usd)?", re.I)
GRID_STORAGE_RE = re.compile(r"(?<!\d)(\d{2,4})\s*(?:gb|g\b|جيجا|كيكا)|(?<!\d)(\d)\s*(?:tb|تيرا)", re.I)


def parse_ocr_grid(lines: list[str]) -> list[Item]:
    """بوسترات جدول: اسم الجهاز، وتحته صف أسعار وصف سعات (256GB 512GB 1TB ...).
    نربط كل سعر بالسعة اللي بنفس الترتيب. الأسعار الصفرية (0,000,000) = غير متوفر."""
    items: list[Item] = []
    blocks, cur = [], None
    for line in lines:
        m, brand, kind = detect_brand(line)
        if brand and not GRID_PRICE_RE.search(line):
            cur = {"line": line, "m": m, "brand": brand, "kind": kind, "prices": [], "storages": []}
            blocks.append(cur)
            continue
        if cur is None:
            continue
        for g in GRID_PRICE_RE.finditer(line):
            amount = float(re.sub(r"[,.]", "", g.group(1)))
            unit = (g.group(2) or "").lower()
            cur["prices"].append((amount, "USD" if unit in ("$", "usd") else "IQD" if unit else "?"))
        for g in GRID_STORAGE_RE.finditer(line):
            cur["storages"].append(f"{g.group(1)}GB" if g.group(1) else f"{g.group(2)}TB")
    for b in blocks:
        pr, st = b["prices"], b["storages"]
        if len(pr) < 2 or len(pr) != len(st):
            continue
        name = re.sub(r"(\s+[0oO©•●.]+)+$", "", extract_model(b["line"], b["m"], b["brand"]))
        if not valid_name(name, b["brand"]):
            continue
        cur_known = {c for _, c in pr if c != "?"}
        for (amount, c), storage in zip(pr, st):
            c = c if c != "?" else (next(iter(cur_known)) if len(cur_known) == 1 else "?")
            if amount == 0 or c == "?" or not price_ok(b["kind"] or "phone", amount, c):
                continue
            items.append(Item(device=name, brand=b["brand"], kind=b["kind"] or "phone", specs=[storage],
                              condition=detect_condition(b["line"]), price=amount, currency=c,
                              price_text=f"{amount:,.0f} {c}", line=b["line"][:300]))
    return items


def parse_post(text: str, ocr: bool = False, strict: bool = False) -> list[Item]:
    """Parse a whole post. A post can list many devices, one per line.

    Rules:
      * a line that has a price AND a brand  -> one item.
      * a line that has a price but no brand -> belongs to the last brand line above it
        (e.g. "Galaxy S24 Ultra" then on the next line "السعر 1,400,000").
      * a line with several "256 / 512" prices for one model -> one item per price.
    """
    text = normalize(text or "")
    lines = [l.strip() for l in re.split(r"[\n\r]+", text) if l.strip()]
    if len(lines) == 1 and len(lines[0]) > 200:
        # long single-line posts: split on bullets/emojis
        lines = [l.strip() for l in re.split(r"[•✅🔥⭐📱👈➖▪️◾]|\s{3,}", lines[0]) if l.strip()]

    if ocr:
        g = parse_ocr_grid(lines)
        if g:
            return g

    whole_condition = detect_condition(text)
    brand_lines = sum(1 for l in lines if detect_brand(l)[2])
    items: list[Item] = []
    last_brand_line = None  # (line, match, brand, kind)
    # strict (نص صفحات المواقع): سطر السعر لازم يجي مباشرة بعد سطر الجهاز.
    # المنشورات: نسمح بسطرين كلام بيناتهم.
    max_gap = 0 if strict else 2
    gap = 0
    for idx, line in enumerate(lines):
        m, brand, kind = detect_brand(line)
        prices = find_prices(line)
        if strict:
            prices = [p for p in prices if p.currency != "?"]
        if brand or kind == "router":
            if not prices:
                last_brand_line = (line, m, brand, kind)
                gap = 0
                continue
            ctx_line = line
        else:
            if not prices:
                gap += 1
                if gap > max_gap:
                    last_brand_line = None
                continue
            if not last_brand_line:
                continue
            line_ctx, m, brand, kind = last_brand_line
            ctx_line = line_ctx + " " + line
        name = extract_model(ctx_line if m is None else ctx_line, m, brand)
        if brand and not valid_name(name, brand):
            continue
        if not name or (kind == "router" and not brand and len(name) < 3):
            name = name or "راوتر"
        if ocr:
            name = re.sub(r"(\s+[0oO©•●.]+)+$", "", name)
        specs = extract_specs(ctx_line, kind)
        if ocr and idx + 1 < len(lines) and not any("GB" in x or "TB" in x for x in specs):
            # بالبوستر السعة تنكتب تحت السعر
            nxt = lines[idx + 1]
            if STORAGE_RE.search(nxt) and not find_prices(nxt):
                specs = extract_specs(ctx_line + " " + nxt, kind)
        cond = detect_condition(ctx_line)
        if not cond and brand_lines <= 1:
            cond = whole_condition  # منشور لجهاز واحد: الحالة ممكن تكون بسطر ثاني
        prices = [p for p in prices if p.amount > 0]
        if ocr and len(prices) > 1 and len({p.currency for p in prices}) == 1:
            # بالبوسترات: السعر القديم المشطوب جنب السعر الجديد، ناخذ الأقل
            prices = [min(prices, key=lambda p: p.amount)]
        prices = [p for p in prices if price_ok(kind or "phone", p.amount, p.currency)]
        for p in prices:
            items.append(Item(device=name, brand=brand, kind=kind or "phone", specs=specs, condition=cond,
                              price=p.amount, currency=p.currency, price_text=p.raw, line=ctx_line[:300]))
    return items


if __name__ == "__main__":
    import json, sys
    print(json.dumps([i.to_dict() for i in parse_post(sys.stdin.read())], ensure_ascii=False, indent=2))

"""البحث التلقائي عن مصادر جديدة داخل العراق.

- المواقع: بحث DuckDuckGo، ويقبل المواقع .iq أو اللي صفحتها تذكر العراق ومدنه.
المصادر الجديدة تنضاف لملف config/discovered.json وتنسحب من اليوم الثاني.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from datetime import date
from pathlib import Path

from websites import fetch

CONFIG = Path(__file__).resolve().parent / "config"
DISCOVERED = CONFIG / "discovered.json"

IRAQ_RE = re.compile(
    r"العراق|عراق|iraq|بغداد|baghdad|البصرة|basra|اربيل|أربيل|erbil|النجف|najaf|كربلاء|karbala|الموصل|mosul|"
    r"كركوك|kirkuk|السليمانية|sulaymaniyah|الحلة|hilla|الناصرية|العمارة|الديوانية|الكوت|الرمادي|بعقوبة|دهوك|duhok|"
    r"سامراء|تكريت|السماوة|الكرادة|المنصور|زيونة|شارع الصناعة|\+964|00964|\b07[3-9]\d{8}\b",
    re.I,
)
TOPIC_RE = re.compile(r"موبايل|موبايلات|هواتف|هاتف|جوال|mobile|phone|ايفون|سامسونج|راوتر|router|اتصالات|electronics|الكترونيات", re.I)
SKIP_DOMAINS = re.compile(r"facebook|instagram|youtube|tiktok|twitter|x\.com|wikipedia|gsmarena|amazon|aliexpress|duckduckgo|google", re.I)


def load():
    if DISCOVERED.exists():
        return json.loads(DISCOVERED.read_text(encoding="utf-8"))
    return {"facebook": [], "websites": [], "rejected": []}


def save(d):
    DISCOVERED.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def known_urls(cfg, disc):
    urls = {s["url"].rstrip("/").lower() for s in cfg.get("facebook", []) + cfg.get("websites", [])}
    urls |= {s["url"].rstrip("/").lower() for s in disc["facebook"] + disc["websites"]}
    urls |= {u.rstrip("/").lower() for u in disc["rejected"]}
    return urls


def ddg(query: str):
    html = fetch("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query), timeout=12)
    links = re.findall(r'class="result__a"[^>]+href="([^"]+)"', html)
    out = []
    for l in links:
        if "uddg=" in l:
            l = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlsplit(l).query).get("uddg", [l])[0])
        out.append(l)
    return out


def discover_websites(cfg, disc, budget):
    added = 0
    known = known_urls(cfg, disc)
    for q in cfg["discovery"].get("web_queries", []):
        try:
            links = ddg(q)
        except Exception as e:
            print("  ! بحث المواقع ما اشتغل (DuckDuckGo ما يستجيب)، نكمل بدونه:", e)
            return added
        for l in links:
            parts = urllib.parse.urlsplit(l)
            base = f"{parts.scheme}://{parts.netloc}"
            if SKIP_DOMAINS.search(parts.netloc) or base.lower() in known:
                continue
            known.add(base.lower())
            ok = parts.netloc.endswith(".iq")
            if not ok:
                try:
                    body = fetch(base, timeout=15)
                    ok = bool(IRAQ_RE.search(body) and TOPIC_RE.search(body))
                except Exception:
                    ok = False
            if ok:
                disc["websites"].append({"name": parts.netloc, "url": base, "found": date.today().isoformat(), "query": q})
                added += 1
                if added >= budget:
                    return added
            else:
                disc["rejected"].append(base)
    return added

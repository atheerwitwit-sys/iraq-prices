"""حفظ الأسعار بقاعدة بيانات SQLite وتصديرها كملفات JSON للموقع."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "collector" / "prices.db"
SITE_DATA = ROOT / "docs" / "data"

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,
  device TEXT NOT NULL,
  brand TEXT,
  kind TEXT,
  specs TEXT,
  condition TEXT,
  price REAL,
  currency TEXT,
  price_text TEXT,
  source_name TEXT,
  source_type TEXT,
  url TEXT,
  excerpt TEXT,
  scraped_at TEXT,
  UNIQUE(day, device, price, currency, url)
);
CREATE INDEX IF NOT EXISTS idx_day ON prices(day);
"""


def connect():
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    return con


def save_items(con, items, source_name, source_type, url, excerpt="", day=None):
    day = day or date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    n = 0
    for it in items:
        cur = con.execute(
            "INSERT OR IGNORE INTO prices(day,device,brand,kind,specs,condition,price,currency,price_text,"
            "source_name,source_type,url,excerpt,scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (day, it.device, it.brand, it.kind, json.dumps(it.specs, ensure_ascii=False), it.condition,
             it.price, it.currency, it.price_text, source_name, source_type, url, (excerpt or it.line)[:400], now),
        )
        n += cur.rowcount
    con.commit()
    return n


def export(con, day=None):
    """يكتب docs/data/<day>.json و latest.json و dates.json"""
    day = day or date.today().isoformat()
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    rows = con.execute(
        "SELECT device,brand,kind,specs,condition,price,currency,price_text,source_name,source_type,url,excerpt,scraped_at "
        "FROM prices WHERE day=? ORDER BY kind, brand, device, price", (day,)
    ).fetchall()
    keys = ["device", "brand", "kind", "specs", "condition", "price", "currency", "price_text",
            "source_name", "source_type", "url", "excerpt", "scraped_at"]
    items = []
    for r in rows:
        d = dict(zip(keys, r))
        d["specs"] = json.loads(d["specs"] or "[]")
        items.append(d)
    payload = {"day": day, "count": len(items), "items": items}
    if not items:
        return 0  # ما نمسح آخر أسعار بالموقع إذا التشغيل ما جاب شي
    (SITE_DATA / f"{day}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (SITE_DATA / "latest.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    days = [r[0] for r in con.execute("SELECT DISTINCT day FROM prices ORDER BY day DESC LIMIT 60")]
    (SITE_DATA / "dates.json").write_text(json.dumps(days), encoding="utf-8")
    return len(items)

"""التشغيل اليومي: يسحب من كل المصادر، يحفظ الأسعار، يحدّث الموقع، وينشره.

الاستعمال:
    python run.py               # تشغيل كامل
    python run.py --no-publish  # بدون رفع على GitHub
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
import traceback
from datetime import date
from functools import partial
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import store  # noqa: E402
from parser import parse_post  # noqa: E402
import discover  # noqa: E402
from websites import scrape_site  # noqa: E402
from saved_pages import process_inbox  # noqa: E402

LOG = HERE / "logs"


def log(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    LOG.mkdir(exist_ok=True)
    with open(LOG / f"{date.today().isoformat()}.log", "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


def load_config():
    cfg = json.loads((HERE / "config" / "sources.json").read_text(encoding="utf-8"))
    disc = discover.load()
    return cfg, disc


def run_websites(con, sites, save):
    total = 0
    for s in sites:
        try:
            res = scrape_site(s["url"])
            n = 0
            for item, link in res:
                n += save(con, [item], s["name"], "website", link)
            log(f"  موقع {s['name']}: {n} سعر")
            total += n
        except Exception as e:
            log(f"  ! موقع {s['name']} فشل: {e}")
    return total


def publish():
    root = HERE.parent
    if not (root / ".git").exists():
        log("  (ما مربوط بـ GitHub، تخطيت النشر)")
        return
    day = date.today().isoformat()
    cmds = [["git", "add", "docs", "collector"],
            ["git", "commit", "-m", f"أسعار {day}"],
            ["git", "pull", "--rebase", "--autostash"],
            ["git", "push"]]
    for c in cmds:
        r = subprocess.run(c, cwd=root, capture_output=True, text=True)
        if r.returncode and c[1] != "commit":
            log("  ! النشر فشل:", " ".join(c), r.stderr.strip()[:300])
            return
    log("  تم النشر على GitHub Pages")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--scheduled", action="store_true", help="تأخير عشوائي حتى ما يكون بنفس الدقيقة كل يوم")
    a = ap.parse_args()
    if a.scheduled:
        time.sleep(random.uniform(0, 45 * 60))

    # تاريخ التشغيل يتثبت من البداية، حتى لو التشغيل عبر نص الليل كل الأسعار تنحسب لنفس اليوم
    day = date.today().isoformat()
    save = partial(store.save_items, day=day)
    cfg, disc = load_config()
    con = store.connect()
    log(f"=== بدء التشغيل {day} ===")

    if cfg["discovery"].get("enabled"):
        added = discover.discover_websites(cfg, disc, cfg["discovery"].get("max_new_sources_per_day", 5))
        discover.save(disc)
        log(f"  بحث تلقائي مواقع: {added} موقع جديد")

    # إذا شغلته أكثر من مرة باليوم، أسعار المواقع تتحدث بدل ما تتكرر
    con.execute("DELETE FROM prices WHERE day=? AND source_type='website'", (day,))
    con.commit()
    total = run_websites(con, cfg.get("websites", []) + disc.get("websites", []), save)
    try:
        total += process_inbox(con, parse_post, save, log)
    except Exception:
        log("  ! خطأ بقراءة الصفحات المحفوظة:\n" + traceback.format_exc())

    n = store.export(con, day)
    log(f"=== انتهى: {total} سعر جديد، {n} سعر لليوم بالموقع ===")
    if not a.no_publish:
        publish()


if __name__ == "__main__":
    main()

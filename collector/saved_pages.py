"""قراءة صفحات فيسبوك وإنستكرام اللي تحفظها أنت من متصفحك (Ctrl+S) بمجلد inbox.

أنت تتصفح بحسابك بشكل طبيعي، والبرنامج ما يدخل على فيسبوك أبداً.
يقبل ملفات .html و .htm و .mhtml. بعد القراءة الملف ينتقل لـ inbox/done/<التاريخ>/.
"""
from __future__ import annotations

import email
import re
import hashlib
import shutil
from urllib.parse import unquote
from datetime import date
from email import policy
from pathlib import Path

from bs4 import BeautifulSoup

import ocr

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"

POST_LINK_RE = re.compile(r"/posts/|/permalink|story_fbid=|/videos/|/reel/|pfbid|/photo|/p/[A-Za-z0-9_-]+")


def read_file(path: Path):
    """يرجع (html، دالة تجيب بايتات الصورة من src)"""
    raw = path.read_bytes()
    if path.suffix.lower() in (".mhtml", ".mht"):
        msg = email.message_from_bytes(raw, policy=policy.default)
        html, parts = "", {}
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html" and not html:
                html = part.get_content()
            elif ctype.startswith("image/"):
                loc = part.get("Content-Location", "")
                if loc:
                    parts[loc] = part.get_payload(decode=True)
        return html, lambda src: parts.get(src)

    def local(src):
        if src.startswith(("http://", "https://", "data:")):
            return None
        f = (path.parent / unquote(src.split("?")[0])).resolve()
        return f.read_bytes() if f.is_file() else None
    return raw.decode("utf-8", "replace"), local


def page_url(html: str, soup: BeautifulSoup) -> str:
    m = re.search(r"saved from url=\(\d+\)(\S+?)\s*-->", html)
    if m:
        return m.group(1)
    for sel, attr in (('link[rel="canonical"]', "href"), ('meta[property="og:url"]', "content")):
        el = soup.select_one(sel)
        if el and el.get(attr):
            return el[attr]
    m = re.search(r"Snapshot-Content-Location:\s*(\S+)", html)
    return m.group(1) if m else ""


def clean_link(href: str) -> str:
    if not href:
        return ""
    if href.startswith("/"):
        href = "https://www.facebook.com" + href
    href = re.sub(r"[?&](__cft__|__tn__|comment_id|ref|mibextid)[^&]*", "", href)
    return href.split("#")[0]


def extract_posts(html: str):
    """يرجع (اسم الصفحة، رابط الصفحة، نوع المصدر، [{text, link}])"""
    soup = BeautifulSoup(html, "html.parser")
    url = page_url(html, soup)
    title = (soup.title.string if soup.title and soup.title.string else "").strip()
    title = re.sub(r"\s*[|\-–]\s*(Facebook|فيسبوك|Instagram).*$", "", title)
    title = re.sub(r"^\(\d+\)\s*", "", title).strip()
    kind = "instagram" if "instagram.com" in url or "Instagram" in (soup.title.string or "" if soup.title else "") else "facebook"

    posts = []
    if kind == "facebook":
        arts = [a for a in soup.select('div[role="article"]') if not a.find_parent("div", attrs={"role": "article"})]
        for a in arts:
            msg = a.select_one('[data-ad-preview="message"], [data-ad-comet-preview="message"]')
            text = (msg or a).get_text("\n", strip=True)
            link = ""
            for el in a.find_all("a", href=True):
                if POST_LINK_RE.search(el["href"]):
                    link = clean_link(el["href"])
                    break
            imgs = []
            for im in a.find_all("img", src=True):
                src = im["src"]
                if re.search(r"emoji|static\.xx|rsrc\.php|/v/t1\.30497-1/|s\d{2}x\d{2}|p\d{2}x\d{2}", src):
                    continue  # إيموجي أو صورة البروفايل
                try:
                    if int(im.get("width") or 999) < 100 or int(im.get("height") or 999) < 100:
                        continue
                except ValueError:
                    pass
                imgs.append(src)
            if text or imgs:
                posts.append({"text": text, "link": link or url, "images": imgs[:6]})
    else:
        # إنستكرام: النص يكون بصفحة المنشور (h1) أو بوصف الصورة (alt)
        h1 = soup.find("h1")
        if h1 and len(h1.get_text(strip=True)) > 5:
            posts.append({"text": h1.get_text("\n", strip=True), "link": url})
        for a in soup.find_all("a", href=re.compile(r"/(p|reel)/")):
            img = a.find("img", alt=True)
            if img and len(img["alt"]) > 10:
                href = a["href"]
                if href.startswith("/"):
                    href = "https://www.instagram.com" + href
                posts.append({"text": img["alt"], "link": href.split("?")[0], "images": [img.get("src", "")]})
    return title or url, url, kind, posts


def process_inbox(con, parse_post, save_items, log=print):
    INBOX.mkdir(exist_ok=True)
    done = INBOX / "done" / date.today().isoformat()
    total = 0
    files = [p for p in INBOX.iterdir() if p.is_file() and p.suffix.lower() in (".html", ".htm", ".mhtml", ".mht")]
    if not files:
        log("  مجلد inbox فارغ (ما حفظت صفحات اليوم)")
    for f in files:
        try:
            html, get_image = read_file(f)
            name, url, kind, posts = extract_posts(html)
            n, n_img, seen = 0, 0, set()
            for p in posts:
                items = parse_post(p["text"]) if p["text"] else []
                n += save_items(con, items, name, kind, p["link"], p["text"][:400])
                if not ocr.available():
                    continue
                for src in p.get("images", []):
                    data = get_image(src)
                    if not data:
                        continue
                    h = hashlib.md5(data).hexdigest()
                    if h in seen:
                        continue
                    seen.add(h)
                    txt = ocr.image_to_text(data)
                    if not txt:
                        continue
                    n_img += 1
                    # نص المنشور (أول سطرين) يساعد إذا اسم الجهاز مكتوب بالمنشور مو بالصورة
                    img_items = parse_post(txt, ocr=True)
                    n += save_items(con, img_items, name, kind, p["link"], "[من الصورة] " + txt[:380])
            extra = f"، قريت {n_img} صورة" if n_img else ("" if ocr.available() else "، (قارئ الصور مو منصب)")
            log(f"  صفحة محفوظة {name}: {len(posts)} منشور{extra}، {n} سعر")
            total += n
        except Exception as e:
            log(f"  ! ما گدرت أقرا {f.name}: {e}")
            continue
        done.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), done / f.name)
        assets = f.with_name(f.stem + "_files")
        if assets.exists():
            shutil.move(str(assets), done / assets.name)
    return total

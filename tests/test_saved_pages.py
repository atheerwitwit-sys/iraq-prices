import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))
from saved_pages import extract_posts

FB = """<!DOCTYPE html><!-- saved from url=(0035)https://www.facebook.com/Trendmiq -->
<html><head><title>(3) Trendmiq | Facebook</title></head><body><div role="feed">
<div role="article"><div data-ad-comet-preview="message"><div>ايفون 15 برو 256 كيكا</div><div>السعر 1,150,000</div></div>
<a href="https://www.facebook.com/Trendmiq/posts/pfbid0abc?__cft__[0]=x&amp;__tn__=R">2h</a>
<div role="article">تعليق: بكم السامسونج A55 بسعر 400 الف</div></div>
<div role="article"><div data-ad-comet-preview="message">راوتر TP-Link Archer C6 بـ 55 الف</div>
<a href="/Trendmiq/posts/123">1d</a></div>
</div></body></html>"""


def test_facebook_saved_page():
    name, url, kind, posts = extract_posts(FB)
    assert name == "Trendmiq" and kind == "facebook" and url.endswith("/Trendmiq")
    assert len(posts) == 2  # التعليق ما ينحسب
    assert posts[0]["link"] == "https://www.facebook.com/Trendmiq/posts/pfbid0abc"
    assert "1,150,000" in posts[0]["text"]
    assert posts[1]["link"] == "https://www.facebook.com/Trendmiq/posts/123"

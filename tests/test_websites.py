import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))
from websites import product_tiles

HTML = """<div class="grid">
<div class="wrapper-with-border"><a href="/ar/iphone-17.html" class="product-link"><img alt="x"></a>
 <div class="product__name">ايفون 17 برو ماكس - 256 جيجا</div>
 <div class="product__price-current cl-red">2,025,000 د.ع</div><div class="product__price-original">2,300,000 د.ع</div></div>
<div class="wrapper-with-border"><a href="/ar/killer.html" class="product-link"></a>
 <div class="product__name">قاتل البعوض المحمول</div><div class="product__price-current">24,754 د.ع</div></div>
<div class="wrapper-with-border"><a href="/ar/archer.html" class="product-link"></a>
 <div class="product__name">راوتر تي بي لينك Archer AX55</div><div class="product__price-current">95,000 د.ع</div></div>
</div>"""


def test_tiles():
    res = product_tiles(HTML, "https://www.elryan.com/ar/c/x")
    names = [(i.device, i.price, link) for i, link in res]
    assert ("iPhone 17 Pro Max", 2025000, "https://www.elryan.com/ar/iphone-17.html") in names
    assert any(d.startswith("TP-Link") and p == 95000 for d, p, _ in names)
    assert len(names) == 2

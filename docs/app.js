(() => {
  const $ = (id) => document.getElementById(id);
  const KIND = { phone: "موبايل", router: "راوتر", tablet: "تابلت" };
  const SRC = { facebook: "فيسبوك", instagram: "إنستكرام", website: "موقع" };
  let items = [];

  const fmt = (it) => {
    if (it.currency === "IQD") return Math.round(it.price).toLocaleString("en-US") + " د.ع";
    if (it.currency === "USD") return "$" + it.price.toLocaleString("en-US");
    return it.price.toLocaleString("en-US") + " (العملة غير مذكورة)";
  };
  // للمقارنة فقط بين الدينار والدولار عند الترتيب (السعر المعروض يبقى مثل المنشور)
  const sortValue = (it) => it.currency === "USD" ? it.price * 1500 : (it.currency === "?" && it.price < 5000 ? it.price * 1000 : it.price);
  const norm = (s) => (s || "").toLowerCase()
    .replace(/[أإآ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي")
    .replace(/ايفون/g, "iphone").replace(/سامسونج|سامسونك/g, "samsung").replace(/كالكسي|جالكسي/g, "galaxy")
    .replace(/شاومي/g, "xiaomi").replace(/ريدمي/g, "redmi").replace(/برو/g, "pro").replace(/ماكس/g, "max")
    .replace(/الترا/g, "ultra").replace(/راوترات|راوتر/g, "router").replace(/موبايلات|هواتف/g, "موبايل").replace(/\s+/g, " ").trim();

  async function loadDay(day) {
    const file = day ? `data/${day}.json` : "data/latest.json";
    try {
      const r = await fetch(file, { cache: "no-store" });
      const d = await r.json();
      items = d.items || [];
      items.forEach((it) => (it._s = norm([it.device, it.brand, (it.specs || []).join(" "), it.source_name, it.kind, KIND[it.kind], it.kind === "tablet" ? "تاب ipad" : ""].join(" "))));
      const brands = [...new Set(items.map((i) => i.brand).filter(Boolean))].sort();
      const sel = $("brand"), cur = sel.value;
      sel.innerHTML = '<option value="">الكل</option>' + brands.map((b) => `<option>${b}</option>`).join("");
      sel.value = brands.includes(cur) ? cur : "";
      render();
    } catch (e) {
      items = [];
      $("summary").textContent = "ما گدرت أحمّل بيانات هذا اليوم.";
      $("list").innerHTML = "";
    }
  }

  function render() {
    const q = norm($("q").value);
    const terms = q ? q.split(" ") : [];
    const kind = $("kind").value, cur = $("cur").value, cond = $("cond").value, brand = $("brand").value;
    const base = items.filter((it) =>
      (!cur || it.currency === cur) && (!cond || it.condition === cond) &&
      (!brand || it.brand === brand) && terms.every((t) => it._s.includes(t)));
    // عدد كل تبويب حسب البحث والفلاتر الحالية
    document.querySelectorAll(".tabs button").forEach((b) => {
      const k = b.dataset.kind;
      b.querySelector("span").textContent = (k ? base.filter((it) => it.kind === k).length : base.length).toLocaleString("en-US");
      b.setAttribute("aria-selected", String(k === kind));
    });
    let rows = base.filter((it) => !kind || it.kind === kind);

    let othersCount = new Map();
    if ($("cheapest").checked) {
      const best = new Map();
      for (const it of rows) {
        const k = norm(it.device) + "|" + (it.specs || []).filter((s) => /GB|TB/.test(s)).join(",") + "|" + it.condition;
        othersCount.set(k, (othersCount.get(k) || 0) + 1);
        if (!best.has(k) || sortValue(it) < sortValue(best.get(k))) best.set(k, Object.assign(it, { _k: k }));
      }
      rows = [...best.values()];
    }
    const s = $("sort").value;
    rows.sort(s === "asc" ? (a, b) => sortValue(a) - sortValue(b)
      : s === "desc" ? (a, b) => sortValue(b) - sortValue(a)
      : (a, b) => a.device.localeCompare(b.device) || sortValue(a) - sortValue(b));

    const sources = new Set(rows.map((r) => r.source_name));
    $("summary").textContent = `${rows.length.toLocaleString("en-US")} سعر من ${sources.size} مصدر`;
    $("empty").hidden = rows.length > 0;

    const tpl = $("card"), frag = document.createDocumentFragment();
    for (const it of rows.slice(0, 600)) {
      const c = tpl.content.cloneNode(true);
      c.querySelector(".name").textContent = it.device;
      const th = c.querySelector(".thumb"), im = th.querySelector("img");
      th.querySelector(".ph").textContent = it.kind === "router" ? "📶" : it.kind === "tablet" ? "▭" : "📱";
      if (/^https:\/\//.test(it.image || "")) {
        im.src = it.image; im.alt = it.device;
        im.onerror = () => { im.remove(); th.classList.add("noimg"); };
      } else { im.remove(); th.classList.add("noimg"); }
      const k = c.querySelector(".kind"); k.textContent = KIND[it.kind] || it.kind; k.classList.add(it.kind);
      const ul = c.querySelector(".specs");
      for (const sp of it.specs || []) { const li = document.createElement("li"); li.textContent = sp; ul.appendChild(li); }
      const p = c.querySelector(".price"); p.textContent = fmt(it);
      if (it.currency === "USD") p.classList.add("usd"); if (it.currency === "?") p.classList.add("unk");
      c.querySelector(".cond").textContent = it.condition || "";
      c.querySelector(".srcname").textContent = `${SRC[it.source_type] || ""} · ${it.source_name}`;
      const a = c.querySelector(".link"); a.href = /^https?:\/\//.test(it.url) ? it.url : "#";
      if (it.source_type === "website") a.textContent = "فتح الصفحة ↗";
      c.querySelector(".excerpt p").textContent = it.excerpt || "";
      if (it._k && othersCount.get(it._k) > 1) {
        const o = document.createElement("div"); o.className = "others";
        o.textContent = `+ ${othersCount.get(it._k) - 1} أسعار ثانية لنفس الجهاز`;
        c.querySelector(".card").insertBefore(o, c.querySelector(".src"));
      }
      frag.appendChild(c);
    }
    $("list").replaceChildren(frag);
  }

  async function init() {
    let days = [];
    try { days = await (await fetch("data/dates.json", { cache: "no-store" })).json(); } catch (e) {}
    const sel = $("day");
    sel.innerHTML = days.length ? days.map((d, i) => `<option value="${d}">${i === 0 ? "اليوم " : ""}${d}</option>`).join("")
                                : '<option value="">آخر تحديث</option>';
    sel.onchange = () => loadDay(sel.value);
    document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => {
      $("kind").value = b.dataset.kind;
      try { localStorage.setItem("kind", b.dataset.kind); } catch (e) {}
      render();
    }));
    try { $("kind").value = localStorage.getItem("kind") || ""; } catch (e) {}
    ["q", "cur", "cond", "brand", "sort", "cheapest"].forEach((id) => $(id).addEventListener("input", render));
    await loadDay(days[0] || "");
  }
  init();
})();

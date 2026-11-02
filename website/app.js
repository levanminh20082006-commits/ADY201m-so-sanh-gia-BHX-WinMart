"use strict";

/* ================================================================ constants */
const STORE = { b: "Bách Hóa Xanh", w: "WinMart" };
const SHORT = { b: "BHX", w: "WinMart" };
const PAGE_PAIRS = 24;
const PAGE_PRODUCTS = 40;
const QUICK = ["Hảo Hảo", "Vinamilk", "Chinsu", "G7", "Omachi", "Maggi", "Head & Shoulders", "Cholimex"];
const ROTATE = ["rẻ hơn?", "lợi hơn?", "hời hơn?"];
const BANDS = ["Dưới 20.000 đ", "20.000 – 100.000 đ", "Từ 100.000 đ"];

const ICON = {
  beverages: '<path d="M7 8h10l-1.2 12a1 1 0 0 1-1 .9H9.2a1 1 0 0 1-1-.9z"/><path d="M12 8l2-5h3"/><path d="M7.5 13h9"/>',
  household_cleaning: '<path d="M9 9h5v2.5a3 3 0 0 1 1.5 2.6V20a1 1 0 0 1-1 1h-6a1 1 0 0 1-1-1v-5.9A3 3 0 0 1 9 11.5z"/><path d="M10 9V6h4l3 2"/><path d="M19 5v.01M20.5 7v.01M19 9v.01"/>',
  instant_food: '<path d="M3 12h18a9 9 0 0 1-18 0z"/><path d="M14 3l-3 9M18 4l-4 8"/><path d="M8 21h8"/>',
  milk_dairy: '<path d="M8 3h8v3l2 3v11a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V9l2-3z"/><path d="M6 9h12"/><path d="M8 6h8"/>',
  personal_care: '<path d="M8 10h8v10a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1z"/><path d="M10 10V7h4v3"/><path d="M12 7V4h4"/><path d="M10.5 15h3"/>',
  seasoning: '<path d="M8 9h8l-1 11a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1z"/><path d="M8 9a4 4 0 0 1 8 0"/><path d="M11 6.5v.01M13 6.5v.01M12 5v.01"/>',
  snacks_confectionery: '<circle cx="12" cy="12" r="4"/><path d="M8.5 10L4 7v10l4.5-3M15.5 10L20 7v10l-4.5-3"/>',
};
const I = {
  bag: '<path d="M6 7h12l-1 13a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1z"/><path d="M9 7a3 3 0 0 1 6 0"/>',
  tag: '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.3"/>',
  eq: '<path d="M5 9h14M5 15h14"/>',
  ext: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  heart: '<path d="M12 20s-7-4.4-9.2-8.7C1.3 8.3 3.1 5 6.4 5c2 0 3.3 1.1 4.1 2.3h3c.8-1.2 2.1-2.3 4.1-2.3 3.3 0 5.1 3.3 3.6 6.3C19 15.6 12 20 12 20z"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  check: '<path d="M5 12l5 5 9-10"/>',
  box: '<path d="M3 7l9-4 9 4-9 4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/>',
  scale: '<path d="M12 3v18M5 7h14"/><path d="M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0z"/>',
  percent: '<path d="M19 5L5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/>',
};
const svg = (paths) => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths}</svg>`;

/* ================================================================ state */
const $ = (id) => document.getElementById(id);
let META, PAIRS, PRODUCTS;
let cart = {};
let favs = new Set();
const S = {
  page: null,
  cmp: { q: "", g: "", sort: "save", cheap: "", focus: null, limit: PAGE_PAIRS },
  prd: { q: "", g: "", price: "", sort: "relevant", store: "", promo: false, both: false, limit: PAGE_PRODUCTS },
  km: { type: "deep", store: "", g: "", limit: PAGE_PRODUCTS },
};
const DEFAULTS = {
  cmp: { q: "", g: "", sort: "save", cheap: "", focus: null },
  prd: { q: "", g: "", price: "", sort: "relevant", store: "", promo: false, both: false },
  km: { type: "deep", store: "", g: "" },
};

/* ================================================================ helpers */
const nf = new Intl.NumberFormat("vi-VN");
const money = (n) => nf.format(Math.round(n)) + " đ";
const pct = (n) => nf.format(Math.round(n * 10) / 10) + "%";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const norm = (s) => String(s ?? "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
const wordsOf = (s) => norm(s).split(/[^a-z0-9]+/).filter(Boolean);
const dot = (s) => `<span class="dot dot-${s}" aria-hidden="true"></span>`;
const pairMin = (x) => Math.min(x.bp, x.wp);
const pairSave = (x) => Math.abs(x.bp - x.wp);
const pairPct = (x) => pairSave(x) / Math.max(x.bp, x.wp) * 100;
const median = (a) => { const s = a.slice().sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const isPromo = (p) => !!(p.d || p.f || p.pt);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

function storage(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch (e) { /* storage blocked: everything still works, nothing is remembered */ }
  return null;
}

// every typed word must start a word of the product ("hao" finds "Hảo Hảo" but not "Cháo")
function matches(words, q) {
  if (!q) return true;
  return wordsOf(q).every((t) => words.some((w) => w.startsWith(t)));
}
function relevance(p, q) {
  const first = wordsOf(q)[0] || "";
  const at = p.nw.findIndex((w) => w.startsWith(first));
  return (at < 0 ? 99 : at) * 1000 + p.n.length;
}
// bold the typed words inside a product name (accent-insensitive)
function highlight(name, q) {
  const qs = wordsOf(q);
  if (!qs.length) return esc(name);
  return name.split(/(\s+)/).map((tok) => {
    const n = norm(tok).replace(/[^a-z0-9]/g, "");
    return qs.some((t) => n.startsWith(t)) && n ? `<mark>${esc(tok)}</mark>` : esc(tok);
  }).join("");
}

function sizeText(p) {
  const parts = [];
  if (p.sz) parts.push(nf.format(p.sz) + (p.su || "") + (p.pk > 1 ? " × " + p.pk : ""));
  else if (p.pk > 1) parts.push(p.pk + " món");
  if (p.ul) parts.push(p.ul);
  return parts.join(" · ");
}
const perUnit = (p) => (p.su === "ml" ? "/lít" : "/kg");
const unitText = (p) => (p.up ? "≈ " + money(p.up) + perUnit(p) : "");

function img(p) {
  if (!p || !p.img) return `<span class="ph">${svg(I.bag)}</span>`;
  return `<img src="${esc(p.img)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">`;
}
document.addEventListener("error", (e) => {      // broken product photo -> neutral placeholder
  if (e.target.tagName === "IMG" && !e.target.dataset.failed) {
    e.target.dataset.failed = "1";
    e.target.outerHTML = `<span class="ph">${svg(I.bag)}</span>`;
  }
}, true);

function promoTags(p, prefix) {
  const t = [];
  if (p.f) t.push(`<span class="tag flash">${prefix}⚡ Flash sale</span>`);
  if (p.d) t.push(`<span class="tag promo">${prefix}Giảm ${pct(p.d)}</span>`);
  if (p.pt) t.push(`<span class="tag promo">${prefix}${esc(p.pt)}</span>`);
  return t.join("");
}

/* ================================================================ motion: reveal, count-up, progress */
const io = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
  for (const en of entries) {
    if (!en.isIntersecting) continue;
    en.target.classList.add("in");
    en.target.querySelectorAll("[data-to]").forEach(countUp);
    if (en.target.matches("[data-to]")) countUp(en.target);
    io.unobserve(en.target);
  }
}, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }) : null;

function observe(root) {
  const els = (root || document).querySelectorAll(".reveal:not(.in), .grow:not(.in)");
  els.forEach((el) => (io ? io.observe(el) : el.classList.add("in")));
}

function countUp(el) {
  if (el.dataset.done) return;
  el.dataset.done = "1";
  const to = +el.dataset.to;
  if (reduceMotion || !to) { el.textContent = nf.format(to); return; }
  const t0 = performance.now(), dur = 1100;
  const step = (t) => {
    const k = Math.min(1, (t - t0) / dur);
    el.textContent = nf.format(Math.round(to * (1 - Math.pow(1 - k, 3))));
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function onScroll() {
  const h = document.documentElement;
  const k = h.scrollHeight > h.clientHeight ? h.scrollTop / (h.scrollHeight - h.clientHeight) : 0;
  $("progress").style.transform = `scaleX(${k})`;
  $("toTop").hidden = h.scrollTop < 700;
}

/* ================================================================ tooltip (charts) */
function bindTooltip() {
  const tip = $("tip");
  const place = (x, y) => {
    const r = tip.getBoundingClientRect();
    tip.style.left = Math.min(window.innerWidth - r.width - 8, Math.max(8, x + 14)) + "px";
    tip.style.top = Math.max(8, y - r.height - 12) + "px";
  };
  document.addEventListener("pointerover", (e) => {
    const t = e.target.closest("[data-tip]");
    if (!t) return;
    tip.innerHTML = t.dataset.tip;
    tip.hidden = false;
    place(e.clientX, e.clientY);
  });
  document.addEventListener("pointermove", (e) => { if (!tip.hidden) place(e.clientX, e.clientY); });
  document.addEventListener("pointerout", (e) => { if (e.target.closest("[data-tip]")) tip.hidden = true; });
  window.addEventListener("scroll", () => { tip.hidden = true; }, { passive: true });
}

/* ================================================================ routing */
const PAGES = ["home", "so-sanh", "san-pham", "khuyen-mai", "thong-ke", "yeu-thich", "gioi-thieu", "gio-hang"];
const TITLES = { home: "So Giá – BHX vs WinMart", "so-sanh": "So sánh giá", "san-pham": "Sản phẩm", "khuyen-mai": "Khuyến mãi",
  "thong-ke": "Thống kê", "yeu-thich": "Yêu thích", "gioi-thieu": "Giới thiệu" };

function parseHash() {
  const h = location.hash.replace(/^#\/?/, "");
  const [path, query] = h.split("?");
  return { page: PAGES.includes(path) ? path : "home", params: new URLSearchParams(query || "") };
}

function hashFor(page) {
  const p = new URLSearchParams();
  const set = (k, v, d) => { if (v !== d && v !== null && v !== "" && v !== false) p.set(k, v === true ? "1" : v); };
  if (page === "so-sanh") {
    const c = S.cmp;
    set("cap", c.focus, null); set("q", c.q, ""); set("nhom", c.g, ""); set("re", c.cheap, ""); set("sx", c.sort, "save");
  } else if (page === "san-pham") {
    const c = S.prd;
    set("q", c.q, ""); set("nhom", c.g, ""); set("gia", c.price, ""); set("st", c.store, ""); set("km", c.promo, false); set("ca2", c.both, false); set("sx", c.sort, "relevant");
  } else if (page === "khuyen-mai") {
    const c = S.km;
    set("loai", c.type, "deep"); set("st", c.store, ""); set("nhom", c.g, "");
  }
  const qs = p.toString();
  return "#/" + (page === "home" ? "" : page) + (qs ? "?" + qs : "");
}

function go(page, patch) {
  const key = { "so-sanh": "cmp", "san-pham": "prd", "khuyen-mai": "km" }[page];
  if (key) Object.assign(S[key], DEFAULTS[key], patch || {});
  const h = hashFor(page);
  if (location.hash === h) onRoute(); else location.hash = h;
}
function syncHash() { history.replaceState(null, "", hashFor(S.page)); }

function onRoute() {
  let { page, params } = parseHash();
  if (page === "gio-hang") { importCart(params.get("c") || ""); return; }
  if (page === "so-sanh") {
    Object.assign(S.cmp, { q: params.get("q") || "", g: params.get("nhom") || "", cheap: params.get("re") || "", sort: params.get("sx") || "save",
      focus: params.has("cap") ? +params.get("cap") : null, limit: PAGE_PAIRS });
  }
  if (page === "san-pham") {
    Object.assign(S.prd, { q: params.get("q") || "", g: params.get("nhom") || "", price: params.get("gia") || "", store: params.get("st") || "",
      promo: params.get("km") === "1", both: params.get("ca2") === "1", sort: params.get("sx") || "relevant", limit: PAGE_PRODUCTS });
  }
  if (page === "khuyen-mai") {
    Object.assign(S.km, { type: params.get("loai") || "deep", store: params.get("st") || "", g: params.get("nhom") || "", limit: PAGE_PRODUCTS });
  }
  const changed = S.page !== page;
  S.page = page;
  closeModal(true);
  ["navQ", "heroQ"].forEach((id) => $(id).closeSuggest && $(id).closeSuggest());
  if (page !== "san-pham") $("navQ").value = "";
  document.querySelectorAll(".page").forEach((s) => { s.hidden = s.dataset.page !== page; });
  document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === page));
  document.title = page === "home" ? TITLES.home : `${TITLES[page]} – So Giá`;
  if (page === "so-sanh") { fillCmpControls(); renderCompare(); }
  if (page === "san-pham") { fillPrdControls(); renderProducts(); }
  if (page === "khuyen-mai") { fillKmControls(); renderPromos(); }
  if (page === "yeu-thich") renderFavs();
  if (changed) window.scrollTo(0, 0);
  observe(document.querySelector(`.page[data-page="${page}"]`));
}

/* ================================================================ cards */
function cartBtn(i, small) {
  const inCart = cart[i] > 0;
  return `<button class="btn ${inCart ? "added" : "primary"} ${small ? "small" : ""}" type="button" data-cart="${i}">${inCart ? svg(I.check) + " Đã có trong giỏ" : "+ Thêm vào giỏ"}</button>`;
}
function favBtn(i) {
  const on = favs.has(PRODUCTS[i].u);
  return `<button class="fav ${on ? "on" : ""}" type="button" data-fav="${i}" aria-pressed="${on}" aria-label="${on ? "Bỏ yêu thích" : "Yêu thích"}">${svg(I.heart)}</button>`;
}

function pairCard(x, k) {
  const B = PRODUCTS[x.b], W = PRODUCTS[x.w];
  const photo = B.img ? B : W;
  const box = (s, P, price) => `
    <div class="pbox ${x.ch === s ? "win" : ""}">
      ${x.ch === s ? `<span class="cheap-flag">Rẻ hơn</span>` : ""}
      <div class="store-name">${dot(s)}${STORE[s]}</div>
      <div class="price">${money(price)}</div>
      ${P.l ? `<span class="old">${money(P.l)}</span>` : ""}
    </div>`;
  const verdict = x.ch === "="
    ? `<p class="verdict eq">${svg(I.eq)}Hai nơi bằng giá</p>`
    : `<p class="verdict">${svg(I.tag)}<span>Mua ở ${SHORT[x.ch]} tiết kiệm <b>${money(pairSave(x))}</b> (${pct(pairPct(x))})</span></p>`;
  const tags = promoTags(B, "BHX: ") + promoTags(W, "WinMart: ");
  return `
    <article class="card enter" style="animation-delay:${Math.min(k || 0, 12) * 35}ms">
      <div class="card-body">
        <div class="pair-top">
          <button class="pair-img" type="button" data-qv="${photo === B ? x.b : x.w}" aria-label="Xem nhanh ${esc(B.n)}">${img(photo)}</button>
          <div>
            <h3 class="clamp"><button type="button" data-qv="${x.b}">${esc(B.n)}</button></h3>
            ${norm(B.n) !== norm(W.n) ? `<p class="alt-name clamp">WinMart: ${esc(W.n)}</p>` : ""}
            <p class="sub">${esc(META.groups[x.g])}${sizeText(B) ? " · " + esc(sizeText(B)) : ""}</p>
          </div>
        </div>
        <div class="prices">${box("b", B, x.bp)}${box("w", W, x.wp)}</div>
        ${verdict}
        ${tags ? `<div class="tags">${tags}</div>` : ""}
        <div class="card-foot">${cartBtn(x.i)}</div>
        <div class="links">
          <a class="btn ghost" href="${esc(B.u)}" target="_blank" rel="noopener">${dot("b")}Xem ở BHX</a>
          <a class="btn ghost" href="${esc(W.u)}" target="_blank" rel="noopener">${dot("w")}Xem ở WinMart</a>
        </div>
      </div>
    </article>`;
}

function productCard(p, k) {
  const other = p.s === "b" ? "w" : "b";
  const tag = p.f ? `<div class="tags"><span class="tag flash">⚡ Flash sale</span></div>`
    : p.pt ? `<div class="tags"><span class="tag promo">${esc(p.pt)}</span></div>` : "";
  return `
    <article class="card enter" style="animation-delay:${Math.min(k || 0, 12) * 30}ms">
      ${favBtn(p.i)}
      <button class="thumb" type="button" data-qv="${p.i}" aria-label="Xem nhanh ${esc(p.n)}">
        ${img(p)}
        <span class="pill store">${dot(p.s)}${SHORT[p.s]}</span>
        ${p.d ? `<span class="pill off">-${Math.round(p.d)}%</span>` : ""}
        <span class="qv-hint">Xem nhanh</span>
      </button>
      <div class="card-body">
        <h3 class="clamp"><button type="button" data-qv="${p.i}" title="${esc(p.n)}">${esc(p.n)}</button></h3>
        <p class="sub">${[p.br, sizeText(p)].filter(Boolean).map(esc).join(" · ")}</p>
        <div>
          <span class="price">${money(p.p)}</span>${p.l ? `<span class="old">${money(p.l)}</span>` : ""}
          ${unitText(p) ? `<div class="unit">${unitText(p)}</div>` : ""}
        </div>
        ${tag}
        <div class="card-foot">
          ${p.m !== undefined ? `<button class="btn primary small" type="button" data-compare="${p.m}">So giá với ${SHORT[other]}</button>` : ""}
          <a class="btn small" href="${esc(p.u)}" target="_blank" rel="noopener" aria-label="Xem ở ${STORE[p.s]}">${p.m !== undefined ? svg(I.ext) : "Xem ở " + SHORT[p.s] + " " + svg(I.ext)}</a>
        </div>
      </div>
    </article>`;
}

const emptyBox = (title, text, action) => `<div class="empty">${svg(I.search)}<h3>${title}</h3>${text}${action || ""}</div>`;

/* ================================================================ home */
function renderHome() {
  const c = META.pairs_cheaper;
  $("heroEyebrow").textContent = `Giá thật của ${nf.format(META.products)} sản phẩm · thu thập ${META.collected_from.slice(0, 10)}`;
  $("hcPairs").textContent = META.pairs;
  [["hcB", c.b], ["hcW", c.w], ["hcEq", c["="]]].forEach(([id, v]) => { $(id).dataset.to = v; });
  const seg = (n, cls, label) => `<span class="dot-${cls}" style="flex:${n}" data-tip="<b>${label}</b><br>${n} cặp (${pct(n / META.pairs * 100)})"></span>`;
  $("hcSplit").innerHTML = seg(c.b, "b", "Rẻ hơn ở BHX") + seg(c["="], "eq", "Bằng giá") + seg(c.w, "w", "Rẻ hơn ở WinMart");
  $("hcNote").innerHTML = `Không siêu thị nào rẻ hơn hẳn: khoảng <b>${Math.round(META.pairs_within_10pct)}%</b> số cặp chênh nhau không quá 10%. Muốn tiết kiệm, hãy so <b>từng món</b>.`;
  $("heroChips").innerHTML = `<span class="chip-lbl">Tìm nhanh:</span>` + QUICK.map((q) => `<button class="chip" type="button" data-quick="${esc(q)}">${esc(q)}</button>`).join("");
  $("menuNote").textContent = `Giá cập nhật ngày ${META.collected_from.slice(0, 10)}`;

  // ticker: biggest gaps, duplicated for a seamless loop
  const top = PAIRS.map((x, i) => ({ ...x, i })).filter((x) => x.ch !== "=").sort((a, b) => pairSave(b) - pairSave(a)).slice(0, 14);
  const tk = top.map((x) => `<a class="tk" href="#/so-sanh?cap=${x.i}">${dot(x.ch)}${esc(PRODUCTS[x.b].n)} · rẻ hơn <b>${money(pairSave(x))}</b> ở ${SHORT[x.ch]}</a>`).join("");
  $("ticker").innerHTML = tk + tk.replace(/<a /g, '<a tabindex="-1" aria-hidden="true" ');

  const promoCount = PRODUCTS.filter(isPromo).length;
  const stats = [
    [I.box, META.products, "sản phẩm có giá"],
    [I.scale, META.pairs, "cặp cùng sản phẩm"],
    [I.percent, promoCount, "món đang khuyến mãi"],
    [I.grid, Object.keys(META.groups).length, "nhóm hàng thiết yếu"],
  ];
  $("statsStrip").innerHTML = stats.map(([ic, v, l]) => `<div class="stat"><span class="stat-ic">${svg(ic)}</span><div><b data-to="${v}">0</b><span>${l}</span></div></div>`).join("");

  const order = Object.keys(META.groups).sort((a, b) => META.group_counts[b] - META.group_counts[a]);
  $("cats").innerHTML = order.map((g) => `
    <a class="cat" href="#/san-pham?nhom=${g}">
      <span class="cat-ic">${svg(ICON[g])}</span>
      <b>${esc(META.groups[g])}</b>
      <small>${nf.format(META.group_counts[g])} sản phẩm</small>
    </a>`).join("");

  $("deals").innerHTML = top.slice(0, 6).map(pairCard).join("");
  const promos = PRODUCTS.filter((p) => p.d && p.img).sort((a, b) => b.d - a.d).slice(0, 15);
  $("promoRail").innerHTML = promos.map(productCard).join("");

  $("groupBars").innerHTML = META.group_pairs.map((r) => {
    const n = r.b + r.w + r["="];
    const s = (v, cls, label) => (v ? `<span class="dot-${cls}" style="flex:${v}" data-tip="<b>${esc(META.groups[r.g])}</b><br>${label}: ${v} / ${n} cặp"></span>` : "");
    return `
      <div class="bar-row" role="row">
        <div class="bar-name" role="rowheader">${esc(META.groups[r.g])}<small>${n} cặp</small></div>
        <div class="bar-track grow" role="cell" aria-label="BHX rẻ hơn ${r.b}, bằng giá ${r["="]}, WinMart rẻ hơn ${r.w}">${s(r.b, "b", "Rẻ hơn ở BHX")}${s(r["="], "eq", "Bằng giá")}${s(r.w, "w", "Rẻ hơn ở WinMart")}</div>
        <div class="bar-val" role="cell">BHX ${r.b} · = ${r["="]} · WM ${r.w}</div>
      </div>`;
  }).join("");
}

function rotateWord() {
  if (reduceMotion) return;
  let k = 0;
  setInterval(() => {
    const el = $("rot");
    if (!el || S.page !== "home") return;
    el.classList.add("out");
    setTimeout(() => { k = (k + 1) % ROTATE.length; el.textContent = ROTATE[k]; el.classList.remove("out"); }, 350);
  }, 2800);
}

/* ================================================================ compare page */
function fillCmpControls() {
  const c = S.cmp;
  $("cmpQ").value = c.q; $("cmpSort").value = c.sort;
  document.querySelectorAll("[data-cheap]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.cheap === c.cheap));
  const count = (g) => PAIRS.filter((x) => !g || x.g === g).length;
  $("cmpChips").innerHTML = [["", "Tất cả"], ...Object.entries(META.groups)].map(([g, name]) =>
    `<button class="chip ${c.g === g ? "on" : ""}" type="button" data-cmpg="${g}">${esc(name)} <small>(${count(g)})</small></button>`).join("");
}

function renderCompare() {
  const c = S.cmp;
  let list = PAIRS.map((x, i) => ({ ...x, i }));
  if (c.focus !== null) list = list.filter((x) => x.i === c.focus);
  else {
    list = list.filter((x) => (!c.g || x.g === c.g) && (!c.cheap || x.ch === c.cheap) && matches(x.key, c.q));
    const by = {
      save: (a, b) => pairSave(b) - pairSave(a),
      pct: (a, b) => pairPct(b) - pairPct(a),
      price: (a, b) => pairMin(a) - pairMin(b),
      name: (a, b) => PRODUCTS[a.b].n.localeCompare(PRODUCTS[b.b].n, "vi"),
    }[c.sort];
    list.sort(by);
  }
  const shown = list.slice(0, c.limit);
  let empty = emptyBox("Không có cặp nào phù hợp", "Thử bỏ bớt bộ lọc hoặc gõ ngắn hơn.");
  if (!list.length && c.q) {
    const hits = PRODUCTS.reduce((n, p) => n + (matches(p.key, c.q) ? 1 : 0), 0);
    if (hits) empty = emptyBox(`Chưa có cặp “${esc(c.q)}” bán ở cả hai nơi`,
      `Có ${nf.format(hits)} sản phẩm khớp trong danh sách đầy đủ — có thể chỉ bán ở một siêu thị hoặc khác khối lượng.<br>`,
      `<button class="btn primary" type="button" data-goto-products="${esc(c.q)}">Xem ${nf.format(hits)} sản phẩm</button>`);
  }
  $("cmpList").innerHTML = shown.length ? shown.map(pairCard).join("") : empty;
  $("cmpMore").hidden = list.length <= c.limit;
  $("cmpMore").textContent = `Xem thêm ${Math.min(PAGE_PAIRS, list.length - shown.length)} cặp (còn ${list.length - shown.length})`;
  const saveAll = list.reduce((s, x) => s + pairSave(x), 0);
  $("cmpInfo").innerHTML = c.focus !== null
    ? `Đang xem 1 cặp sản phẩm. <a href="#/so-sanh">Xem tất cả ${PAIRS.length} cặp →</a>`
    : `<b>${nf.format(list.length)}</b> cặp giống hệt nhau (cùng thương hiệu, khối lượng, số lượng)` +
      (list.length ? ` · mua mỗi món một cái ở đúng nơi rẻ hơn tiết kiệm tổng cộng <b>${money(saveAll)}</b>` : "");
}

/* ================================================================ products page */
function fillPrdControls() {
  const c = S.prd;
  $("prdQ").value = c.q; $("prdG").value = c.g; $("prdPrice").value = c.price; $("prdSort").value = c.sort;
  $("prdPromo").checked = c.promo; $("prdBoth").checked = c.both;
  document.querySelectorAll("[data-store]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.store === c.store));
}

function inPrice(p, range) {
  if (!range) return true;
  const [lo, hi] = range.split("-");
  return p.p >= +lo && (hi === "" || p.p < +hi);
}

function renderProducts() {
  const c = S.prd;
  let list = PRODUCTS.filter((p) =>
    (!c.g || p.g === c.g) && (!c.store || p.s === c.store) && (!c.promo || isPromo(p)) &&
    (!c.both || p.m !== undefined) && inPrice(p, c.price) && matches(p.key, c.q));
  const last = Number.MAX_SAFE_INTEGER;
  const by = {
    relevant: c.q ? (a, b) => relevance(a, c.q) - relevance(b, c.q) : null,
    price: (a, b) => a.p - b.p,
    "price-desc": (a, b) => b.p - a.p,
    unit: (a, b) => (a.up || last) - (b.up || last),
    disc: (a, b) => (b.d || 0) - (a.d || 0),
  }[c.sort];
  if (by) list = list.slice().sort(by);
  const shown = list.slice(0, c.limit);
  $("prdTitle").textContent = c.g ? META.groups[c.g] : "Tất cả sản phẩm";
  $("prdList").innerHTML = shown.length ? shown.map(productCard).join("")
    : emptyBox("Không tìm thấy sản phẩm", "Thử gõ ngắn hơn, ví dụ “hảo hảo” thay vì “mì hảo hảo tôm chua cay”, hoặc bỏ bớt bộ lọc.");
  $("prdMore").hidden = list.length <= c.limit;
  $("prdMore").textContent = `Xem thêm ${Math.min(PAGE_PRODUCTS, list.length - shown.length)} sản phẩm (còn ${nf.format(list.length - shown.length)})`;
  const both = list.filter((p) => p.m !== undefined).length;
  $("prdInfo").innerHTML = `<b>${nf.format(list.length)}</b> sản phẩm` + (both ? ` · ${nf.format(both)} món có bán ở cả hai nơi (bấm “So giá”)` : "");

  // removable chips for the filters in use
  const af = [];
  const priceLbl = $("prdPrice").selectedOptions[0]?.textContent;
  if (c.q) af.push(["q", `“${esc(c.q)}”`]);
  if (c.g) af.push(["g", esc(META.groups[c.g])]);
  if (c.price) af.push(["price", esc(priceLbl)]);
  if (c.store) af.push(["store", STORE[c.store]]);
  if (c.promo) af.push(["promo", "Đang khuyến mãi"]);
  if (c.both) af.push(["both", "Có bán cả 2 nơi"]);
  $("prdActive").innerHTML = af.map(([k, l]) => `<button class="af" type="button" data-unfilter="${k}">${l}${svg(I.close)}</button>`).join("") +
    (af.length > 1 ? `<button class="af clear" type="button" data-unfilter="all">Xóa tất cả bộ lọc</button>` : "");
}

/* ================================================================ promotions page */
function fillKmControls() {
  const c = S.km;
  $("kmG").value = c.g;
  document.querySelectorAll("[data-km]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.km === c.type));
  document.querySelectorAll("[data-kmstore]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.kmstore === c.store));
}

function renderPromos() {
  const c = S.km;
  const base = PRODUCTS.filter((p) => (!c.store || p.s === c.store) && (!c.g || p.g === c.g));
  const pick = {
    deep: () => base.filter((p) => p.d).sort((a, b) => b.d - a.d),
    flash: () => base.filter((p) => p.f).sort((a, b) => (b.d || 0) - (a.d || 0)),
    combo: () => base.filter((p) => p.pt).sort((a, b) => a.n.localeCompare(b.n, "vi")),
  }[c.type];
  const list = pick();
  const shown = list.slice(0, c.limit);
  $("kmList").innerHTML = shown.length ? shown.map(productCard).join("") : emptyBox("Không có khuyến mãi phù hợp", "Thử chọn loại khuyến mãi hoặc siêu thị khác.");
  $("kmMore").hidden = list.length <= c.limit;
  $("kmMore").textContent = `Xem thêm (còn ${nf.format(list.length - shown.length)})`;
  const label = { deep: "sản phẩm đang giảm giá", flash: "sản phẩm flash sale", combo: "sản phẩm có ưu đãi mua kèm / combo" }[c.type];
  $("kmInfo").innerHTML = `<b>${nf.format(list.length)}</b> ${label}`;
}

/* ================================================================ statistics page */
function groupedBars(rows, fmt, tipLabel) {
  const max = Math.max(...rows.flatMap((r) => [r.b, r.w]));
  return rows.map((r) => `
    <div class="gb">
      <div class="gb-name">${esc(r.name)}</div>
      ${["b", "w"].map((s) => `<div class="gb-bar"><span class="m dot-${s}" style="width:${(r[s] / max) * 100}%" data-tip="<b>${esc(r.name)} · ${STORE[s]}</b><br>${tipLabel}: ${fmt(r[s])}"></span><em>${fmt(r[s])}</em></div>`).join("")}
    </div>`).join("");
}

function tableView(head, rows) {
  return `<details class="table-view"><summary>Xem bảng số liệu</summary><div class="table-wrap"><table>
    <thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${r.map((v) => `<td>${v}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`;
}

function renderStats() {
  const st = META.stats;
  const gs = Object.keys(META.groups);
  const byStore = { b: PRODUCTS.filter((p) => p.s === "b"), w: PRODUCTS.filter((p) => p.s === "w") };
  const medAll = { b: median(byStore.b.map((p) => p.p)), w: median(byStore.w.map((p) => p.p)) };
  const promoAll = Object.fromEntries(["b", "w"].map((s) => {
    const n = gs.reduce((a, g) => a + st.groups[g][s].n, 0);
    return [s, gs.reduce((a, g) => a + st.groups[g][s].promo * st.groups[g][s].n, 0) / n];
  }));
  $("kpis").innerHTML = [
    [nf.format(META.products), `sản phẩm · BHX ${nf.format(META.by_store.b)} / WinMart ${nf.format(META.by_store.w)}`],
    [META.pairs, `cặp cùng sản phẩm · BHX rẻ hơn ${META.pairs_cheaper.b}, WinMart rẻ hơn ${META.pairs_cheaper.w}`],
    [`${nf.format(Math.round(medAll.b / 1000))}k / ${nf.format(Math.round(medAll.w / 1000))}k`, "giá trung vị BHX / WinMart (cả kệ hàng)"],
    [`${pct(promoAll.b)} / ${pct(promoAll.w)}`, "tỉ lệ sản phẩm đang khuyến mãi BHX / WinMart"],
  ].map(([b, s]) => `<div class="kpi reveal"><b>${b}</b><span>${s}</span></div>`).join("");

  const rows = (key) => gs.map((g) => ({ name: META.groups[g], b: st.groups[g].b[key], w: st.groups[g].w[key] }));
  const cnt = rows("n").sort((a, b) => b.b + b.w - a.b - a.w);
  const med = rows("med").sort((a, b) => b.w - a.w);
  const pro = rows("promo").sort((a, b) => b.b - a.b);
  const wMore = (rs) => rs.filter((r) => r.w > r.b).length;

  // histogram of the signed gap (WinMart vs BHX, %): negative = WinMart cheaper, 0 = same price, positive = BHX cheaper
  const bins = [];
  for (let lo = -35; lo < 0; lo += 5) bins.push({ lo, hi: lo + 5, n: 0, s: "w" });
  bins.push({ lo: 0, hi: 0, n: 0, s: "eq" });
  for (let lo = 0; lo < 50; lo += 5) bins.push({ lo, hi: lo + 5, n: 0, s: "b" });
  for (const d of st.diffs) {
    const b = d === 0 ? bins.find((x) => x.s === "eq")
      : d < 0 ? bins.find((x) => x.s === "w" && d >= x.lo && d < x.hi) || bins[0]
      : bins.find((x) => x.s === "b" && d > x.lo && d <= x.hi) || bins[bins.length - 1];
    b.n++;
  }
  const hmax = Math.max(...bins.map((b) => b.n));
  const binLabel = (b) => b.s === "eq" ? "Bằng giá" : b.s === "w" ? `WinMart rẻ hơn ${-b.hi}–${-b.lo}%` : `BHX rẻ hơn (WinMart đắt hơn ${b.lo}–${b.hi}%)`;
  const hist = `<div class="hist">${bins.map((b) => `<span class="dot-${b.s}" style="height:${(b.n / hmax) * 100}%" data-tip="<b>${binLabel(b)}</b><br>${b.n} cặp"></span>`).join("")}</div>
    <div class="hist-axis"><span>WinMart rẻ hơn 35%</span><span>bằng giá</span><span>WinMart đắt hơn 50%</span></div>`;

  const bands = st.bands;
  const bandRow = (s) => {
    const n = bands[s].reduce((a, v) => a + v, 0);
    return `<div class="stack-row"><span>${dot(s)}${STORE[s]}</span><div class="stack">${bands[s].map((v, k) =>
      `<span style="flex:${v};background:var(--band-${k + 1});color:${k === 0 ? "#0b0b0b" : "#fff"}" data-tip="<b>${STORE[s]} · ${BANDS[k]}</b><br>${nf.format(v)} sản phẩm (${pct(v / n * 100)})">${Math.round(v / n * 100)}%</span>`).join("")}</div></div>`;
  };
  const share = (s, k) => bands[s][k] / bands[s].reduce((a, v) => a + v, 0) * 100;

  $("charts").innerHTML = `
    <article class="chart reveal">
      <h3>Số sản phẩm theo nhóm hàng</h3><p class="note">Mỗi siêu thị bày bán bao nhiêu sản phẩm trong từng nhóm.</p>
      ${groupedBars(cnt, (v) => nf.format(v), "Số sản phẩm")}
      <p class="take">WinMart có nhiều sản phẩm hơn ở <b>${wMore(cnt)}/7</b> nhóm — hai kệ hàng có cơ cấu khác nhau.</p>
      ${tableView(["Nhóm hàng", "BHX", "WinMart"], cnt.map((r) => [esc(r.name), nf.format(r.b), nf.format(r.w)]))}
    </article>
    <article class="chart reveal">
      <h3>Giá bán trung vị theo nhóm hàng</h3><p class="note">Giá ở giữa (median) của cả kệ hàng, đơn vị đồng.</p>
      ${groupedBars(med, money, "Giá trung vị")}
      <p class="take">WinMart có giá trung vị cao hơn ở <b>${wMore(med)}/7</b> nhóm — nhưng đó là do <b>khác mặt hàng</b>; so cùng sản phẩm thì không bên nào rẻ hơn hẳn.</p>
      ${tableView(["Nhóm hàng", "BHX", "WinMart"], med.map((r) => [esc(r.name), money(r.b), money(r.w)]))}
    </article>
    <article class="chart reveal">
      <h3>Tỉ lệ sản phẩm đang khuyến mãi</h3><p class="note">Phần trăm sản phẩm có giảm giá trong từng nhóm.</p>
      ${groupedBars(pro, pct, "Đang khuyến mãi")}
      <p class="take">BHX khuyến mãi nhiều hơn ở <b>${7 - wMore(pro)}/7</b> nhóm, rõ nhất ở ${esc(pro[0].name.toLowerCase())} (${pct(pro[0].b)}).</p>
      ${tableView(["Nhóm hàng", "BHX", "WinMart"], pro.map((r) => [esc(r.name), pct(r.b), pct(r.w)]))}
    </article>
    <article class="chart reveal">
      <h3>Phân khúc giá</h3><p class="note">Tỉ lệ sản phẩm theo 3 khoảng giá bán.</p>
      ${bandRow("b")}${bandRow("w")}
      <div class="band-legend">${BANDS.map((b, k) => `<span><span class="sw" style="background:var(--band-${k + 1})"></span>${b}</span>`).join("")}</div>
      <p class="take">BHX có <b>${pct(share("b", 0))}</b> sản phẩm dưới 20.000 đ, WinMart chỉ <b>${pct(share("w", 0))}</b> — một lý do khiến giá trung vị của BHX thấp hơn.</p>
      ${tableView(["Siêu thị", ...BANDS], ["b", "w"].map((s) => [STORE[s], ...bands[s].map((v) => nf.format(v))]))}
    </article>
    <article class="chart wide reveal">
      <h3>Chênh lệch giá của ${META.pairs} cặp cùng sản phẩm</h3>
      <p class="note">Mỗi cột là số cặp có mức chênh trong khoảng 5%. Bên trái: WinMart rẻ hơn; giữa: bằng giá; bên phải: BHX rẻ hơn.</p>
      <div class="legend"><span>${dot("w")}WinMart rẻ hơn</span><span>${dot("eq")}Bằng giá</span><span>${dot("b")}BHX rẻ hơn</span></div>
      ${hist}
      <p class="take">Các cột dồn quanh mức 0 và hai bên gần cân bằng (${META.pairs_cheaper.w} so với ${META.pairs_cheaper.b}): khoảng <b>${Math.round(META.pairs_within_10pct)}%</b> số cặp chênh không quá 10%. Cùng một món thì <b>không siêu thị nào rẻ hơn một cách có hệ thống</b>.</p>
      ${tableView(["Khoảng chênh", "Số cặp"], bins.map((b) => [binLabel(b), b.n]))}
    </article>`;
}

/* ================================================================ favorites + about */
function renderFavs() {
  const list = PRODUCTS.filter((p) => favs.has(p.u));
  $("favInfo").innerHTML = list.length ? `<b>${list.length}</b> sản phẩm yêu thích` : "";
  $("favList").innerHTML = list.length ? list.map(productCard).join("")
    : `<div class="empty">${svg(I.heart)}<h3>Chưa có sản phẩm yêu thích</h3>Bấm biểu tượng ♥ trên ảnh sản phẩm để lưu lại xem sau.<br><a class="btn primary" href="#/san-pham">Khám phá sản phẩm</a></div>`;
}

function renderAbout() {
  const c = META.pairs_cheaper;
  const time = `${META.collected_from.slice(11)}–${META.collected_to.slice(11)}`;
  const facts = [
    [META.products, "sản phẩm có giá"],
    [META.by_store.b, "sản phẩm Bách Hóa Xanh"],
    [META.by_store.w, "sản phẩm WinMart"],
    [Object.keys(META.groups).length, "nhóm hàng tiêu dùng"],
    [META.pairs, "cặp cùng sản phẩm ở cả 2 nơi"],
  ];
  $("facts").innerHTML = facts.map(([b, s]) => `<div class="fact"><b data-to="${b}">0</b><span>${s}</span></div>`).join("") +
    `<div class="fact"><b>${META.collected_from.slice(0, 10)}</b><span>ngày thu thập (${time})</span></div>`;
  $("facts").classList.add("reveal");
  const steps = [
    ["Thu thập", `Chương trình Python đọc giá từ website công khai của hai siêu thị trong cùng một buổi (${time}, ngày ${META.collected_from.slice(0, 10)}), lưu dữ liệu gốc và vào SQL Server.`],
    ["Làm sạch", `Loại ${META.duplicates_removed} dòng trùng, sửa ${META.values_fixed} giá trị số lượng bị đọc sai, xử lý giá trị thiếu có đánh dấu — không xóa sản phẩm nào có giá thật.`],
    ["Ghép cặp", `So khớp tên, thương hiệu, khối lượng, số lượng và hương vị để tìm ra ${META.pairs} cặp sản phẩm giống hệt nhau ở hai siêu thị.`],
    ["Phân tích", "Thống kê mô tả, kiểm định ý nghĩa thống kê và trực quan hóa để trả lời: cùng một món thì nơi nào rẻ hơn?"],
  ];
  $("pipeline").innerHTML = steps.map(([h, p]) => `<li><h3>${h}</h3><p>${p}</p></li>`).join("");
  const big = META.group_pairs.filter((r) => r.b + r.w + r["="] >= 10);
  $("findings").innerHTML = [
    `Trong ${META.pairs} cặp cùng sản phẩm: <b>${c.b}</b> cặp rẻ hơn ở Bách Hóa Xanh, <b>${c.w}</b> cặp rẻ hơn ở WinMart, <b>${c["="]}</b> cặp bằng giá — <b>không siêu thị nào rẻ hơn một cách có hệ thống</b>.`,
    `Khoảng <b>${Math.round(META.pairs_within_10pct)}%</b> số cặp chênh nhau không quá 10%; một số ít món chênh rất lớn — đó là chỗ người mua tiết kiệm được nhiều nhất.`,
    `Theo nhóm hàng: ${big.map((r) => `${META.groups[r.g]} (BHX rẻ hơn ${r.b}, WinMart rẻ hơn ${r.w})`).join("; ")}.`,
    `${nf.format(PRODUCTS.filter(isPromo).length)} sản phẩm đang có khuyến mãi tại thời điểm thu thập.`,
    `Lời khuyên: đừng mặc định một siêu thị luôn rẻ hơn — hãy so từng món, hoặc cho cả giỏ hàng vào để biết nên mua ở đâu.`,
  ].map((t) => `<li>${t}</li>`).join("");
  const faq = [
    ["Giá trên website có phải giá hiện tại không?", `Không hẳn. Giá được thu thập ngày ${META.collected_from.slice(0, 10)} (${time}). Khuyến mãi thay đổi hằng ngày, vì vậy hãy bấm “Xem ở BHX / WinMart” để kiểm tra giá hiện tại trước khi mua.`],
    ["“Cùng một sản phẩm” được xác định như thế nào?", "Hai sản phẩm chỉ được ghép cặp khi cùng thương hiệu, cùng khối lượng hoặc dung tích, cùng số lượng trong gói và cùng hương vị, tên gần giống nhau. Nhờ vậy phép so sánh luôn công bằng."],
    ["Vì sao có món chỉ thấy ở một siêu thị?", "Mỗi siêu thị bán mặt hàng và quy cách khác nhau (ví dụ một bên bán lốc 6, bên kia bán thùng 24). Những món không có bản giống hệt ở nơi còn lại vẫn xem được ở trang Sản phẩm."],
    ["“Giá theo kg / lít” dùng để làm gì?", "Để so gói to với gói nhỏ, hoặc thương hiệu này với thương hiệu khác. Khi xem nhanh một sản phẩm, trang gợi ý các món cùng danh mục có giá theo kg/lít rẻ hơn."],
    ["Giỏ hàng và mục yêu thích có lưu thông tin của tôi không?", "Chỉ lưu trên trình duyệt của chính bạn (localStorage), không gửi đi đâu. Khi bấm “Chia sẻ giỏ hàng”, đường link chỉ chứa mã sản phẩm và số lượng."],
    ["Website có liên kết với Bách Hóa Xanh hay WinMart không?", "Không. Đây là sản phẩm học tập của nhóm sinh viên môn ADY201m, dữ liệu lấy từ website công khai của hai siêu thị."],
  ];
  $("faq").innerHTML = faq.map(([q, a], k) => `<details ${k === 0 ? "open" : ""}><summary>${q}</summary><p>${a}</p></details>`).join("");
  $("limits").innerHTML = [
    "Giá là ảnh chụp tại một thời điểm, khuyến mãi thay đổi hằng ngày — luôn kiểm tra giá hiện tại trước khi mua.",
    "Giá theo khu vực mặc định của mỗi website (chưa chọn địa chỉ giao hàng); giá ở cửa hàng hoặc khu vực khác có thể khác.",
    "Chỉ gồm 7 nhóm hàng tiêu dùng nhanh; không có rau củ, thịt cá tươi.",
    "Giỏ hàng chỉ tính những món đã ghép được cặp giống hệt nhau, để phép so sánh luôn công bằng.",
  ].map((t) => `<li>${t}</li>`).join("");
  $("footMeta").textContent = `${nf.format(META.products)} sản phẩm · ${META.pairs} cặp cùng sản phẩm · thu thập ${META.collected_from.slice(0, 10)}.`;
  $("cmpLead").textContent = `${META.pairs} cặp sản phẩm giống hệt nhau có bán ở cả hai siêu thị. Ô viền xanh là nơi rẻ hơn.`;
  $("prdLead").textContent = `${nf.format(META.products)} sản phẩm của Bách Hóa Xanh (${nf.format(META.by_store.b)}) và WinMart (${nf.format(META.by_store.w)}). Bấm vào ảnh để xem nhanh và gợi ý món rẻ hơn theo kg/lít.`;
  $("kmLead").textContent = `${nf.format(PRODUCTS.filter(isPromo).length)} sản phẩm đang có ưu đãi tại thời điểm thu thập: giảm giá, flash sale, mua kèm, combo.`;
}

/* ================================================================ quick view */
let modalReturn = null;
function cheaperAlternatives(p) {
  if (!p.up || !p.c) return null;
  const peers = PRODUCTS.filter((q) => q.c === p.c && q.su === p.su && q.up && q.i !== p.i);
  if (!peers.length) return null;
  return peers.filter((q) => q.up < p.up * 0.97).sort((a, b) => a.up - b.up).slice(0, 4);
}

function openQuickView(i) {
  const p = PRODUCTS[i];
  const x = p.m !== undefined ? { ...PAIRS[p.m], i: p.m } : null;
  const other = x ? PRODUCTS[p.s === "b" ? x.w : x.b] : null;
  const alts = cheaperAlternatives(p);
  const on = favs.has(p.u);
  let compare = "";
  if (x) {
    const box = (s, price) => `<div class="pbox ${x.ch === s ? "win" : ""}">${x.ch === s ? `<span class="cheap-flag">Rẻ hơn</span>` : ""}<div class="store-name">${dot(s)}${STORE[s]}</div><div class="price">${money(price)}</div></div>`;
    compare = `<div class="qv-section"><h3>So với ${STORE[p.s === "b" ? "w" : "b"]}</h3>
      ${other && norm(other.n) !== norm(p.n) ? `<p class="sub" style="margin-bottom:8px">${esc(other.n)}</p>` : ""}
      <div class="prices">${box("b", x.bp)}${box("w", x.wp)}</div>
      <p class="verdict" style="margin-top:8px">${x.ch === "=" ? svg(I.eq) + "Hai nơi bằng giá" : svg(I.tag) + `<span>Mua ở ${SHORT[x.ch]} tiết kiệm <b>${money(pairSave(x))}</b> (${pct(pairPct(x))})</span>`}</p>
      <div style="margin-top:8px">${cartBtn(x.i)}</div></div>`;
  }
  let altHtml = "";
  if (alts && alts.length) {
    altHtml = `<div class="qv-section"><h3>Rẻ hơn theo ${p.su === "ml" ? "lít" : "kg"} trong “${esc(p.c)}”</h3><div class="alts">${alts.map((q) => `
      <button class="alt" type="button" data-qv="${q.i}">
        <span class="pair-img">${img(q)}</span>
        <span><span class="alt-n clamp">${esc(q.n)}</span><span class="alt-m">${dot(q.s)}${SHORT[q.s]} · ${money(q.p)}${sizeText(q) ? " · " + esc(sizeText(q)) : ""}</span></span>
        <span class="alt-p"><b>-${Math.round((1 - q.up / p.up) * 100)}%</b>${money(q.up)}${perUnit(q)}</span>
      </button>`).join("")}</div></div>`;
  } else if (alts) {
    altHtml = `<div class="qv-section"><p class="verdict">${svg(I.check)}<span>Đây là lựa chọn <b>rẻ nhất theo ${p.su === "ml" ? "lít" : "kg"}</b> trong danh mục “${esc(p.c)}”.</span></p></div>`;
  }
  $("modalBox").innerHTML = `
    <button class="icon-btn qv-close" type="button" data-close-modal aria-label="Đóng">${svg(I.close)}</button>
    <div class="qv">
      <div class="qv-img">${img(p)}<span class="pill store">${dot(p.s)}${STORE[p.s]}</span>${p.d ? `<span class="pill off">-${Math.round(p.d)}%</span>` : ""}</div>
      <div class="qv-body">
        <h2 id="qvTitle">${esc(p.n)}</h2>
        <div class="qv-price"><span class="price">${money(p.p)}</span>${p.l ? `<span class="old">${money(p.l)}</span>` : ""}${unitText(p) ? `<span class="unit">${unitText(p)}</span>` : ""}</div>
        ${promoTags(p, "") ? `<div class="tags">${promoTags(p, "")}</div>` : ""}
        <dl class="spec">
          ${p.br ? `<dt>Thương hiệu</dt><dd>${esc(p.br)}</dd>` : ""}
          ${sizeText(p) ? `<dt>Quy cách</dt><dd>${esc(sizeText(p))}</dd>` : ""}
          <dt>Nhóm hàng</dt><dd>${esc(META.groups[p.g])}${p.c && norm(p.c) !== norm(META.groups[p.g]) ? " · " + esc(p.c) : ""}</dd>
          <dt>Siêu thị</dt><dd>${STORE[p.s]}</dd>
        </dl>
        ${compare}
        ${altHtml}
        <div class="qv-actions">
          <a class="btn primary" href="${esc(p.u)}" target="_blank" rel="noopener">Xem ở ${STORE[p.s]} ${svg(I.ext)}</a>
          <button class="btn" type="button" data-fav="${p.i}" data-fav-text>${on ? "♥ Đã yêu thích" : "♡ Yêu thích"}</button>
        </div>
      </div>
    </div>`;
  // returning focus to a search box would reopen its suggestions, so fall back to the page in that case
  if ($("modal").hidden) modalReturn = document.activeElement && document.activeElement.type === "search" ? null : document.activeElement;
  $("modal").hidden = false;
  document.body.classList.add("no-scroll");
  $("modalBox").scrollTop = 0;
  $("modalBox").focus();
}
function closeModal(silent) {
  if ($("modal").hidden) return;
  $("modal").hidden = true;
  if (!$("drawer").classList.contains("open")) document.body.classList.remove("no-scroll");
  if (!silent && modalReturn && document.contains(modalReturn)) modalReturn.focus();
}

/* ================================================================ search suggestions */
function attachSuggest(input, list, onSubmit) {
  let on = -1, timer;
  const close = () => { list.hidden = true; input.setAttribute("aria-expanded", "false"); on = -1; };
  const items = () => [...list.querySelectorAll(".sg, .sg-all")];
  const render = () => {
    const q = input.value.trim();
    if (!q) { close(); return; }
    const hits = PRODUCTS.filter((p) => matches(p.key, q)).sort((a, b) => relevance(a, q) - relevance(b, q));
    const pairsHit = PAIRS.filter((x) => matches(x.key, q)).length;
    list.innerHTML = hits.length ? `<div class="sg-head">Sản phẩm</div>` + hits.slice(0, 6).map((p) => `
      <button class="sg" type="button" role="option" data-qv="${p.i}">
        <span class="pair-img">${img(p)}</span>
        <span><span class="sg-name clamp">${highlight(p.n, q)}</span><span class="sg-meta">${dot(p.s)}${SHORT[p.s]}${sizeText(p) ? " · " + esc(sizeText(p)) : ""}</span></span>
        <span class="sg-price">${money(p.p)}</span>
      </button>`).join("") +
      (pairsHit ? `<a class="sg-all" href="#/so-sanh?q=${encodeURIComponent(q)}" role="option">So sánh ${pairsHit} cặp cùng sản phẩm cho “${esc(q)}” →</a>` : "") +
      `<a class="sg-all" href="#/san-pham?q=${encodeURIComponent(q)}" role="option">Xem tất cả ${nf.format(hits.length)} kết quả →</a>`
      : `<div class="sg-empty">Không tìm thấy “${esc(q)}”. Thử gõ ngắn hơn.</div>`;
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    on = -1;
  };
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(render, 90); });
  input.addEventListener("click", () => { if (list.hidden && input.value.trim()) render(); });
  input.closeSuggest = close;
  input.addEventListener("keydown", (e) => {
    const it = items();
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (list.hidden || !it.length) return;
      e.preventDefault();
      on = (on + (e.key === "ArrowDown" ? 1 : -1) + it.length) % it.length;
      it.forEach((el, k) => el.classList.toggle("on", k === on));
      it[on].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter" && on >= 0 && it[on]) {
      e.preventDefault(); it[on].click(); close();
    } else if (e.key === "Escape") close();
  });
  input.addEventListener("blur", () => setTimeout(close, 180));
  list.addEventListener("mousedown", (e) => e.preventDefault());   // keep focus so the click lands
  list.addEventListener("click", () => setTimeout(() => { close(); input.blur(); }, 0));
  input.form.addEventListener("submit", (e) => { e.preventDefault(); close(); onSubmit(input.value.trim()); input.blur(); });
}

/* ================================================================ cart */
function cartItems() {
  return Object.entries(cart).filter(([i, q]) => q > 0 && PAIRS[+i]).map(([i, q]) => ({ x: PAIRS[+i], i: +i, q }));
}
function cartTotals(items) {
  let b = 0, w = 0, s = 0;
  for (const { x, q } of items) { b += x.bp * q; w += x.wp * q; s += pairMin(x) * q; }
  return { b, w, s };
}
function saveCart(bump) {
  storage("sogia-cart", JSON.stringify(cart));
  const n = Object.values(cart).reduce((s, q) => s + q, 0);
  $("cartCount").textContent = n;
  if (bump) { const el = $("cartCount"); el.classList.remove("bump"); void el.offsetWidth; el.classList.add("bump"); }
}
function saveFavs() {
  storage("sogia-favs", JSON.stringify([...favs]));
  $("favCount").textContent = favs.size;
  $("favCount").hidden = !favs.size;
}

function renderCart() {
  const items = cartItems();
  const n = items.reduce((s, it) => s + it.q, 0);
  $("drawerCount").textContent = n ? `(${n} món)` : "";
  if (!items.length) {
    $("drawerBody").innerHTML = `<div class="drawer-empty">${svg(I.bag)}<h3>Giỏ hàng đang trống</h3>
      <p>Thêm những món bạn định mua, trang sẽ tính tổng tiền ở mỗi siêu thị và chỉ ra cách mua rẻ nhất.</p>
      <a class="btn primary" href="#/so-sanh" data-close>Tìm món để so sánh</a></div>`;
    $("drawerFoot").innerHTML = "";
    return;
  }
  $("drawerBody").innerHTML = items.map(({ x, i, q }) => {
    const B = PRODUCTS[x.b];
    const where = x.ch === "=" ? "Hai nơi bằng giá" : `${dot(x.ch)}Nên mua ở ${SHORT[x.ch]}`;
    return `
      <div class="ci">
        <button class="pair-img" type="button" data-qv="${B.img ? x.b : x.w}" aria-label="Xem nhanh">${img(B.img ? B : PRODUCTS[x.w])}</button>
        <div>
          <div class="ci-name clamp">${esc(B.n)}</div>
          <div class="ci-prices">
            <span class="${x.ch === "b" ? "best" : ""}">${dot("b")}${money(x.bp)}</span>
            <span class="${x.ch === "w" ? "best" : ""}">${dot("w")}${money(x.wp)}</span>
          </div>
          <div class="ci-row">
            <span class="where">${where}</span>
            <span class="qty">
              <button type="button" data-qty="${i}" data-d="-1" aria-label="Bớt 1">−</button>
              <span aria-label="Số lượng">${q}</span>
              <button type="button" data-qty="${i}" data-d="1" aria-label="Thêm 1">+</button>
            </span>
          </div>
        </div>
      </div>`;
  }).join("");

  const t = cartTotals(items);
  const best = t.b <= t.w ? "b" : "w", worst = best === "b" ? "w" : "b";
  const bestTotal = Math.min(t.b, t.w), worstTotal = Math.max(t.b, t.w);
  const splitGain = bestTotal - t.s;
  let advice;
  if (splitGain === 0) {
    advice = t.b === t.w ? "Hai nơi tổng tiền bằng nhau — mua ở đâu cũng được."
      : `Mua hết ở <b>${STORE[best]}</b> là rẻ nhất: tiết kiệm <b>${money(worstTotal - bestTotal)}</b> so với mua hết ở ${STORE[worst]}.`;
  } else {
    advice = `Rẻ nhất là <b>mua tách 2 nơi</b> (mỗi món ở nơi rẻ hơn). Muốn đi <b>1 nơi cho nhanh</b>, chọn <b>${STORE[best]}</b> — chỉ đắt hơn mua tách ${money(splitGain)}.`;
  }
  const row = (label, total, on) => `<div class="tot ${on ? "best" : ""}"><span>${label}</span><strong>${money(total)}</strong></div>`;
  $("drawerFoot").innerHTML = `
    ${row(dot("b") + "Mua hết ở BHX", t.b, best === "b" && splitGain === 0 && t.b !== t.w)}
    ${row(dot("w") + "Mua hết ở WinMart", t.w, best === "w" && splitGain === 0 && t.b !== t.w)}
    ${row("Mua tách 2 nơi (rẻ nhất từng món)", t.s, splitGain > 0)}
    ${worstTotal - t.s > 0 ? `<div class="saving"><span>Mua đúng nơi, bạn tiết kiệm</span><b>${money(worstTotal - t.s)}</b></div>` : ""}
    <p class="advice">${advice}</p>
    <div class="drawer-actions">
      <button class="btn primary full" type="button" id="copyList">Sao chép danh sách đi chợ</button>
      <button class="btn" type="button" id="shareCart">Chia sẻ giỏ hàng</button>
      <button class="btn" type="button" id="downloadList">Tải danh sách</button>
      <button class="btn ghost full" type="button" id="clearCart">Xóa giỏ hàng</button>
    </div>`;
}

function shoppingList() {
  const items = cartItems();
  const t = cartTotals(items);
  const single = t.b <= t.w ? "b" : "w";
  const plan = { b: [], w: [] };
  for (const it of items) plan[it.x.ch === "=" ? single : it.x.ch].push(it);
  const lines = ["DANH SÁCH ĐI CHỢ – So Giá BHX vs WinMart", ""];
  for (const s of ["b", "w"]) {
    if (!plan[s].length) continue;
    let sum = 0;
    lines.push(`Mua ở ${STORE[s]}:`);
    for (const { x, q } of plan[s]) {
      const price = s === "b" ? x.bp : x.wp;
      sum += price * q;
      lines.push(`  [ ] ${q} x ${PRODUCTS[x.b].n}: ${money(price * q)}`);
    }
    lines.push(`  Cộng: ${money(sum)}`, "");
  }
  lines.push(`Tổng cộng: ${money(t.s)} (tiết kiệm ${money(Math.max(t.b, t.w) - t.s)} so với mua hết ở nơi đắt hơn)`);
  lines.push(`Giá thu thập ngày ${META.collected_from.slice(0, 10)} — kiểm tra lại giá hiện tại trước khi mua.`);
  return lines.join("\n");
}

const shareLink = () => location.href.split("#")[0] + "#/gio-hang?c=" + cartItems().map(({ i, q }) => `${i}-${q}`).join(".");

function importCart(code) {
  const next = {};
  for (const part of code.split(".")) {
    const [i, q] = part.split("-").map(Number);
    if (PAIRS[i] && q > 0 && q < 100) next[i] = q;
  }
  history.replaceState(null, "", "#/so-sanh");
  onRoute();
  if (Object.keys(next).length) {
    cart = next; saveCart(true); refreshCartButtons();
    openCart();
    toast(`${svg(I.check)}Đã mở giỏ hàng được chia sẻ (${Object.values(next).reduce((a, b) => a + b, 0)} món)`);
  }
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch (e) { /* fall back below */ }
  const ta = document.createElement("textarea");
  ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta); ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
  ta.remove();
  return ok;
}

let lastFocus = null;
function openCart() {
  renderCart();
  lastFocus = document.activeElement;
  $("overlay").hidden = false;
  $("drawer").classList.add("open");
  $("drawer").setAttribute("aria-hidden", "false");
  document.body.classList.add("no-scroll");
  $("drawerClose").focus();
}
function closeCart() {
  if (!$("drawer").classList.contains("open")) return;
  $("overlay").hidden = true;
  $("drawer").classList.remove("open");
  $("drawer").setAttribute("aria-hidden", "true");
  if ($("modal").hidden) document.body.classList.remove("no-scroll");
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
}

let toastTimer;
function toast(html) {
  const t = $("toast");
  t.hidden = true; void t.offsetWidth;
  t.innerHTML = html;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 3400);
}
function refreshCartButtons() {
  document.querySelectorAll("[data-cart]").forEach((b) => { b.outerHTML = cartBtn(+b.dataset.cart, b.classList.contains("small")); });
}
function refreshFavButtons(i) {
  const on = favs.has(PRODUCTS[i].u);
  document.querySelectorAll(`[data-fav="${i}"]`).forEach((b) => {
    if (b.hasAttribute("data-fav-text")) { b.textContent = on ? "♥ Đã yêu thích" : "♡ Yêu thích"; return; }
    b.classList.toggle("on", on); b.setAttribute("aria-pressed", on); b.setAttribute("aria-label", on ? "Bỏ yêu thích" : "Yêu thích");
    if (on) { b.classList.remove("pop"); void b.offsetWidth; b.classList.add("pop"); }
  });
}

/* ================================================================ events */
function bind() {
  window.addEventListener("hashchange", onRoute);
  window.addEventListener("scroll", onScroll, { passive: true });
  bindTooltip();

  attachSuggest($("navQ"), $("navQ-list"), (q) => go("san-pham", { q }));
  attachSuggest($("heroQ"), $("heroQ-list"), (q) => (q && PAIRS.some((x) => matches(x.key, q)) ? go("so-sanh", { q }) : go("san-pham", { q })));

  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) { e.preventDefault(); $("navQ").focus(); }
    if (e.key === "Escape") { if (!$("modal").hidden) closeModal(); else closeCart(); }
  });

  // compare
  let t1;
  $("cmpQ").addEventListener("input", (e) => {
    clearTimeout(t1);
    t1 = setTimeout(() => { Object.assign(S.cmp, { q: e.target.value.trim(), focus: null, limit: PAGE_PAIRS }); syncHash(); renderCompare(); }, 150);
  });
  $("cmpSort").addEventListener("change", (e) => { Object.assign(S.cmp, { sort: e.target.value, limit: PAGE_PAIRS }); syncHash(); renderCompare(); });
  $("cmpMore").addEventListener("click", () => { S.cmp.limit += PAGE_PAIRS; renderCompare(); });

  // products
  let t2;
  $("prdQ").addEventListener("input", (e) => {
    clearTimeout(t2);
    t2 = setTimeout(() => { Object.assign(S.prd, { q: e.target.value.trim(), limit: PAGE_PRODUCTS }); syncHash(); renderProducts(); }, 150);
  });
  const prdSet = (patch) => { Object.assign(S.prd, patch, { limit: PAGE_PRODUCTS }); syncHash(); renderProducts(); };
  $("prdG").addEventListener("change", (e) => prdSet({ g: e.target.value }));
  $("prdPrice").addEventListener("change", (e) => prdSet({ price: e.target.value }));
  $("prdSort").addEventListener("change", (e) => prdSet({ sort: e.target.value }));
  $("prdPromo").addEventListener("change", (e) => prdSet({ promo: e.target.checked }));
  $("prdBoth").addEventListener("change", (e) => prdSet({ both: e.target.checked }));
  $("prdMore").addEventListener("click", () => { S.prd.limit += PAGE_PRODUCTS; renderProducts(); });

  // promotions
  $("kmG").addEventListener("change", (e) => { Object.assign(S.km, { g: e.target.value, limit: PAGE_PRODUCTS }); syncHash(); renderPromos(); });
  $("kmMore").addEventListener("click", () => { S.km.limit += PAGE_PRODUCTS; renderPromos(); });

  $("cartBtn").addEventListener("click", openCart);
  $("drawerClose").addEventListener("click", closeCart);
  $("overlay").addEventListener("click", closeCart);
  $("modal").addEventListener("click", (e) => { if (e.target === $("modal")) closeModal(); });
  $("toTop").addEventListener("click", () => window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" }));

  document.addEventListener("click", async (e) => {
    const el = (sel) => e.target.closest(sel);
    let b;
    if ((b = el("[data-fav]"))) {
      const i = +b.dataset.fav, u = PRODUCTS[i].u;
      favs.has(u) ? favs.delete(u) : favs.add(u);
      saveFavs(); refreshFavButtons(i);
      toast(favs.has(u) ? `${svg(I.heart)}Đã thêm vào yêu thích <button type="button" data-goto="#/yeu-thich">Xem</button>` : "Đã bỏ khỏi yêu thích");
      if (S.page === "yeu-thich" && !favs.has(u) && !b.hasAttribute("data-fav-text")) renderFavs();
      return;
    }
    if ((b = el("[data-cart]"))) {
      const i = +b.dataset.cart;
      const adding = !(cart[i] > 0);
      cart[i] = adding ? 1 : 0;
      saveCart(adding);
      refreshCartButtons();
      if (adding) toast(`${svg(I.check)}Đã thêm “${esc(PRODUCTS[PAIRS[i].b].n.slice(0, 38))}${PRODUCTS[PAIRS[i].b].n.length > 38 ? "…" : ""}” <button type="button" data-open-cart>Xem giỏ</button>`);
      return;
    }
    if ((b = el("[data-qv]"))) { e.preventDefault(); openQuickView(+b.dataset.qv); return; }
    if (el("[data-close-modal]")) { closeModal(); return; }
    if (el("[data-open-cart]")) { $("toast").hidden = true; openCart(); return; }
    if ((b = el("[data-goto]"))) { $("toast").hidden = true; location.hash = b.dataset.goto; return; }
    if ((b = el("[data-quick]"))) { go("so-sanh", { q: b.dataset.quick }); return; }
    if ((b = el("[data-compare]"))) { go("so-sanh", { focus: +b.dataset.compare }); return; }
    if ((b = el("[data-goto-products]"))) { go("san-pham", { q: b.dataset.gotoProducts }); return; }
    if ((b = el("[data-cmpg]"))) { Object.assign(S.cmp, { g: b.dataset.cmpg, focus: null, limit: PAGE_PAIRS }); fillCmpControls(); syncHash(); renderCompare(); return; }
    if ((b = el("[data-cheap]"))) { Object.assign(S.cmp, { cheap: b.dataset.cheap, focus: null, limit: PAGE_PAIRS }); fillCmpControls(); syncHash(); renderCompare(); return; }
    if ((b = el("[data-store]"))) { Object.assign(S.prd, { store: b.dataset.store, limit: PAGE_PRODUCTS }); fillPrdControls(); syncHash(); renderProducts(); return; }
    if ((b = el("[data-km]"))) { Object.assign(S.km, { type: b.dataset.km, limit: PAGE_PRODUCTS }); fillKmControls(); syncHash(); renderPromos(); return; }
    if ((b = el("[data-kmstore]"))) { Object.assign(S.km, { store: b.dataset.kmstore, limit: PAGE_PRODUCTS }); fillKmControls(); syncHash(); renderPromos(); return; }
    if ((b = el("[data-unfilter]"))) {
      const k = b.dataset.unfilter;
      const reset = { q: { q: "" }, g: { g: "" }, price: { price: "" }, store: { store: "" }, promo: { promo: false }, both: { both: false }, all: DEFAULTS.prd }[k];
      Object.assign(S.prd, reset, { limit: PAGE_PRODUCTS }); fillPrdControls(); syncHash(); renderProducts();
      return;
    }
    if ((b = el("[data-scroll]"))) { const r = $(b.dataset.scroll); r.scrollBy({ left: +b.dataset.dir * r.clientWidth * 0.9 }); return; }
    if (el("[data-faq]")) { e.preventDefault(); location.hash = "#/gioi-thieu"; setTimeout(() => $("faq").scrollIntoView({ behavior: "smooth", block: "start" }), 80); return; }
    if ((b = el("[data-qty]"))) {
      const i = +b.dataset.qty;
      cart[i] = Math.max(0, (cart[i] || 0) + +b.dataset.d);
      saveCart(false); renderCart(); refreshCartButtons();
      return;
    }
    if (el("#clearCart")) { cart = {}; saveCart(false); renderCart(); refreshCartButtons(); return; }
    if (el("#copyList")) { toast((await copyText(shoppingList())) ? `${svg(I.check)}Đã sao chép — dán vào Zalo, Messenger hoặc ghi chú.` : "Không sao chép được trên trình duyệt này."); return; }
    if (el("#shareCart")) { toast((await copyText(shareLink())) ? `${svg(I.check)}Đã sao chép link giỏ hàng — gửi cho người nhà để mở cùng giỏ.` : "Không sao chép được link."); return; }
    if (el("#downloadList")) {
      const blob = new Blob(["﻿" + shoppingList()], { type: "text/plain;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "danh-sach-di-cho.txt"; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      return;
    }
    if (el("[data-close]")) closeCart();
  });

  $("themeBtn").addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    storage("sogia-theme", root.dataset.theme);
  });
}

/* ================================================================ start */
(async function start() {
  const theme = storage("sogia-theme");
  if (theme) document.documentElement.dataset.theme = theme;
  try {
    const get = (f) => fetch("data/" + f).then((r) => { if (!r.ok) throw new Error(f); return r.json(); });
    [META, PAIRS, PRODUCTS] = await Promise.all([get("meta.json"), get("pairs.json"), get("products.json")]);
  } catch (e) {
    $("loading").innerHTML = `<div class="empty">${svg(I.info)}<h3>Không tải được dữ liệu</h3>Nếu bạn mở file trực tiếp trên máy, hãy chạy qua một web server (xem README).</div>`;
    return;
  }
  PRODUCTS.forEach((p, i) => { p.i = i; p.nw = wordsOf(p.n); p.key = wordsOf([p.n, p.br, p.c].filter(Boolean).join(" ")); });
  PAIRS.forEach((x) => { x.key = wordsOf([PRODUCTS[x.b].n, PRODUCTS[x.w].n, PRODUCTS[x.b].br].filter(Boolean).join(" ")); });
  try {
    const saved = JSON.parse(storage("sogia-cart") || "{}");
    for (const [k, v] of Object.entries(saved)) if (PAIRS[+k] && v > 0) cart[k] = v;
  } catch (e) { cart = {}; }
  try { favs = new Set(JSON.parse(storage("sogia-favs") || "[]")); } catch (e) { favs = new Set(); }

  const groupOpts = `<option value="">Tất cả nhóm</option>` + Object.entries(META.groups).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");
  $("prdG").innerHTML = groupOpts;
  $("kmG").innerHTML = groupOpts;

  saveCart(false);
  saveFavs();
  renderHome();
  renderAbout();
  renderStats();
  bind();
  rotateWord();
  $("loading").hidden = true;
  onRoute();
  onScroll();
})();

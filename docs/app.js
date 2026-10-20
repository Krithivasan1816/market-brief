"use strict";
const view = document.getElementById("view");
const updatedEl = document.getElementById("updated");
const cache = {};

function el(tag, props, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === "class") n.className = v;
    else if (k === "href") { if (/^https?:\/\//.test(v)) { n.href = v; n.target = "_blank"; n.rel = "noopener noreferrer"; } }
    else n.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) n.append(k);
  return n;
}

async function load(path) {
  if (cache[path]) return cache[path];
  const r = await fetch(path, { cache: "no-cache" });
  if (!r.ok) throw new Error(path + " " + r.status);
  return (cache[path] = await r.json());
}

function ago(iso) {
  const m = Math.round((Date.now() - new Date(iso)) / 60000);
  if (m < 60) return Math.max(m, 1) + "m ago";
  if (m < 1440) return Math.round(m / 60) + "h ago";
  return Math.round(m / 1440) + "d ago";
}

function newsItem(n) {
  return el("a", { class: "card item", href: n.link },
    el("div", { class: "t" }, n.title),
    el("div", { class: "s" }, n.source + " · " + ago(n.published)),
    n.snippet ? el("div", { class: "sn" }, n.snippet) : null);
}

function renderNews(d) {
  updatedEl.textContent = "Brief for " + d.date + " · updated " + ago(d.updated);
  const out = [];
  if (d.quotes && d.quotes.length) {
    out.push(el("div", { class: "tiles" }, d.quotes.map(q => {
      const c = q.change_pct;
      return el("div", { class: "tile" },
        el("div", { class: "n" }, q.name),
        el("div", { class: "p" }, q.price.toLocaleString()),
        c == null ? null : el("div", { class: c >= 0 ? "up" : "down" }, (c >= 0 ? "+" : "") + c + "%"));
    })));
    out.push(el("div", { class: "muted" }, "Change vs previous close. Quotes may be delayed."));
  }
  if (d.summary) out.push(el("h2", {}, "AI summary"), el("div", { class: "card summary" }, d.summary));
  out.push(el("h2", {}, "India"), d.india.map(newsItem));
  out.push(el("h2", {}, "USA"), d.usa.map(newsItem));
  out.push(disclaimer());
  view.replaceChildren(...out.flat());
}

function disclaimer() {
  return el("p", { class: "disclaimer" }, "Educational only, not financial advice. Headlines come from public RSS feeds; tap to read at the source. Returns shown are historical ranges, never promises.");
}

async function today() {
  renderNews(await load("data/news.json"));
}

async function invest() {
  const d = await load("data/invest.json");
  let region = "india", risk = "all";
  const box = el("div");
  function draw() {
    const chips = el("div", { class: "chips" },
      [["india", "India"], ["usa", "USA"]].map(([v, l]) =>
        el("button", { class: region === v ? "on" : "", "data-r": v }, l)),
      ["all", "low", "medium", "high"].map(v =>
        el("button", { class: risk === v ? "on" : "", "data-k": v }, v === "all" ? "Any risk" : v + " risk")));
    chips.addEventListener("click", e => {
      if (e.target.dataset.r) region = e.target.dataset.r;
      if (e.target.dataset.k) risk = e.target.dataset.k;
      draw();
    });
    const list = d.options.filter(o => o.region === region && (risk === "all" || o.risk.startsWith(risk)));
    const cards = list.map(o => el("div", { class: "card" },
      el("h3", {}, o.name),
      el("span", { class: "badge risk-" + o.risk.split("-")[0] }, o.risk + " risk"),
      el("div", { class: "muted", style: "margin-top:6px" }, o.note),
      el("dl", {},
        ["Returns", o.returns, "Lock-in", o.lockin, "Liquidity", o.liquidity, "Minimum", o.min, "Tax", o.tax, "Where", o.where]
          .reduce((a, v, i, arr) => (i % 2 ? a : [...a, el("dt", {}, v), el("dd", {}, arr[i + 1])]), [])),
      el("p", {}, el("a", { class: "link", href: o.link }, "Learn more ↗"))));
    box.replaceChildren(
      el("h2", {}, "Where to start (in order)"),
      el("div", { class: "card" }, el("ol", { class: "steps" }, d.order[region].map(s => el("li", {}, s)))),
      el("h2", {}, "Options"), chips,
      ...(cards.length ? cards : [el("p", { class: "muted" }, "None match this filter.")]),
      disclaimer());
  }
  draw();
  view.replaceChildren(box);
}

async function learn() {
  const d = await load("data/invest.json");
  view.replaceChildren(...[
    el("h2", {}, "Free study resources"),
    d.learn.map(r => el("a", { class: "card item", href: r.link },
      el("div", { class: "t" }, r.title), el("div", { class: "sn" }, r.desc))),
    el("h2", {}, "Glossary"),
    d.glossary.map(g => el("div", { class: "card" }, el("h3", {}, g.term), el("div", { class: "muted" }, g.def))),
    disclaimer()].flat());
}

async function archive() {
  const dates = await load("data/archive_index.json");
  const sel = el("select", {}, dates.map(x => el("option", { value: x }, x)));
  const body = el("div");
  async function show() {
    try { renderInto(await load("data/archive/" + sel.value + ".json")); }
    catch (e) { body.replaceChildren(el("p", { class: "muted" }, "Not available offline.")); }
  }
  function renderInto(d) {
    body.replaceChildren(el("h2", {}, "India"), ...d.india.map(newsItem), el("h2", {}, "USA"), ...d.usa.map(newsItem));
  }
  sel.addEventListener("change", show);
  view.replaceChildren(el("h2", {}, "Past briefs (30 days)"), sel, body);
  if (dates.length) show();
}

const tabs = { today, invest, learn, archive };
async function go(name) {
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  try { await tabs[name](); window.scrollTo(0, 0); }
  catch (e) { view.replaceChildren(el("p", { class: "card" }, "Could not load data. Check connection and retry.")); }
  if (name !== "today") updatedEl.textContent = "";
  try { localStorage.setItem("tab", name); } catch (e) { /* private mode */ }
}
document.getElementById("tabs").addEventListener("click", e => { if (e.target.dataset.tab) go(e.target.dataset.tab); });

let start = "today";
try { start = localStorage.getItem("tab") || "today"; } catch (e) { /* ignore */ }
go(tabs[start] ? start : "today");

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});

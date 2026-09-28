/*
OWNER: Frontend, API & Demo role — Amogh R B (covering for Abhishek Chugh)
LANGUAGE: vanilla JavaScript (ES2020+), no framework, no npm, no bundler.
          Chart.js 4 is available as the global `Chart` (web/vendor/).

──────────────────────────────── AI PROMPT ────────────────────────────────
Paste this comment + AGENTS.md + docs/interfaces.md + web/index.html into
your AI, then say: "Implement web/app.js exactly as described. Only edit this file."

DATA
  api(path, opts) → fetch(path).then(r => r.json()). If the fetch FAILS
  (backend not running), fall back to sample.json:
    sample.json = { "status": {...}, "people": [...],
                    "timelines": {"<id>": Timeline}, "summaries": {"<id>": DoctorSummary} }
  so the whole UI works with no backend. Show a small "demo data" badge then.

FLOW
  1. On load: GET /api/status → set #llm-status. GET /api/people → render
     #people buttons; select the first person.
  2. Select person → GET /api/timeline/{id} →
     - fill #test-picker from timeline.series (group <optgroup> by category if
       present; default to the test of the first flag, else the first series)
     - draw the chart for the selected series
     - render flags + caveats
  3. Chart (Chart.js line chart, one series at a time):
     - x = point.date (use a category axis with the dates as labels; no date
       adapter needed), y = point.value, y-axis title = unit
     - shade the normal range: two extra datasets for normal[0] and normal[1]
       with fill between them (light green, no points); skip a bound if null
     - point colour: green inside the range, amber within 10% of a limit,
       red outside; tooltip shows value + unit + point.source
  4. Flag cards: coloured left border by level (red/amber/green), title,
     detail, "Ask your doctor: …" in bold, and the sources as small chips.
     Clicking a card switches the chart to that flag's test if it has one.
  5. Upload: drag-drop or file picker → POST /api/upload as FormData with
     field "files" (append each file) → show each UploadResult.message
     (green if ok, red if not) → refresh people + timeline.
  6. Summary button → GET /api/summary/{id} → fill <dialog id="summary">:
     intro paragraph, medicines, top trends, questions, caveats, generated date.

RULES
  - Escape any text you put into innerHTML (write a small esc() helper), or use
    textContent. Report text comes from PDFs and must not run as HTML.
  - No external requests: only /api/* and sample.json.
  - Keep it in one file, organised as small functions.

DONE WHEN
  With the backend OFF: `cd web && python -m http.server 8000` shows the
  chart, flags and summary from sample.json. With the backend ON (./run.sh):
  uploading a sample PDF adds it and the chart updates.
────────────────────────────────────────────────────────────────────────────
*/

"use strict";

const $ = (sel) => document.querySelector(sel);
const state = { demo: false, sample: null, people: [], personId: null, timeline: null, chart: null };

// ── data ────────────────────────────────────────────────────────────────────

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function loadSample() {
  if (!state.sample) state.sample = await fetch("sample.json").then((r) => r.json());
  return state.sample;
}

// Same answers as the API, read from sample.json (backend off).
async function fromSample(path) {
  const d = await loadSample();
  const id = path.split("/").pop();
  if (path === "/api/status") return d.status;
  if (path === "/api/people") return d.people;
  if (path.startsWith("/api/timeline/")) return d.timelines[id] ?? null;
  if (path.startsWith("/api/summary/")) return d.summaries[id] ?? null;
  return null;
}

async function api(path, opts) {
  if (state.demo) return fromSample(path);
  const r = await fetch(path.slice(1), opts);   // relative: works behind any prefix
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

// ── header ──────────────────────────────────────────────────────────────────

async function initStatus() {
  let st;
  try {
    const r = await fetch("api/status");
    st = r.ok ? await r.json() : null;
  } catch { st = null; }
  if (!st || st.ok !== true) {           // no backend (e.g. python -m http.server)
    state.demo = true;
    st = await fromSample("/api/status");
  }
  $("#demo-badge").hidden = !state.demo;
  const pill = $("#llm-status");
  pill.textContent = st.llm ? `Local AI on (${st.model})` : "Local AI off (rules mode)";
  pill.classList.toggle("on", !!st.llm);
}

// ── people ──────────────────────────────────────────────────────────────────

async function loadPeople() {
  state.people = (await api("/api/people")) ?? [];
  const box = $("#people");
  if (!state.people.length) {
    box.innerHTML = `<p class="empty">No one yet. Add a report to start.</p>`;
    return;
  }
  box.innerHTML = state.people.map((p) =>
    `<button type="button" class="btn" data-id="${p.id}" aria-pressed="false">` +
    `${esc(p.name)} <span class="count">· ${p.reports} report${p.reports === 1 ? "" : "s"}</span></button>`
  ).join("");
  const keep = state.people.some((p) => p.id === state.personId);
  await selectPerson(keep ? state.personId : state.people[0].id);
}

async function selectPerson(id) {
  state.personId = id;
  for (const b of document.querySelectorAll("#people .btn")) {
    b.setAttribute("aria-pressed", String(Number(b.dataset.id) === id));
  }
  state.timeline = await api(`/api/timeline/${id}`);
  renderTimeline();
}

// ── timeline ────────────────────────────────────────────────────────────────

// Flags carry no test_id, so find the series a flag talks about by name.
function flagTest(flag) {
  const text = `${flag.title} ${flag.detail}`.toLowerCase();
  const series = state.timeline?.series ?? [];
  const hit = series.find((s) => text.includes(s.test.toLowerCase()) || text.includes(s.test_id));
  return hit ? hit.test_id : null;
}

function renderTimeline() {
  const t = state.timeline;
  const series = t?.series ?? [];
  const picker = $("#test-picker");

  const byCat = new Map();
  for (const s of series) {
    const cat = s.category || "";
    if (!byCat.has(cat)) byCat.set(cat, []);
    byCat.get(cat).push(s);
  }
  const opt = (s) => `<option value="${esc(s.test_id)}">${esc(s.test)} (${esc(s.unit)})</option>`;
  picker.innerHTML = [...byCat].map(([cat, list]) =>
    cat ? `<optgroup label="${esc(cat)}">${list.map(opt).join("")}</optgroup>` : list.map(opt).join("")
  ).join("");
  picker.disabled = !series.length;

  const first = (t?.flags ?? []).map(flagTest).find(Boolean);
  if (series.length) picker.value = first ?? series[0].test_id;
  drawChart(picker.value);
  renderFlags();
}

function pointColour(v, [lo, hi]) {
  const css = getComputedStyle(document.documentElement);
  const c = (name) => css.getPropertyValue(name).trim();
  if ((lo != null && v < lo) || (hi != null && v > hi)) return c("--red");
  const near = (lim) => lim != null && Math.abs(v - lim) <= Math.abs(lim) * 0.1;
  return near(lo) || near(hi) ? c("--amber") : c("--green");
}

function drawChart(testId) {
  const s = (state.timeline?.series ?? []).find((x) => x.test_id === testId);
  $("#chart-empty").hidden = !!s;
  $(".chart-box").hidden = !s;
  if (state.chart) { state.chart.destroy(); state.chart = null; }
  if (!s || typeof Chart === "undefined") return;

  const labels = s.points.map((p) => p.date);
  const [lo, hi] = s.normal;
  const band = "rgba(6, 118, 71, 0.10)";
  const flat = (v) => labels.map(() => v);
  const datasets = [];
  if (lo != null) datasets.push({ label: "Normal low", data: flat(lo), fill: hi != null ? false : "end" });
  if (hi != null) datasets.push({ label: "Normal high", data: flat(hi), fill: lo != null ? "-1" : "start" });
  for (const d of datasets) Object.assign(d, { borderWidth: 0, pointRadius: 0, backgroundColor: band, band: true });

  const colours = s.points.map((p) => pointColour(p.value, s.normal));
  const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
  datasets.push({
    label: s.test, data: s.points.map((p) => p.value),
    borderColor: accent, borderWidth: 2, tension: 0.2,
    pointBackgroundColor: colours, pointBorderColor: colours, pointRadius: 5, pointHoverRadius: 7,
  });

  const muted = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
  state.chart = new Chart($("#chart"), {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "nearest", intersect: true },
      plugins: {
        legend: { display: false },
        tooltip: {
          filter: (item) => !item.dataset.band,
          callbacks: {
            label: (item) => `${item.parsed.y} ${s.unit}`,
            afterLabel: (item) => s.points[item.dataIndex].source,
          },
        },
      },
      scales: {
        x: { ticks: { color: muted } },
        y: {
          title: { display: true, text: s.unit, color: muted }, ticks: { color: muted },
          // Open-ended range: leave room so the shaded normal band is visible.
          suggestedMin: lo == null && hi != null ? hi * 0.8 : undefined,
          suggestedMax: hi == null && lo != null ? lo * 1.2 : undefined,
        },
      },
    },
  });
}

// ── flags ───────────────────────────────────────────────────────────────────

function renderFlags() {
  const flags = state.timeline?.flags ?? [];
  const caveats = state.timeline?.caveats ?? [];
  $("#flags").innerHTML = flags.length ? flags.map((f, i) => {
    const test = flagTest(f);
    return `<article class="flag ${esc(f.level)}" data-i="${i}"${test ? ` data-test="${esc(test)}" tabindex="0"` : ""}>
      <h3>${esc(f.title)}</h3>
      <p>${esc(f.detail)}</p>
      <p class="ask">Ask your doctor: ${esc(f.ask_doctor)}</p>
      <div class="chips">${(f.sources ?? []).map((src) => `<span class="chip">${esc(src)}</span>`).join("")}</div>
    </article>`;
  }).join("") : `<p class="empty">Nothing flagged for ${esc(state.timeline?.person ?? "this person")}.</p>`;
  $("#caveats").innerHTML = caveats.map((c) => `<li>${esc(c)}</li>`).join("");
}

function showFlagTest(card) {
  if (!card?.dataset.test) return;
  $("#test-picker").value = card.dataset.test;
  drawChart(card.dataset.test);
  $(".chart-box").scrollIntoView({ behavior: "smooth", block: "center" });
}

// ── upload ──────────────────────────────────────────────────────────────────

function showResults(items) {
  $("#upload-results").innerHTML = items.map((r) =>
    `<li class="${r.ok ? "ok" : "err"}">${esc(r.filename)}: ${esc(r.message)}</li>`).join("");
}

async function upload(files) {
  const pdfs = [...files];
  if (!pdfs.length) return;
  if (state.demo) {
    showResults([{ filename: "Demo mode", ok: false, message: "the app isn't running. Start it with ./run.sh to add reports." }]);
    return;
  }
  const form = new FormData();
  for (const f of pdfs) form.append("files", f);
  showResults(pdfs.map((f) => ({ filename: f.name, ok: true, message: "reading…" })));
  try {
    showResults((await api("/api/upload", { method: "POST", body: form })) ?? []);
  } catch (e) {
    showResults([{ filename: "Upload", ok: false, message: e.message }]);
  }
  await loadPeople();
}

function initUpload() {
  const drop = $("#drop");
  const input = $("#file-input");
  input.addEventListener("change", () => { upload(input.files); input.value = ""; });
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  for (const ev of ["dragenter", "dragover"]) {
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("dragover"); });
  }
  for (const ev of ["dragleave", "drop"]) {
    drop.addEventListener(ev, () => drop.classList.remove("dragover"));
  }
  drop.addEventListener("drop", (e) => { e.preventDefault(); upload(e.dataTransfer.files); });
}

// ── doctor summary ──────────────────────────────────────────────────────────

function list(items, empty = "None recorded.") {
  return items?.length ? `<ul>${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p class="empty">${empty}</p>`;
}

async function openSummary() {
  if (state.personId == null) return;
  const s = await api(`/api/summary/${state.personId}`);
  const body = $("#summary-body");
  if (!s) {
    body.innerHTML = `<p class="empty">No summary yet. Add some reports first.</p>`;
  } else {
    body.innerHTML = `
      <p class="meta"><strong>${esc(s.person)}</strong> · generated ${esc(s.generated)}</p>
      <p>${esc(s.intro)}</p>
      <h3>Medicines</h3>${list(s.medicines)}
      <h3>Trends to discuss</h3>${list((s.top_trends ?? []).map((f) => `${f.title}: ${f.detail}`), "Nothing stands out.")}
      <h3>Questions for the doctor</h3>${list(s.questions)}
      ${s.caveats?.length ? `<h3>Data notes</h3>${list(s.caveats)}` : ""}`;
  }
  $("#summary").showModal();
}

// ── start ───────────────────────────────────────────────────────────────────

function wire() {
  $("#people").addEventListener("click", (e) => {
    const b = e.target.closest(".btn[data-id]");
    if (b) selectPerson(Number(b.dataset.id));
  });
  $("#test-picker").addEventListener("change", (e) => drawChart(e.target.value));
  $("#flags").addEventListener("click", (e) => showFlagTest(e.target.closest(".flag")));
  $("#flags").addEventListener("keydown", (e) => { if (e.key === "Enter") showFlagTest(e.target.closest(".flag")); });
  $("#summary-btn").addEventListener("click", openSummary);
  $("#print-btn").addEventListener("click", () => window.print());
  $("#close-btn").addEventListener("click", () => $("#summary").close());
  initUpload();
}

async function main() {
  wire();
  await initStatus();
  await loadPeople();
}

main().catch((e) => {
  console.error(e);
  $("#flags").innerHTML = `<p class="empty">Something went wrong: ${esc(e.message)}</p>`;
});

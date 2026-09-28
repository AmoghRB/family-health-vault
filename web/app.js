// OWNER: Abhishek Chugh (contract alignment: Pankaj Kumar B S)
// Reads the shapes in src/contracts.py / docs/interfaces.md.
// If the API is unreachable it falls back to web/sample.json (same shapes).

const state = { mode: "api", people: [], personId: null, sample: null, charts: [] };
const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const icon = (name) => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const LEVELS = {
  red: { label: "Needs attention", icon: "alert" },
  amber: { label: "Worth watching", icon: "flag" },
  green: { label: "For information", icon: "info" },
};
const SPLASH_MIN_MS = 1200;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  const started = Date.now();
  wireTabs();
  wireUpload();
  $("print-btn").addEventListener("click", () => window.print());
  await loadPeople();
  await loadStatus();
  const first = state.personId != null ? loadPerson(state.personId) : (renderEmpty(), null);
  await first; // resolves once flags + timeline are drawn; the summary keeps loading on its own
  setTimeout(hideSplash, Math.max(0, SPLASH_MIN_MS - (Date.now() - started)));
}

function hideSplash() {
  const splash = $("splash");
  splash.classList.add("hide");
  splash.setAttribute("aria-hidden", "true");
  setTimeout(() => splash.remove(), 600);
}

/* ---------- tabs ---------- */

function wireTabs() {
  const tabs = [...document.querySelectorAll(".tab")];
  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => selectTab(tab.dataset.panel));
    tab.addEventListener("keydown", (e) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (!step) return;
      const next = tabs[(i + step + tabs.length) % tabs.length];
      selectTab(next.dataset.panel);
      next.focus();
    });
  });
}

function selectTab(name) {
  document.querySelectorAll(".tab").forEach((t) => {
    const on = t.dataset.panel === name;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
  });
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${name}`));
  // Charts drawn while their panel was hidden need a resize once visible.
  if (name === "timeline") state.charts.forEach((c) => c.resize());
}

/* ---------- data ---------- */

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} returned ${res.status}`);
  return res.json();
}

async function loadPeople(keepId) {
  try {
    state.people = await api("/api/people");
    state.mode = "api";
  } catch (err) {
    state.sample = await (await fetch("sample.json")).json();
    state.people = state.sample.people;
    state.mode = "demo";
  }
  const ids = state.people.map((p) => p.id);
  state.personId = ids.includes(keepId) ? keepId : (ids[0] ?? null);
  renderPeople();
}

const initials = (name) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");

function renderPeople() {
  const box = $("person-chips");
  if (!state.people.length) {
    box.innerHTML = '<p class="section-lead">No one yet. Family members appear here once you upload their reports.</p>';
    return;
  }
  box.innerHTML = state.people
    .map(
      (p) => `
      <button class="person-chip" role="radio" data-id="${p.id}" aria-checked="${p.id === state.personId}">
        <span class="avatar" aria-hidden="true">${esc(initials(p.name))}</span>
        <span class="name">${esc(p.name)}<span class="meta">${p.reports} report${p.reports === 1 ? "" : "s"}</span></span>
      </button>`
    )
    .join("");
  box.querySelectorAll(".person-chip").forEach((chip) =>
    chip.addEventListener("click", () => loadPerson(Number(chip.dataset.id)))
  );
}

async function loadStatus() {
  const pill = $("status-pill");
  let text, cls = "";
  if (state.mode === "demo") {
    text = "Demo data · backend not running";
    cls = "warn";
  } else {
    try {
      const s = await api("/api/status");
      text = s.llm ? `Private · on-device AI (${s.model})` : "Private · rules reader (local AI off)";
      if (!s.llm) cls = "warn";
    } catch (err) {
      text = "Can't reach the vault";
      cls = "error";
    }
  }
  $("status-text").textContent = text;
  pill.className = `status-pill ${cls}`;
}

async function loadPerson(id) {
  state.personId = id;
  document.querySelectorAll(".person-chip").forEach((c) =>
    c.setAttribute("aria-checked", String(Number(c.dataset.id) === id))
  );
  let timeline;
  try {
    timeline = state.mode === "api" ? await api(`/api/timeline/${id}`) : state.sample.timelines[id];
  } catch (err) {
    console.error(err);
    $("timeline-content").innerHTML = emptyHtml("Couldn't load this person's data", esc(err.message));
    return;
  }
  renderGlance(timeline);
  renderTimeline(timeline);
  renderFlags(timeline.flags);
  loadSummary(id); // slower: the on-device model writes the intro, so don't block the rest on it
}

async function loadSummary(id) {
  const box = $("summary-content");
  box.innerHTML = `<div class="writing"><span class="spinner" aria-hidden="true"></span>Writing the summary with the on-device AI…</div>`;
  try {
    const summary = state.mode === "api" ? await api(`/api/summary/${id}`) : state.sample.summaries[id];
    if (state.personId === id) renderSummary(summary); // ignore if the user switched person meanwhile
  } catch (err) {
    box.innerHTML = emptyHtml("Couldn't write the summary", esc(err.message));
  }
}

/* ---------- empty states ---------- */

const emptyHtml = (title, text, action = "") =>
  `<div class="empty"><strong>${title}</strong>${text}${action}</div>`;

const uploadAction = '<br><button class="btn btn-primary" data-go="upload">' + icon("upload") + "Upload a report</button>";

function wireEmptyActions(root) {
  root.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => selectTab(b.dataset.go)));
}

function renderEmpty() {
  $("glance").innerHTML = "";
  $("flag-count").hidden = true;
  const html = emptyHtml("Your vault is empty", "Upload a lab report or prescription to start a timeline.", uploadAction);
  ["timeline-content", "flags-content", "summary-content"].forEach((id) => {
    $(id).innerHTML = html;
    wireEmptyActions($(id));
  });
}

/* ---------- at a glance ---------- */

function renderGlance(t) {
  const person = state.people.find((p) => p.id === state.personId);
  const attention = t.flags.filter((f) => f.level === "red" || f.level === "amber").length;
  $("glance").innerHTML = `
    <div class="stat"><p class="stat-value">${person ? person.reports : "–"}</p><p class="stat-label">reports in the vault</p></div>
    <div class="stat"><p class="stat-value">${t.series.length}</p><p class="stat-label">tests tracked over time</p></div>
    <div class="stat ${attention ? "alert" : "calm"}"><p class="stat-value">${attention || "All clear"}</p>
      <p class="stat-label">${attention ? `thing${attention === 1 ? "" : "s"} to ask the doctor` : "nothing flagged right now"}</p></div>`;
  const badge = $("flag-count");
  badge.hidden = !attention;
  badge.textContent = attention;
  badge.setAttribute("aria-label", `${attention} flagged`);
}

/* ---------- helpers ---------- */

const outOfRange = (v, [lo, hi]) => (lo != null && v < lo) || (hi != null && v > hi);
const rangeText = ([lo, hi], unit) =>
  lo == null ? `below ${hi} ${unit}` : hi == null ? `above ${lo} ${unit}` : `${lo}–${hi} ${unit}`;
const formatDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
const caveatHtml = (c) => `<div class="caveat">${icon("alert")}<span>${esc(c)}</span></div>`;
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/* ---------- flags ---------- */

function flagHtml(f, withCard = true) {
  const lvl = LEVELS[f.level] || LEVELS.green;
  const n = f.sources.length;
  return `
    <div class="${withCard ? "card " : ""}flag ${esc(f.level)}">
      <span class="flag-icon">${icon(lvl.icon)}</span>
      <span class="level">${lvl.label}</span>
      <p class="flag-title">${esc(f.title)}</p>
      <p class="flag-detail">${esc(f.detail)}</p>
      <p class="ask"><strong>Ask your doctor:</strong> ${esc(f.ask_doctor)}</p>
      ${n ? `<details class="sources"><summary>Based on ${n} report${n === 1 ? "" : "s"}</summary>
        <div class="chips">${f.sources.map((s) => `<span class="chip">${esc(s)}</span>`).join("")}</div></details>` : ""}
    </div>`;
}

function renderFlags(flags) {
  $("flags-content").innerHTML = flags.length
    ? flags.map((f) => flagHtml(f)).join("")
    : emptyHtml("Nothing flagged", "No trends or cross-report patterns need attention for this person right now.");
}

/* ---------- timeline ---------- */

function trend(points) {
  if (points.length < 2) return null;
  const first = points[0].value, last = points[points.length - 1].value;
  const change = (last - first) / Math.abs(first || 1);
  if (Math.abs(change) < 0.03) return { icon: "flat", text: "steady" };
  return change > 0 ? { icon: "up", text: "rising" } : { icon: "down", text: "falling" };
}

function renderTimeline(t) {
  const box = $("timeline-content");
  state.charts.forEach((c) => c.destroy());
  state.charts = [];
  const caveats = t.caveats.length ? `<div class="caveats">${t.caveats.map(caveatHtml).join("")}</div>` : "";
  if (!t.series.length) {
    box.innerHTML = caveats + emptyHtml("No values yet", "Upload a lab report to see this person's timeline.", uploadAction);
    wireEmptyActions(box);
    return;
  }
  box.innerHTML = caveats;
  t.series.forEach((s, i) => {
    const last = s.points[s.points.length - 1];
    const out = outOfRange(last.value, s.normal);
    const [lo] = s.normal;
    const status = out ? (lo != null && last.value < lo ? "Below range" : "Above range") : "In range";
    const tr = trend(s.points);
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="series-head">
        <div><h3>${esc(s.test)}</h3><p class="range">Normal: ${esc(rangeText(s.normal, s.unit))}</p></div>
        <div class="latest">
          <p class="latest-value">${last.value} <small>${esc(s.unit)}</small></p>
          <span class="pill ${out ? "out" : ""}">${status}${tr ? ` · ${icon(tr.icon)}${tr.text}` : ""}</span>
        </div>
      </div>
      <div class="chart-wrap"><canvas id="chart-${i}" role="img" aria-label="${esc(s.test)} over time, latest ${last.value} ${esc(s.unit)}"></canvas></div>
      <details class="readings">
        <summary>Show all ${s.points.length} readings and their sources</summary>
        <table>
          <thead><tr><th>Date</th><th>Value</th><th>Source</th></tr></thead>
          <tbody>${s.points
            .map((p) => {
              const [file, page] = p.source.split("#p");
              return `<tr><td>${formatDate(p.date)}</td><td class="value ${outOfRange(p.value, s.normal) ? "out" : ""}">${p.value} ${esc(s.unit)}</td><td>${esc(file)}${page ? " · page " + esc(page) : ""}</td></tr>`;
            })
            .join("")}</tbody>
        </table>
      </details>`;
    box.appendChild(card);
    drawChart(`chart-${i}`, s);
  });
}

function drawChart(canvasId, s) {
  const [lo, hi] = s.normal;
  const line = cssVar("--chart-line"), warn = cssVar("--critical");
  const band = {
    id: "band",
    beforeDatasetsDraw(chart) {
      const a = chart.chartArea;
      if (!a) return;
      const y = chart.scales.y;
      const top = Math.max(y.getPixelForValue(hi ?? y.max), a.top);
      const bottom = Math.min(y.getPixelForValue(lo ?? y.min), a.bottom);
      const ctx = chart.ctx;
      ctx.save();
      ctx.fillStyle = cssVar("--chart-band");
      ctx.fillRect(a.left, top, a.right - a.left, bottom - top);
      ctx.restore();
    },
  };
  const values = s.points.map((p) => p.value);
  const axis = { ticks: { color: cssVar("--chart-text") }, grid: { color: cssVar("--chart-grid") }, border: { display: false } };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  state.charts.push(
    new Chart($(canvasId).getContext("2d"), {
      type: "line",
      data: {
        labels: s.points.map((p) => formatDate(p.date)),
        datasets: [{
          data: values,
          borderColor: line,
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointBackgroundColor: values.map((v) => (outOfRange(v, s.normal) ? warn : line)),
          pointBorderColor: cssVar("--surface"),
          pointBorderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: reduce ? false : { duration: 500 },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => `${c.parsed.y} ${s.unit}`, afterLabel: (c) => s.points[c.dataIndex].source } },
        },
        scales: { x: axis, y: { ...axis, suggestedMin: lo ?? undefined, suggestedMax: hi ?? undefined } },
      },
      plugins: [band],
    })
  );
}

/* ---------- summary ---------- */

function renderSummary(s) {
  $("summary-content").innerHTML = `
    <h2>${esc(s.person)}: visit summary</h2>
    <p class="meta">Generated ${esc(s.generated)} · from recorded reports only</p>
    <p class="intro">${esc(s.intro)}</p>
    ${s.medicines.length ? `<h3>Medicines on record</h3><div class="meds">${s.medicines.map((m) => `<span class="med">${esc(m)}</span>`).join("")}</div>` : ""}
    ${s.top_trends.length ? `<h3>Top trends</h3>${s.top_trends.map((f) => flagHtml(f, false)).join("")}` : ""}
    ${s.questions.length ? `<h3>Questions to ask the doctor</h3><ol class="questions">${s.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ol>` : ""}
    ${s.caveats.length ? `<h3>Data-quality notes</h3>${s.caveats.map(caveatHtml).join("")}` : ""}
    <p class="disclaimer">This summarizes recorded values and flagged trends only. It is not a diagnosis and gives no dosing advice.</p>`;
}

/* ---------- upload ---------- */

function wireUpload() {
  const zone = $("dropzone");
  const input = $("file-input");
  zone.addEventListener("click", (e) => {
    if (e.target !== input) input.click(); // the input sits inside the zone; ignore its own bubbled click
  });
  zone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      input.click();
    }
  });
  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("drag-over");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    handleUpload([...e.dataTransfer.files]);
  });
  input.addEventListener("change", () => {
    handleUpload([...input.files]);
    input.value = "";
  });
}

async function handleUpload(files) {
  const pdfs = files.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
  const log = $("upload-log");
  log.querySelector(".upload-done")?.remove();
  if (!pdfs.length) {
    log.insertAdjacentHTML("afterbegin", `<div class="upload-row warn"><span class="row-icon">${icon("alert")}</span><span class="msg">Only PDF files can be read.</span></div>`);
    return;
  }
  const rows = pdfs.map((f) => {
    const row = document.createElement("div");
    row.className = "upload-row";
    row.innerHTML = `<span class="row-icon"><span class="spinner" aria-hidden="true"></span></span>
      <span class="file">${esc(f.name)}</span><span class="msg">Reading with the on-device AI…</span>`;
    log.prepend(row);
    return row;
  });
  const setRow = (row, ok, msg) => {
    row.className = `upload-row ${ok ? "ok" : "warn"}`;
    row.querySelector(".row-icon").innerHTML = icon(ok ? "check" : "alert");
    row.querySelector(".msg").textContent = msg;
  };
  if (state.mode === "demo") {
    rows.forEach((r) => setRow(r, false, "Demo mode: start the backend to read files."));
    return;
  }
  try {
    const form = new FormData();
    pdfs.forEach((f) => form.append("files", f));
    const res = await fetch("/api/upload", { method: "POST", body: form });
    if (!res.ok) throw new Error(`upload returned ${res.status}`);
    const results = await res.json();
    results.forEach((r, i) => rows[i] && setRow(rows[i], r.ok, r.message));
    const saved = results.find((r) => r.ok && r.person_id != null);
    await loadPeople(saved ? saved.person_id : state.personId);
    if (state.personId != null) await loadPerson(state.personId);
    const okCount = results.filter((r) => r.ok).length;
    if (okCount) {
      log.insertAdjacentHTML("beforeend", `
        <div class="upload-done"><p>${okCount} report${okCount === 1 ? "" : "s"} added to the vault.</p>
          <button class="btn btn-primary" data-go="flags">See flags ${icon("arrow")}</button></div>`);
      wireEmptyActions(log);
    }
  } catch (err) {
    rows.forEach((r) => setRow(r, false, `Upload failed: ${err.message}`));
  }
}

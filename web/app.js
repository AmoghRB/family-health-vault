// OWNER: Abhishek Chugh (contract alignment: Pankaj Kumar B S)
// Reads the shapes in src/contracts.py / docs/interfaces.md.
// If the API is unreachable it falls back to web/sample.json (same shapes).

const state = { mode: "api", people: [], personId: null, sample: null, charts: [] };
const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const LEVEL_CLASS = { red: "severity-critical", amber: "severity-warning", green: "severity-info" };

document.addEventListener("DOMContentLoaded", init);

async function init() {
  wireTabs();
  wireUpload();
  $("print-btn").addEventListener("click", () => window.print());
  $("person-select").addEventListener("change", (e) => loadPerson(Number(e.target.value)));
  await loadPeople();
  await loadStatus();
  if (state.personId != null) await loadPerson(state.personId);
  else renderEmpty();
}

function wireTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.setAttribute("aria-selected", "false"));
      tab.setAttribute("aria-selected", "true");
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      $(`panel-${tab.dataset.panel}`).classList.add("active");
    });
  });
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
  $("person-select").innerHTML = state.people
    .map((p) => `<option value="${p.id}">${esc(p.name)} (${p.reports} report${p.reports === 1 ? "" : "s"})</option>`)
    .join("");
  if (state.personId != null) $("person-select").value = state.personId;
}

async function loadStatus() {
  let text, color, soft;
  if (state.mode === "demo") {
    text = "Demo data — backend not running";
    color = "--warn";
    soft = "--warn-soft";
  } else {
    try {
      const s = await api("/api/status");
      text = s.llm ? `Running locally · ${s.model}` : "Running locally · LLM off (template summaries)";
      color = s.llm ? "--accent" : "--warn";
      soft = s.llm ? "--accent-soft" : "--warn-soft";
    } catch (err) {
      text = "API error";
      color = "--critical";
      soft = "--critical-soft";
    }
  }
  $("status-text").textContent = text;
  const dot = document.querySelector(".status-dot");
  dot.style.background = `var(${color})`;
  dot.style.boxShadow = `0 0 0 3px var(${soft})`;
}

async function loadPerson(id) {
  state.personId = id;
  let timeline, summary;
  try {
    if (state.mode === "api") {
      [timeline, summary] = await Promise.all([api(`/api/timeline/${id}`), api(`/api/summary/${id}`)]);
    } else {
      timeline = state.sample.timelines[id];
      summary = state.sample.summaries[id];
    }
  } catch (err) {
    console.error(err);
    $("timeline-content").innerHTML = `<div class="empty-state">Could not load data: ${esc(err.message)}</div>`;
    return;
  }
  renderTimeline(timeline);
  renderFlags(timeline.flags);
  renderSummary(summary);
}

function renderEmpty() {
  const msg = '<div class="empty-state">Upload a report to get started.</div>';
  ["timeline-content", "flags-content", "summary-content"].forEach((id) => ($(id).innerHTML = msg));
}

/* ---------- helpers ---------- */

const outOfRange = (v, [lo, hi]) => (lo != null && v < lo) || (hi != null && v > hi);
const rangeText = ([lo, hi], unit) =>
  lo == null ? `up to ${hi} ${unit}` : hi == null ? `${lo} ${unit} or more` : `${lo}–${hi} ${unit}`;
const formatDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
const caveatHtml = (c) => `<div class="caveat">⚠ ${esc(c)}</div>`;

/* ---------- timeline ---------- */

function renderTimeline(t) {
  const box = $("timeline-content");
  state.charts.forEach((c) => c.destroy());
  state.charts = [];
  const caveats = t.caveats.map(caveatHtml).join("");
  if (!t.series.length) {
    box.innerHTML = caveats + '<div class="empty-state">No standardized values yet for this person.</div>';
    return;
  }
  box.innerHTML = caveats;
  t.series.forEach((s, i) => {
    const card = document.createElement("div");
    card.className = "card series-card";
    card.innerHTML = `
      <div class="series-head">
        <h3>${esc(s.test)}</h3>
        <span class="series-range">normal: ${esc(rangeText(s.normal, s.unit))}</span>
      </div>
      <div class="series-canvas-wrap"><canvas id="chart-${i}"></canvas></div>
      <table class="source-table">
        <thead><tr><th>Date</th><th>Value</th><th>Source</th></tr></thead>
        <tbody>${s.points
          .map((p) => {
            const [file, page] = p.source.split("#p");
            const cls = outOfRange(p.value, s.normal) ? "out-of-range" : "";
            return `<tr><td>${formatDate(p.date)}</td><td class="value ${cls}">${p.value} ${esc(s.unit)}</td><td>${esc(file)}${page ? " · p" + esc(page) : ""}</td></tr>`;
          })
          .join("")}</tbody>
      </table>`;
    box.appendChild(card);
    drawChart(`chart-${i}`, s);
  });
}

function drawChart(canvasId, s) {
  const [lo, hi] = s.normal;
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
      ctx.fillStyle = "rgba(79, 166, 160, 0.10)";
      ctx.fillRect(a.left, top, a.right - a.left, bottom - top);
      ctx.restore();
    },
  };
  const values = s.points.map((p) => p.value);
  const axis = { ticks: { color: "#8fa0a8" }, grid: { color: "#2a343b" } };
  state.charts.push(
    new Chart($(canvasId).getContext("2d"), {
      type: "line",
      data: {
        labels: s.points.map((p) => formatDate(p.date)),
        datasets: [
          {
            data: values,
            borderColor: "#4fa6a0",
            backgroundColor: "#4fa6a0",
            borderWidth: 2,
            tension: 0.25,
            pointRadius: 5,
            pointBackgroundColor: values.map((v) => (outOfRange(v, s.normal) ? "#d9a441" : "#4fa6a0")),
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { afterLabel: (c) => s.points[c.dataIndex].source } },
        },
        scales: { x: axis, y: { ...axis, suggestedMin: lo ?? undefined, suggestedMax: hi ?? undefined } },
      },
      plugins: [band],
    })
  );
}

/* ---------- flags and summary ---------- */

const flagHtml = (f) => `
  <div class="card flag-card ${LEVEL_CLASS[f.level] || ""}">
    <p class="flag-title">${esc(f.title)}</p>
    <p class="flag-message">${esc(f.detail)}</p>
    <p class="flag-ask"><strong>Ask your doctor:</strong> ${esc(f.ask_doctor)}</p>
    <div class="flag-sources">${f.sources.map((s) => `<span class="source-chip">${esc(s)}</span>`).join("")}</div>
  </div>`;

function renderFlags(flags) {
  $("flags-content").innerHTML = flags.length
    ? flags.map(flagHtml).join("")
    : '<div class="empty-state">No flags for this person right now.</div>';
}

function renderSummary(s) {
  $("summary-content").innerHTML = `
    <h3 style="margin-top:0">${esc(s.person)} — visit summary</h3>
    <p class="summary-meta">Generated ${esc(s.generated)} · from recorded reports only</p>
    <p>${esc(s.intro)}</p>
    ${s.medicines.length ? `<p class="section-title">Medicines on record</p><p>${s.medicines.map((m) => esc(m)).join(", ")}</p>` : ""}
    ${s.top_trends.length ? `<p class="section-title">Top trends</p>${s.top_trends.map(flagHtml).join("")}` : ""}
    ${s.questions.length ? `<p class="section-title">Questions to ask the doctor</p><ol class="summary-lines">${s.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ol>` : ""}
    ${s.caveats.length ? `<p class="section-title">Data-quality notes</p>${s.caveats.map(caveatHtml).join("")}` : ""}
    <p class="summary-disclaimer">This summarizes recorded values and flagged trends only. It is not a diagnosis and gives no dosing advice.</p>`;
}

/* ---------- upload ---------- */

function wireUpload() {
  const zone = $("dropzone");
  const input = $("file-input");
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") input.click();
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
  if (!pdfs.length) return;
  const log = $("upload-log");
  if (log.querySelector(".empty-state")) log.innerHTML = "";
  const rows = pdfs.map((f) => {
    const row = document.createElement("div");
    row.className = "upload-row";
    row.innerHTML = `<span class="file-name">${esc(f.name)}</span><span>Processing…</span>`;
    log.prepend(row);
    return row;
  });
  const setMsg = (row, cls, msg) => {
    row.lastChild.className = cls;
    row.lastChild.textContent = msg;
  };
  if (state.mode === "demo") {
    rows.forEach((r) => setMsg(r, "status-warn", "Demo mode — start the backend to process files."));
    return;
  }
  try {
    const form = new FormData();
    pdfs.forEach((f) => form.append("files", f));
    const res = await fetch("/api/upload", { method: "POST", body: form });
    if (!res.ok) throw new Error(`upload returned ${res.status}`);
    const results = await res.json();
    results.forEach((r, i) => rows[i] && setMsg(rows[i], r.ok ? "status-ok" : "status-warn", r.message));
    const saved = results.find((r) => r.ok && r.person_id != null);
    await loadPeople(saved ? saved.person_id : state.personId);
    if (state.personId != null) await loadPerson(state.personId);
  } catch (err) {
    rows.forEach((r) => setMsg(r, "status-warn", `Upload failed — ${err.message}`));
  }
}

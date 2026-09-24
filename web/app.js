/*
OWNER: Frontend & Demo role — name: ________ (fill in when you pick this)
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

// TODO(FRONTEND): implement

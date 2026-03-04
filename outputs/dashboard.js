// dashboard.js — flask-connected dashboard

const API = ""  // same origin

let pollTimer  = null
let activeRun  = null


// ── on page load
window.onload = () => {
  loadFiles()
  refreshAccounts()
}


// ── load file lists into selects
async function loadFiles() {
  try {
    const r = await fetch(`${API}/api/files`)
    const d = await r.json()
    if (!d.ok) return

    const demoSel    = document.getElementById("demo-file")
    const onboardSel = document.getElementById("onboard-file")

    d.demo.forEach(f => {
      const o = document.createElement("option")
      o.value = `data/demo/${f}`
      o.text  = f
      demoSel.appendChild(o)
    })

    d.onboard.forEach(f => {
      const o = document.createElement("option")
      o.value = `data/onboard/${f}`
      o.text  = f
      onboardSel.appendChild(o)
    })
  } catch(e) {
    console.error("loadFiles failed:", e)
  }
}


// ── refresh accounts from sqlite
async function refreshAccounts() {
  try {
    const r = await fetch(`${API}/api/accounts`)
    const d = await r.json()

    if (!d.ok) {
      showEmpty()
      return
    }

    const accts = d.accounts || []

    if (accts.length === 0) {
      showEmpty()
      return
    }

    hideEmpty()
    renderMetrics(accts)
    renderAccounts(accts)
  } catch(e) {
    console.error("refreshAccounts failed:", e)
    showEmpty()
  }
}


// ── render metrics from accounts
function renderMetrics(accts) {
  const el = document.getElementById("metrics")
  el.style.display = "grid"

  const total   = accts.length
  const ok      = accts.filter(a => a.status === "v2_done").length
  const fail    = accts.filter(a => a.status === "failed").length
  const totChg  = accts.reduce((s, a) => s + (a.open_qs_cnt || 0), 0)

  document.getElementById("m-total").textContent   = total
  document.getElementById("m-ok").textContent      = ok
  document.getElementById("m-fail").textContent    = fail
  document.getElementById("m-changes").textContent = "—"
  document.getElementById("m-openqs").textContent  = totChg
}


// ── render account cards
function renderAccounts(accts) {
  document.getElementById("acct-title").style.display = "block"
  document.getElementById("acct-grid").style.display  = "grid"

  const grid = document.getElementById("acct-grid")
  grid.innerHTML = accts.map(a => buildCard(a)).join("")
}


// ── build single account card
function buildCard(a) {
  const isDone = a.status === "v2_done"
  const isV1   = a.status === "v1_done"

  const badge = isDone
    ? `<span class="badge badge-green">v2 done</span>`
    : isV1
    ? `<span class="badge badge-amber">v1 only</span>`
    : `<span class="badge badge-gray">${esc(a.status)}</span>`

  const name = a.co_name || a.acct_id

  const v1At = a.v1_at
    ? new Date(a.v1_at).toLocaleString() : "—"
  const v2At = a.v2_at
    ? new Date(a.v2_at).toLocaleString() : "—"

  const diffBtn = isDone
    ? `<button class="btn btn-gray"
         style="width:100%;margin-top:10px;font-size:0.8rem"
         onclick="loadChangelog('${esc(a.acct_id)}', '${esc(name)}')">
         View Changelog Diff →
       </button>`
    : ""

  const onboardBtn = isV1
    ? `<button class="btn btn-green"
         style="width:100%;margin-top:10px;font-size:0.8rem"
         onclick="quickOnboard('${esc(a.acct_id)}')">
         ▶ Run Pipeline B
       </button>`
    : ""

  return `
    <div class="acct-card">
      <div class="acct-hdr">
        <div>
          <h3>${esc(name)}</h3>
          <div class="acct-id">${esc(a.acct_id)}</div>
        </div>
        ${badge}
      </div>
      <div class="acct-body">
        <div class="stat-row">
          <span class="s-lbl">Status</span>
          <span class="s-val ${isDone ? 'green' : 'amber'}">${esc(a.status)}</span>
        </div>
        <div class="stat-row">
          <span class="s-lbl">Open Questions</span>
          <span class="s-val ${(a.open_qs_cnt > 5) ? 'amber' : 'green'}">
            ${a.open_qs_cnt ?? "—"}
          </span>
        </div>
        <div class="stat-row">
          <span class="s-lbl">v1 processed</span>
          <span class="s-val">${v1At}</span>
        </div>
        <div class="stat-row">
          <span class="s-lbl">v2 processed</span>
          <span class="s-val">${v2At}</span>
        </div>
        ${diffBtn}
        ${onboardBtn}
      </div>
    </div>
  `
}


// ── run batch
async function runBatch() {
  if (!confirm("Run batch pipeline on all accounts? This will use Gemini API calls.")) return

  startLog("batch", "═══ BATCH PIPELINE ═══")

  try {
    const r = await fetch(`${API}/api/run/batch`, { method: "POST" })
    const d = await r.json()
    if (d.ok) pollLog(d.run_key, () => refreshAccounts())
    else appendLog("err", `Error: ${d.error}`)
  } catch(e) {
    appendLog("err", `Request failed: ${e}`)
  }
}


// ── run demo pipeline
async function runDemo() {
  const fpath = document.getElementById("demo-file").value
  if (!fpath) { alert("Select a demo file first"); return }

  startLog(`demo_${fpath.split("/").pop().replace(".txt","").replace(".m4a","")}`,
    `═══ PIPELINE A → ${fpath} ═══`)

  try {
    const r = await fetch(`${API}/api/run/demo`, {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ fpath })
    })
    const d = await r.json()
    if (d.ok) pollLog(d.run_key, () => refreshAccounts())
    else appendLog("err", `Error: ${d.error}`)
  } catch(e) {
    appendLog("err", `Request failed: ${e}`)
  }
}


// ── run onboard pipeline
async function runOnboard() {
  const fpath   = document.getElementById("onboard-file").value
  const acct_id = document.getElementById("onboard-acct").value.trim()

  if (!fpath)   { alert("Select an onboard file first"); return }
  if (!acct_id) { alert("Enter the ACCT-XXXXXXXX ID from Pipeline A"); return }

  startLog(`onboard_${acct_id}`,
    `═══ PIPELINE B → ${fpath} | ${acct_id} ═══`)

  try {
    const r = await fetch(`${API}/api/run/onboard`, {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ fpath, acct_id })
    })
    const d = await r.json()
    if (d.ok) pollLog(d.run_key, () => refreshAccounts())
    else appendLog("err", `Error: ${d.error}`)
  } catch(e) {
    appendLog("err", `Request failed: ${e}`)
  }
}


// ── quick run onboard from card button
function quickOnboard(acctId) {
  document.getElementById("onboard-acct").value = acctId
  document.getElementById("onboard-file").focus()
  document.getElementById("run-section")
    .scrollIntoView({ behavior: "smooth" })
}


// ── poll run log
function pollLog(runKey, onDone) {
  activeRun = runKey
  if (pollTimer) clearInterval(pollTimer)

  pollTimer = setInterval(async () => {
    try {
      const r = await fetch(`${API}/api/log/${runKey}`)
      const d = await r.json()

      const body = document.getElementById("log-body")
      body.innerHTML = d.lines.map(l => {
        const cls = l.startsWith("ERROR") ? "err"
          : l.includes("DONE") || l.includes("Done") ? "ok"
          : l.includes("Start") || l.includes("═══") ? "info"
          : "plain"
        return `<div class="log-line ${cls}">${esc(l)}</div>`
      }).join("")

      body.scrollTop = body.scrollHeight

      // check if done
      const last = d.lines[d.lines.length - 1] || ""
      if (last.includes("DONE") || last.includes("Done") || last.includes("ERROR")) {
        clearInterval(pollTimer)
        pollTimer = null
        if (onDone) setTimeout(onDone, 1000)
      }
    } catch(e) {
      clearInterval(pollTimer)
    }
  }, 1000)
}


// ── log panel helpers
function startLog(runKey, title) {
  activeRun = runKey
  document.getElementById("log-panel").style.display = "block"
  document.getElementById("log-title").textContent   = title
  document.getElementById("log-body").innerHTML      = ""
  document.getElementById("log-panel")
    .scrollIntoView({ behavior: "smooth" })
}

function appendLog(cls, msg) {
  const body = document.getElementById("log-body")
  body.innerHTML += `<div class="log-line ${cls}">${esc(msg)}</div>`
  body.scrollTop  = body.scrollHeight
}

function closeLog() {
  document.getElementById("log-panel").style.display = "none"
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}


// ── load changelog for account
async function loadChangelog(acctId, name) {
  try {
    const r  = await fetch(`${API}/api/changelog/${acctId}`)
    const d  = await r.json()
    if (!d.ok) { alert("Changelog not found for this account"); return }
    renderDiff(acctId, name, d.changelog)
  } catch(e) {
    alert(`Failed to load changelog: ${e}`)
  }
}


// ── render diff panel
function renderDiff(acctId, name, cl) {
  const panel = document.getElementById("diff-panel")
  panel.classList.add("open")

  document.getElementById("diff-title").textContent =
    `Changelog — ${name} (${cl.total_changes ?? 0} changes)`

  const changes = cl.changes           || []
  const openQs  = cl.open_qs_remaining || []

  const rows = changes.map(c => `
    <div class="chg-row">
      <div class="chg-cell chg-field">${esc(c.field)}</div>
      <div class="chg-cell">
        <span class="act-${c.action}">${c.action}</span>
      </div>
      <div class="chg-cell val-v1">${fmtVal(c.v1)}</div>
      <div class="chg-cell val-v2">${fmtVal(c.v2)}</div>
    </div>
  `).join("")

  const qsHtml = openQs.length === 0
    ? `<div class="qs-section">
         <h4>Open Questions</h4>
         <p style="color:#34d399;font-size:0.85rem">All resolved ✓</p>
       </div>`
    : `<div class="qs-section">
         <h4>Open Questions Remaining (${openQs.length})</h4>
         ${openQs.map((q,i) => `
           <div class="q-item">
             <span class="q-num">${i+1}.</span>
             <span>${esc(q)}</span>
           </div>`).join("")}
       </div>`

  document.getElementById("diff-rows").innerHTML = rows + qsHtml
  panel.scrollIntoView({ behavior: "smooth", block: "start" })
}


// ── close diff panel
function closeDiff() {
  document.getElementById("diff-panel").classList.remove("open")
}


// ── empty state helpers
function showEmpty() {
  document.getElementById("empty-state").style.display  = "block"
  document.getElementById("acct-grid").style.display    = "none"
  document.getElementById("acct-title").style.display   = "none"
  document.getElementById("metrics").style.display      = "none"
}

function hideEmpty() {
  document.getElementById("empty-state").style.display = "none"
}


// ── escape html
function esc(s) {
  if (!s) return ""
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}


// ── format value
function fmtVal(v) {
  if (v === null || v === undefined)
    return `<span class="val-null">null</span>`
  if (Array.isArray(v)) {
    if (v.length === 0) return `<span class="val-null">[]</span>`
    return v.map(x => `<div>• ${esc(String(x))}</div>`).join("")
  }
  return esc(String(v))
}
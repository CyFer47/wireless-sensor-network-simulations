const apiBase = window.WSN_API_BASE || window.location.origin;

const LS_SELECTED_RUN = "wsn.selectedRunId";
const LS_CURRENT_TAB = "wsn.currentTab";
const LS_AUTO_REFRESH = "wsn.autoRefresh";

const pageState = {
  events: 1,
  nodefinal: 1,
  nodesstatic: 1,
  raw: 1,
  analytics: 1,
};

const globalMetricDefs = [
  ["raw_tx_cum", "Raw TX", "#2f8bbd"],
  ["raw_rx_cum", "Raw RX", "#56a0d3"],
  ["agg_tx_cum", "Agg TX", "#0f9d8d"],
  ["agg_rx_cum", "Agg RX", "#13b6a3"],
  ["direct_agg_rx_cum", "Direct Agg RX", "#17a2d4"],
  ["relayed_agg_rx_cum", "Relayed Agg RX", "#2f6bbd"],
  ["relay_fwd_cum", "Relay Fwd", "#2f52a2"],
  ["avg_res_j", "Avg Residual", "#2f9e44"],
  ["min_res_j", "Min Residual", "#79b43c"],
  ["consumed_j", "Consumed", "#d17b21"],
  ["failed_chs", "Failed CH", "#c93535"],
  ["recovered_clusters", "Recovered Clusters", "#c8a323"],
];

const clusterMetricDefs = [
  ["cluster_consumed_j", "Consumed", "#d17b21"],
  ["ch_res_j", "CH Residual", "#2f9e44"],
  ["pending_raw", "Pending Raw", "#c93535"],
  ["agg_tx_cum", "Agg TX", "#0f9d8d"],
  ["relay_fwd_cum", "Relay Fwd", "#2f52a2"],
  ["raw_rx_cum", "Raw RX", "#56a0d3"],
];

const replayMarkerStyles = {
  firstAgg: ["first aggregate", "aggregate"],
  firstFailure: ["failure injection", "failure"],
  recoveryStart: ["recovery start", "recovery-start"],
  recoveryApplied: ["recovery applied", "recovery-applied"],
  firstRecoveredRaw: ["first recovered raw", "recovery-applied"],
  firstRecoveredAgg: ["first recovered aggregate", "recovered-aggregate"],
  end: ["simulation end", "end"],
};

const state = {
  selectedRunId: null,
  currentTab: "overview",
  refreshTimer: null,
  replayPlaying: false,
  replaySpeed: 1,
  replayCurrentTime: 0,
  replayMaxTime: 30,
  replayMarkers: null,
  replayMarkersRunId: null,
  replayFetchInFlight: false,
  replayRafId: null,
  replayLastFrameTs: null,
  replayLastFetchTs: 0,
  replayPrevClusterStatus: {},
  snapshotCache: new Map(),
  compareSecondaryRunId: null,
  compareCsv: "",
  analyticsRunIdsByPage: [],
  analyticsSelectedRunIds: new Set(),
  analyticsLastFilters: null,
  analyticsLastGroupBy: "",
  analyticsCachedRows: [],
  globalSelectedMetrics: new Set(["raw_tx_cum", "raw_rx_cum", "agg_tx_cum", "agg_rx_cum"]),
  clusterSelectedMetrics: new Set(["cluster_consumed_j", "ch_res_j", "pending_raw", "agg_tx_cum"]),
};

function q(id) {
  return document.getElementById(id);
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[m]));
}

function valueOrNull(id) {
  const el = q(id);
  if (!el) return null;
  const v = el.value;
  return v === "" ? null : v;
}

function queryString(params) {
  const sp = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v === null || v === undefined || v === "") return;
    sp.append(k, String(v));
  });
  return sp.toString();
}

function parseBoolOrEmpty(v) {
  if (v === "true") return true;
  if (v === "false") return false;
  return null;
}

function idsCsv(ids) {
  if (!ids || !ids.size) return "";
  return [...ids].sort((a, b) => a - b).join(",");
}

function triggerDownload(url) {
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function toNumber(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function fmt(v, digits = 3) {
  if (v === null || v === undefined || v === "") return "-";
  if (typeof v === "number" && Number.isFinite(v)) return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  return String(v);
}

function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}

function downsampleRows(rows, maxPoints = 320) {
  if (!Array.isArray(rows) || rows.length <= maxPoints) return rows || [];
  const step = Math.ceil(rows.length / maxPoints);
  const out = [];
  for (let i = 0; i < rows.length; i += step) out.push(rows[i]);
  const last = rows[rows.length - 1];
  if (out[out.length - 1] !== last) out.push(last);
  return out;
}

function renderPanelMessage(hostId, message) {
  const host = q(hostId);
  if (host) host.innerHTML = `<div class="panel">${escapeHtml(message)}</div>`;
}

function renderLoading(hostId, label = "Loading...") {
  renderPanelMessage(hostId, label);
}

function renderError(hostId, err) {
  renderPanelMessage(hostId, `Error: ${String(err)}`);
}

function withStatusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s.includes("fail")) return "status-failed";
  if (s.includes("recovering")) return "status-recovering";
  if (s.includes("recover")) return "status-recovered";
  return "status-normal";
}

function statusClassForCluster(status) {
  const s = String(status || "").toLowerCase();
  if (s.includes("fail")) return "failed";
  if (s.includes("recovering")) return "recovering";
  if (s.includes("recover")) return "recovered";
  return "normal";
}

function categoryClass(category) {
  const c = String(category || "other").toLowerCase();
  return `tag tag-${c}`;
}

function renderKVTable(obj) {
  const entries = Object.entries(obj || {});
  if (!entries.length) return '<div class="empty-state">No data.</div>';
  return `<table class="kv-table"><tbody>${entries.map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(v ?? "")}</td></tr>`).join("")}</tbody></table>`;
}

function renderCards(hostId, cards) {
  const host = q(hostId);
  if (!host) return;
  if (!cards || cards.length === 0) {
    host.innerHTML = '<div class="empty-state">No data.</div>';
    return;
  }
  host.innerHTML = `<div class="summary-grid">${cards.map((card) => `<div class="summary-chip"><div class="label">${escapeHtml(card.label)}</div><div class="value">${escapeHtml(card.value)}</div></div>`).join("")}</div>`;
}

function renderTable(hostId, rows, rowClassFn, columnOrder) {
  const host = q(hostId);
  if (!host) return;
  if (!rows || rows.length === 0) {
    host.innerHTML = '<div class="panel">No rows found.</div>';
    return;
  }
  const cols = columnOrder && columnOrder.length ? columnOrder : Object.keys(rows[0]);
  const thead = cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
  const tbody = rows.map((r) => {
    const rowCls = rowClassFn ? rowClassFn(r) : "";
    const cells = cols.map((c) => {
      const v = r[c];
      if (c === "category") return `<td><span class="${categoryClass(v)}">${escapeHtml(v)}</span></td>`;
      if (c === "status" || c === "final_status") return `<td><span class="${withStatusClass(v)}">${escapeHtml(v)}</span></td>`;
      if (v && typeof v === "object") return `<td><pre>${escapeHtml(JSON.stringify(v))}</pre></td>`;
      return `<td>${escapeHtml(v ?? "")}</td>`;
    }).join("");
    return `<tr class="${rowCls}">${cells}</tr>`;
  }).join("");
  host.innerHTML = `<div class="table-wrap"><table><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table></div>`;
}

function renderPager(hostId, key, data, loader) {
  const host = q(hostId);
  if (!host) return;
  const pages = Math.max(1, Number(data.pages || 0));
  const page = Number(data.page || 1);
  host.innerHTML = `
    <button ${page <= 1 ? "disabled" : ""} id="${key}Prev">Prev</button>
    <span>Page ${page} / ${pages} | Total ${data.total || 0}</span>
    <button ${page >= pages ? "disabled" : ""} id="${key}Next">Next</button>`;
  q(`${key}Prev`).onclick = () => loader(Math.max(1, page - 1));
  q(`${key}Next`).onclick = () => loader(Math.min(pages, page + 1));
}

async function api(path) {
  const res = await fetch(`${apiBase}${path}`);
  if (!res.ok) {
    throw new Error(`${res.status}: ${await res.text()}`);
  }
  return res.json();
}

function setActiveTab(tab) {
  state.currentTab = tab;
  localStorage.setItem(LS_CURRENT_TAB, tab);
  document.querySelectorAll(".tab").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tab}`));
}

function getSelectedRun() {
  return state.selectedRunId || Number(localStorage.getItem(LS_SELECTED_RUN) || 0) || null;
}

function saveRunSelection(runId) {
  state.selectedRunId = runId ? Number(runId) : null;
  if (state.selectedRunId) localStorage.setItem(LS_SELECTED_RUN, String(state.selectedRunId));
}

function parseNextHopId(nextHop) {
  const m = /CH\((\d+)\)/i.exec(String(nextHop || ""));
  return m ? Number(m[1]) : null;
}

function formatStatusCounts(clusters) {
  const counts = { normal: 0, failed: 0, recovering: 0, recovered: 0 };
  (clusters || []).forEach((c) => {
    const s = statusClassForCluster(c.status);
    counts[s] = (counts[s] || 0) + 1;
  });
  return counts;
}

function buildPathSummary(clusters) {
  if (!clusters || !clusters.length) return "No active routes.";
  const lines = clusters.slice(0, 8).map((c) => {
    const original = Number(c.original_ch_id);
    const current = Number(c.current_ch_id);
    const bsRoute = String(c.next_hop || "BS");
    if (original !== current) {
      return `C${c.cluster_id}: CH${original} -> CH${current} -> ${bsRoute}`;
    }
    return `C${c.cluster_id}: CH${current} -> ${bsRoute}`;
  });
  const extra = clusters.length > 8 ? ` (+${clusters.length - 8} more)` : "";
  return `${lines.join(" | ")}${extra}`;
}

function initMetricChecklist(hostId, defs, selectedSet, onChange) {
  const host = q(hostId);
  host.innerHTML = defs.map(([key, label, color]) => `
    <label class="metric-item" style="border-color:${color}">
      <input type="checkbox" data-metric="${key}" ${selectedSet.has(key) ? "checked" : ""} />
      <span>${escapeHtml(label)}</span>
    </label>`).join("");
  host.querySelectorAll("input[type=checkbox]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const metric = cb.getAttribute("data-metric");
      if (cb.checked) selectedSet.add(metric);
      else selectedSet.delete(metric);
      onChange();
    });
  });
}

function getMetricColor(defs, key) {
  const found = defs.find((d) => d[0] === key);
  return found ? found[2] : "#177e98";
}

function getMetricLabel(defs, key) {
  const found = defs.find((d) => d[0] === key);
  return found ? found[1] : key;
}

function drawMultiSeriesChart(canvasId, rows, xKey, metrics, defs, legendId, statsHostId) {
  const canvas = q(canvasId);
  const legendHost = q(legendId);
  if (!canvas || !legendHost) return;

  const dataRows = downsampleRows(rows, 360);
  const activeMetrics = metrics.filter((m) => dataRows.some((r) => r[m] !== undefined));
  legendHost.innerHTML = activeMetrics.map((m) => {
    const color = getMetricColor(defs, m);
    return `<span class="legend-item"><span class="legend-swatch" style="background:${color};border-color:${color}"></span>${escapeHtml(getMetricLabel(defs, m))}</span>`;
  }).join("") || "<span class='legend-item'>No metrics selected</span>";

  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(320, Math.floor(rect.width * dpr));
  const height = Math.floor((Number(canvas.getAttribute("height")) || 240) * dpr);
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, height / dpr);

  if (!dataRows.length || !activeMetrics.length) {
    ctx.fillStyle = "#5a6f79";
    ctx.fillText("No data", 12, 20);
    return;
  }

  const xs = dataRows.map((r) => toNumber(r[xKey]));
  const ys = [];
  activeMetrics.forEach((m) => dataRows.forEach((r) => ys.push(toNumber(r[m]))));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const pad = 34;
  const plotW = rect.width - pad * 2;
  const plotH = (height / dpr) - pad * 2;
  const normX = (x) => pad + ((x - minX) / ((maxX - minX) || 1)) * plotW;
  const normY = (y) => (height / dpr) - pad - ((y - minY) / ((maxY - minY) || 1)) * plotH;

  ctx.strokeStyle = "#9ab3bf";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad, pad);
  ctx.lineTo(pad, height / dpr - pad);
  ctx.lineTo(rect.width - pad, height / dpr - pad);
  ctx.stroke();

  activeMetrics.forEach((m) => {
    ctx.strokeStyle = getMetricColor(defs, m);
    ctx.lineWidth = 2;
    ctx.beginPath();
    dataRows.forEach((r, i) => {
      const x = normX(toNumber(r[xKey]));
      const y = normY(toNumber(r[m]));
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });

  ctx.fillStyle = "#3a5562";
  ctx.font = "11px IBM Plex Sans";
  ctx.fillText(`${xKey}: ${fmt(minX, 1)} -> ${fmt(maxX, 1)}`, pad, height / dpr - 8);
  ctx.fillText(`y-range: ${fmt(minY, 3)} -> ${fmt(maxY, 3)} (${dataRows.length} pts)`, pad, 14);

  canvas.onmousemove = (ev) => {
    const b = canvas.getBoundingClientRect();
    const px = ev.clientX - b.left;
    const xValue = minX + ((px - pad) / Math.max(plotW, 1)) * ((maxX - minX) || 1);
    let nearest = dataRows[0];
    let best = Number.POSITIVE_INFINITY;
    for (const row of dataRows) {
      const d = Math.abs(toNumber(row[xKey]) - xValue);
      if (d < best) {
        best = d;
        nearest = row;
      }
    }
    if (q(statsHostId)) {
      const vals = activeMetrics.slice(0, 6).map((m) => `${getMetricLabel(defs, m)}=${fmt(nearest[m], 3)}`).join(" | ");
      q(statsHostId).innerHTML = `<h3>Series</h3><div>t=${fmt(nearest[xKey], 2)} | ${escapeHtml(vals)}</div>`;
    }
  };
}

function drawGroupedBarChart(canvasId, labels, primaryVals, secondaryVals, colors = ["#2f8bbd", "#d17b21"]) {
  const canvas = q(canvasId);
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(320, Math.floor(rect.width * dpr));
  const height = Math.floor((Number(canvas.getAttribute("height")) || 220) * dpr);
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, height / dpr);

  if (!labels.length) {
    ctx.fillStyle = "#5a6f79";
    ctx.fillText("No data", 12, 20);
    return;
  }

  const pad = 30;
  const h = height / dpr;
  const w = rect.width;
  const maxVal = Math.max(1, ...primaryVals, ...secondaryVals);
  const groupW = (w - pad * 2) / labels.length;
  const barW = Math.max(6, groupW * 0.33);

  ctx.strokeStyle = "#9ab3bf";
  ctx.beginPath();
  ctx.moveTo(pad, pad);
  ctx.lineTo(pad, h - pad);
  ctx.lineTo(w - pad, h - pad);
  ctx.stroke();

  labels.forEach((label, i) => {
    const gx = pad + i * groupW + groupW * 0.15;
    const pVal = toNumber(primaryVals[i]);
    const sVal = toNumber(secondaryVals[i]);
    const ph = ((h - pad * 2) * pVal) / maxVal;
    const sh = ((h - pad * 2) * sVal) / maxVal;

    ctx.fillStyle = colors[0];
    ctx.fillRect(gx, h - pad - ph, barW, ph);
    ctx.fillStyle = colors[1];
    ctx.fillRect(gx + barW + 4, h - pad - sh, barW, sh);

    ctx.save();
    ctx.translate(gx + barW, h - pad + 10);
    ctx.rotate(-0.35);
    ctx.fillStyle = "#3a5562";
    ctx.font = "10px IBM Plex Sans";
    ctx.fillText(label, 0, 0);
    ctx.restore();
  });
}

function comparisonTable(title, rows) {
  return `
    <h3>${escapeHtml(title)}</h3>
    <div class="table-wrap">
      <table class="compare-table">
        <thead><tr><th>Metric</th><th>Primary</th><th>Comparison</th><th>Delta (P-C)</th></tr></thead>
        <tbody>${rows.map((r) => `<tr><td>${escapeHtml(r.metric)}</td><td>${escapeHtml(r.primary)}</td><td>${escapeHtml(r.secondary)}</td><td><span class="${escapeHtml(r.deltaCls)}">${escapeHtml(r.delta)}</span></td></tr>`).join("")}</tbody>
      </table>
    </div>`;
}

function compareDelta(primary, secondary, direction) {
  const p = toNumber(primary, NaN);
  const s = toNumber(secondary, NaN);
  if (!Number.isFinite(p) || !Number.isFinite(s)) return { text: "-", cls: "delta-neutral" };
  const diff = p - s;
  if (Math.abs(diff) < 1e-9) return { text: "0", cls: "delta-neutral" };
  const improved = direction === "higher-better" ? diff > 0 : diff < 0;
  return { text: diff > 0 ? `+${fmt(diff, 3)}` : fmt(diff, 3), cls: improved ? "delta-up" : "delta-down" };
}

function setupGlobalPreset() {
  const sel = q("globalMetricPreset");
  sel.innerHTML = `
    <option value="delivery">delivery</option>
    <option value="aggregation">aggregation</option>
    <option value="energy">energy</option>
    <option value="resilience">resilience</option>
    <option value="all">all</option>`;
  sel.value = "delivery";
  sel.onchange = () => {
    const v = sel.value;
    const set = state.globalSelectedMetrics;
    set.clear();
    if (v === "delivery") ["raw_tx_cum", "raw_rx_cum"].forEach((x) => set.add(x));
    else if (v === "aggregation") ["agg_tx_cum", "agg_rx_cum", "direct_agg_rx_cum", "relayed_agg_rx_cum", "relay_fwd_cum"].forEach((x) => set.add(x));
    else if (v === "energy") ["avg_res_j", "min_res_j", "consumed_j"].forEach((x) => set.add(x));
    else if (v === "resilience") ["failed_chs", "recovered_clusters", "pending_raw_total"].forEach((x) => set.add(x));
    else globalMetricDefs.forEach((d) => set.add(d[0]));
    initMetricChecklist("globalMetricChecklist", globalMetricDefs, state.globalSelectedMetrics, () => loadGlobal());
    loadGlobal();
  };
}

async function loadHealth() {
  try {
    const h = await api("/api/health");
    const badge = q("statusBadge");
    badge.textContent = h.database === "connected" ? "db:connected" : "db:disconnected";
    badge.classList.remove("ok", "err");
    badge.classList.add(h.database === "connected" ? "ok" : "err");
  } catch {
    const badge = q("statusBadge");
    badge.textContent = "db:error";
    badge.classList.remove("ok");
    badge.classList.add("err");
  }
}

async function loadRuns() {
  const data = await api("/api/runs?page=1&size=100&sort=run_id&order=desc");
  const runSelect = q("runSelect");
  runSelect.innerHTML = data.items.map((r) => `<option value="${r.run_id}">Run ${r.run_id} | ${escapeHtml(r.experiment_version || "-")} | ${escapeHtml(r.started_at || "")}</option>`).join("");

  const stored = Number(localStorage.getItem(LS_SELECTED_RUN) || 0) || null;
  if (stored && data.items.some((r) => Number(r.run_id) === stored)) saveRunSelection(stored);
  else if (!state.selectedRunId && data.items.length > 0) saveRunSelection(data.items[0].run_id);
  if (state.selectedRunId) runSelect.value = String(state.selectedRunId);

  const primary = q("comparePrimaryRun");
  const secondary = q("compareSecondaryRun");
  const options = data.items.map((r) => `<option value="${r.run_id}">Run ${r.run_id}</option>`).join("");
  primary.innerHTML = options;
  secondary.innerHTML = options;
  if (state.selectedRunId) primary.value = String(state.selectedRunId);
  if (!state.compareSecondaryRunId) {
    const alt = data.items.find((x) => Number(x.run_id) !== Number(state.selectedRunId));
    state.compareSecondaryRunId = alt ? Number(alt.run_id) : Number(state.selectedRunId);
  }
  secondary.value = String(state.compareSecondaryRunId);
}

function setOverviewCards(overview) {
  const rs = overview?.result_summary || {};
  renderCards("summaryCards", [
    { label: "Run ID", value: overview.run_id },
    { label: "Raw Delivery %", value: `${fmt(rs.raw_delivery_pct, 2)}%` },
    { label: "Failed CHs", value: rs.failed_chs },
    { label: "Recovered Clusters", value: rs.recovered_clusters },
    { label: "Pending Raw", value: rs.pending_raw_total },
    { label: "Avg Residual J", value: fmt(rs.avg_residual_j) },
    { label: "Min Residual J", value: fmt(rs.min_residual_j) },
    { label: "Total Consumed J", value: fmt(rs.total_consumed_j) },
  ]);
}

async function loadOverview() {
  const runId = getSelectedRun();
  if (!runId) return;
  renderLoading("overviewIdentity");
  try {
    const data = await api(`/api/run/${runId}/overview`);
    setOverviewCards(data);
    q("overviewIdentity").innerHTML = `<h3>Run Identity</h3>${renderKVTable(data.run_identity)}`;
    q("overviewConfig").innerHTML = `<h3>Configuration Summary</h3>${renderKVTable(data.configuration_summary)}`;
    q("overviewResult").innerHTML = `<h3>Result Summary</h3>${renderKVTable(data.result_summary)}`;
    q("clusterSummaryGrid").innerHTML = (data.cluster_summary || []).map((c) => `<div class="cluster-card ${statusClassForCluster(c.status)}"><h4>Cluster ${escapeHtml(c.cluster_id)}</h4>${renderKVTable({ status: c.status, original_ch: c.original_ch_id, current_ch: c.current_ch_id, mode: c.mode, next_hop: c.next_hop, members: c.members_count, raw_rx: c.raw_rx_cum, pending_raw: c.pending_raw, agg_tx: c.agg_tx_cum, relay_forwarded: c.relay_fwd_cum, ch_residual_j: c.ch_res_j, avg_member_residual_j: c.avg_mem_res_j, cluster_consumed_j: c.cluster_consumed_j, ch_changed: c.ch_changed, recovery_applied: c.recovery_applied })}</div>`).join("") || '<div class="panel">No cluster data.</div>';

    state.replayMaxTime = Math.max(1, toNumber(data.configuration_summary?.sim_time_s, 30));
    q("replayTimeRange").max = String(state.replayMaxTime);
    q("replayExactTime").max = String(state.replayMaxTime);
    q("replayBar").setAttribute("aria-valuemax", String(state.replayMaxTime));
    q("replayBarEndLabel").textContent = `${fmt(state.replayMaxTime, 1)}s`;
  } catch (err) {
    renderError("overviewIdentity", err);
  }
}

async function loadGlobal() {
  const runId = getSelectedRun();
  if (!runId) return;
  renderLoading("globalTable");
  try {
    const params = new URLSearchParams();
    const fromTime = valueOrNull("globalFromTime");
    const toTime = valueOrNull("globalToTime");
    if (fromTime !== null) params.append("from_time", fromTime);
    if (toTime !== null) params.append("to_time", toTime);

    const rows = await api(`/api/run/${runId}/global-timeseries?${params.toString()}`);
    const metrics = [...state.globalSelectedMetrics];
    drawMultiSeriesChart("globalChart", rows, "sim_time_s", metrics, globalMetricDefs, "globalLegend", "globalStats");
    q("globalStats").innerHTML = `<h3>Series</h3><div>Metrics: ${metrics.map((m) => getMetricLabel(globalMetricDefs, m)).join(", ")} | points: ${rows.length}</div>`;
    renderTable("globalTable", rows);
  } catch (err) {
    renderError("globalTable", err);
  }
}

function buildClusterCompactSummary(rows, selectedCluster) {
  const host = q("clusterCompactSummary");
  if (!rows || rows.length === 0) {
    host.innerHTML = "<h3>Cluster Summary</h3><div>No rows.</div>";
    return;
  }
  const grouped = new Map();
  rows.forEach((r) => {
    if (!grouped.has(r.cluster_id)) grouped.set(r.cluster_id, []);
    grouped.get(r.cluster_id).push(r);
  });
  const subset = selectedCluster ? (grouped.get(Number(selectedCluster)) ? [[Number(selectedCluster), grouped.get(Number(selectedCluster))]] : []) : [...grouped.entries()];
  host.innerHTML = `<h3>Cluster Summary</h3>${subset.map(([cid, list]) => {
    const first = list[0];
    const last = list[list.length - 1];
    const chChanged = Number(first.original_ch_id) !== Number(last.current_ch_id);
    return `<div class="panel"><strong>Cluster ${cid}</strong><br/>original CH: ${first.original_ch_id} | final CH: ${last.current_ch_id}<br/>CH changed: ${chChanged} | final status: ${escapeHtml(last.status)}<br/>pending raw: ${escapeHtml(last.pending_raw)} | agg tx: ${escapeHtml(last.agg_tx_cum)}</div>`;
  }).join("")}`;
}

async function loadClusters() {
  const runId = getSelectedRun();
  if (!runId) return;
  renderLoading("clusterTable");
  try {
    const params = new URLSearchParams();
    const cid = valueOrNull("clusterFilterId");
    const fromTime = valueOrNull("clusterFromTime");
    const toTime = valueOrNull("clusterToTime");
    if (cid !== null) params.append("cluster_id", cid);
    if (fromTime !== null) params.append("from_time", fromTime);
    if (toTime !== null) params.append("to_time", toTime);

    const rows = await api(`/api/run/${runId}/cluster-timeseries?${params.toString()}`);
    const metrics = [...state.clusterSelectedMetrics];
    drawMultiSeriesChart("clusterChart", rows, "sim_time_s", metrics, clusterMetricDefs, "clusterLegend", "clusterCompactSummary");
    buildClusterCompactSummary(rows, cid);
    renderTable("clusterTable", rows, null);
  } catch (err) {
    renderError("clusterTable", err);
  }
}

function renderEventTimeline(items) {
  const host = q("eventsTimeline");
  if (!items || items.length === 0) {
    host.innerHTML = "<h3>Event Timeline</h3><div class='empty-state'>No events in the current filter.</div>";
    return;
  }
  host.innerHTML = `<h3>Event Timeline</h3><div class="timeline-strip">${items.map((e) => `<div class="event-chip ${categoryClass(e.category)}"><span class="time">t=${escapeHtml(fmt(e.sim_time_s, 1))}</span><span class="type">${escapeHtml(e.event_type || "event")}</span><span class="msg">${escapeHtml(e.message || "")}</span></div>`).join("")}</div>`;
}

async function loadEvents(page = 1) {
  const runId = getSelectedRun();
  if (!runId) return;
  pageState.events = page;
  renderLoading("eventsTable");
  try {
    const params = new URLSearchParams({ page: String(page), size: "30", sort: "sim_time_s", order: q("eventOrder").value });
    const search = valueOrNull("eventSearch");
    const category = valueOrNull("eventCategory");
    const fromTime = valueOrNull("eventFromTime");
    const toTime = valueOrNull("eventToTime");
    if (search) params.append("search", search);
    if (category) params.append("category", category);
    if (fromTime !== null) params.append("from_time", fromTime);
    if (toTime !== null) params.append("to_time", toTime);
    const data = await api(`/api/run/${runId}/events?${params.toString()}`);
    renderEventTimeline((data.items || []).slice(0, 20));
    renderTable("eventsTable", data.items || []);
    renderPager("eventsPager", "events", data, loadEvents);
  } catch (err) {
    renderError("eventsTable", err);
  }
}

async function loadNodesStatic(page = 1) {
  const runId = getSelectedRun();
  if (!runId) return;
  pageState.nodesstatic = page;
  renderLoading("nodesStaticTable");
  try {
    const params = new URLSearchParams({ page: String(page), size: "30", sort: q("nodesStaticSort").value, order: q("nodesStaticOrder").value });
    const nodeId = valueOrNull("nodesStaticNodeId");
    const role = valueOrNull("nodesStaticRoleFilter");
    const clusterId = valueOrNull("nodesStaticClusterFilter");
    if (nodeId !== null) params.append("nodeId", nodeId);
    if (role) params.append("role", role);
    if (clusterId !== null) params.append("clusterId", clusterId);
    const data = await api(`/api/runs/${runId}/nodes-static?${params.toString()}`);
    q("nodesStaticSummary").innerHTML = `<h3>Static Node Snapshot</h3>${renderKVTable({ total: data.total, page_count: data.items ? data.items.length : 0, node_filter: nodeId ?? "any", role_filter: role || "any", cluster_filter: clusterId ?? "any" })}`;
    renderTable("nodesStaticTable", data.items || []);
    renderPager("nodesStaticPager", "nodesStatic", data, loadNodesStatic);
  } catch (err) {
    renderError("nodesStaticTable", err);
  }
}

async function loadRunSummary() {
  const runId = getSelectedRun();
  if (!runId) return;
  renderLoading("runSummaryPanel");
  try {
    const data = await api(`/api/runs/${runId}/run-summary`);
    q("runSummaryPanel").innerHTML = data.item ? `<h3>Run Summary</h3>${renderKVTable(data.item)}` : '<div class="empty-state">No run summary available.</div>';
  } catch (err) {
    renderError("runSummaryPanel", err);
  }
}

function renderTopList(panelId, title, rows, fields) {
  const host = q(panelId);
  const body = (rows || []).map((r) => `<tr>${fields.map((f) => `<td>${escapeHtml(r[f] ?? "")}</td>`).join("")}</tr>`).join("");
  const head = fields.map((f) => `<th>${escapeHtml(f)}</th>`).join("");
  host.innerHTML = `<h3>${escapeHtml(title)}</h3><div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

async function loadNodeFinal(page = 1) {
  const runId = getSelectedRun();
  if (!runId) return;
  pageState.nodefinal = page;
  renderLoading("nodeFinalTable");
  try {
    const params = new URLSearchParams({ page: String(page), size: "30", sort: q("nodeSort").value, order: q("nodeOrder").value });
    const role = valueOrNull("nodeRoleFilter");
    const cluster = valueOrNull("nodeClusterFilter");
    if (role) params.append("role", role);
    if (cluster !== null) params.append("cluster_id", cluster);
    const data = await api(`/api/run/${runId}/node-final-summary?${params.toString()}`);
    renderTable("nodeFinalTable", data.items || []);
    renderPager("nodeFinalPager", "nodeFinal", data, loadNodeFinal);
    renderTopList("lowestResidualPanel", "Top 10 Lowest Residual", data.top_lowest_residual || [], ["node_id", "role", "cluster_id", "residual_j", "consumed_j", "final_status"]);
    renderTopList("highestConsumedPanel", "Top 10 Highest Consumed", data.top_highest_consumed || [], ["node_id", "role", "cluster_id", "consumed_j", "residual_j", "final_status"]);
    renderTable("roleSummaryPanel", data.role_summary || [], null, ["role", "nodes", "avg_residual_j", "avg_consumed_j", "min_residual_j", "max_consumed_j"]);
  } catch (err) {
    renderError("nodeFinalTable", err);
  }
}

async function loadRawTables() {
  const data = await api("/api/raw/tables");
  q("rawTableSelect").innerHTML = data.tables.map((t) => `<option value="${t}">${t}</option>`).join("");
}

async function loadRaw(page = 1) {
  const runId = getSelectedRun();
  if (!runId) return;
  pageState.raw = page;
  const params = new URLSearchParams({ table: q("rawTableSelect").value, runId: String(runId), page: String(page), size: "30", sort: q("rawSort").value, order: q("rawOrder").value });
  try {
    const data = await api(`/api/raw/table?${params.toString()}`);
    renderTable("rawTable", data.items || []);
    renderPager("rawPager", "raw", data, loadRaw);
  } catch (err) {
    renderError("rawTable", err);
  }
}

async function loadComparison() {
  const runCount = q("comparePrimaryRun")?.options?.length || 0;
  if (runCount <= 1) {
    renderPanelMessage("comparisonSummary", "Only one run is available. Import another run to compare.");
    q("comparisonMeta").innerHTML = "";
    q("comparisonConfig").innerHTML = "";
    q("comparisonResults").innerHTML = "";
    q("comparisonClusters").innerHTML = "";
    q("comparisonMainLegend").innerHTML = "";
    q("comparisonClusterLegend").innerHTML = "";
    drawGroupedBarChart("comparisonMainChart", [], [], []);
    drawGroupedBarChart("comparisonClusterChart", [], [], []);
    state.compareCsv = "";
    return;
  }

  const primaryId = Number(q("comparePrimaryRun").value || getSelectedRun());
  const secondaryId = Number(q("compareSecondaryRun").value || primaryId);
  if (!primaryId || !secondaryId) {
    renderPanelMessage("comparisonSummary", "Select two runs to compare.");
    return;
  }

  renderLoading("comparisonSummary", "Loading run comparison...");
  try {
    const [p, s] = await Promise.all([api(`/api/run/${primaryId}/overview`), api(`/api/run/${secondaryId}/overview`)]);

    renderCards("comparisonSummary", [
      { label: "Primary", value: primaryId },
      { label: "Comparison", value: secondaryId },
      { label: "Primary delivery %", value: fmt(p.result_summary.raw_delivery_pct, 2) },
      { label: "Comparison delivery %", value: fmt(s.result_summary.raw_delivery_pct, 2) },
    ]);

    const metaKeys = ["run_id", "experiment_version", "scenario_name", "started_at"];
    const configKeys = ["sim_time_s", "node_count", "cluster_count", "traffic_interval_s", "aggregation_interval_s", "failure_time_s", "recovery_delay_s", "recovery_enabled"];
    const resultKeys = ["raw_tx_total", "raw_rx_total", "raw_delivery_pct", "agg_tx_total", "agg_rx_total", "agg_per_raw_rx", "direct_agg_rx_total", "relayed_agg_rx_total", "relay_forward_total", "failed_chs", "recovered_clusters", "pending_raw_total", "avg_residual_j", "min_residual_j", "total_consumed_j"];
    const higherBetter = new Set(["raw_tx_total", "raw_rx_total", "raw_delivery_pct", "agg_tx_total", "agg_rx_total", "agg_per_raw_rx", "direct_agg_rx_total", "relayed_agg_rx_total", "relay_forward_total", "recovered_clusters", "avg_residual_j", "min_residual_j"]);
    const lowerBetter = new Set(["failed_chs", "pending_raw_total", "total_consumed_j"]);

    const buildRows = (keys, pObj, sObj, mode) => keys.map((k) => {
      const dir = mode === "result" ? (higherBetter.has(k) ? "higher-better" : (lowerBetter.has(k) ? "lower-better" : "neutral")) : "neutral";
      const delta = dir === "neutral" ? { text: "-", cls: "delta-neutral" } : compareDelta(pObj?.[k], sObj?.[k], dir);
      return { metric: k, primary: fmt(pObj?.[k]), secondary: fmt(sObj?.[k]), delta: delta.text, deltaCls: delta.cls };
    });

    q("comparisonMeta").innerHTML = comparisonTable("Run Metadata", buildRows(metaKeys, p.run_identity, s.run_identity, "neutral"));
    q("comparisonConfig").innerHTML = comparisonTable("Configuration", buildRows(configKeys, p.configuration_summary, s.configuration_summary, "neutral"));
    const resultRows = buildRows(resultKeys, p.result_summary, s.result_summary, "result");
    q("comparisonResults").innerHTML = comparisonTable("Result Summary", resultRows);

    const chartMetrics = ["raw_delivery_pct", "agg_rx_total", "failed_chs", "recovered_clusters", "avg_residual_j", "min_residual_j", "total_consumed_j"];
    drawGroupedBarChart(
      "comparisonMainChart",
      chartMetrics.map((m) => m.replace(/_/g, " ")),
      chartMetrics.map((m) => toNumber(p.result_summary[m])),
      chartMetrics.map((m) => toNumber(s.result_summary[m])),
      ["#2f8bbd", "#d17b21"],
    );
    q("comparisonMainLegend").innerHTML = `<span class="legend-item"><span class="legend-swatch" style="background:#2f8bbd"></span>Primary Run ${primaryId}</span><span class="legend-item"><span class="legend-swatch" style="background:#d17b21"></span>Comparison Run ${secondaryId}</span>`;

    const pMap = new Map((p.cluster_summary || []).map((c) => [Number(c.cluster_id), c]));
    const sMap = new Map((s.cluster_summary || []).map((c) => [Number(c.cluster_id), c]));
    const ids = [...new Set([...pMap.keys(), ...sMap.keys()])].sort((a, b) => a - b);

    drawGroupedBarChart(
      "comparisonClusterChart",
      ids.map((id) => `C${id}`),
      ids.map((id) => toNumber((pMap.get(id) || {}).cluster_consumed_j)),
      ids.map((id) => toNumber((sMap.get(id) || {}).cluster_consumed_j)),
      ["#19895a", "#b85858"],
    );
    q("comparisonClusterLegend").innerHTML = `<span class="legend-item"><span class="legend-swatch" style="background:#19895a"></span>Primary Cluster Consumed</span><span class="legend-item"><span class="legend-swatch" style="background:#b85858"></span>Comparison Cluster Consumed</span>`;

    const clusterRows = [];
    ids.forEach((id) => {
      const pc = pMap.get(id) || {};
      const sc = sMap.get(id) || {};
      const push = (metric, pv, sv, dir = "neutral") => {
        const d = dir === "neutral" ? { text: "-", cls: "delta-neutral" } : compareDelta(pv, sv, dir);
        clusterRows.push(`<tr><td>C${id} / ${metric}</td><td>${fmt(pv)}</td><td>${fmt(sv)}</td><td><span class="${d.cls}">${d.text}</span></td></tr>`);
      };
      push("status", pc.status, sc.status);
      push("current_ch", pc.current_ch_id, sc.current_ch_id);
      push("mode", pc.mode, sc.mode);
      push("next_hop", pc.next_hop, sc.next_hop);
      push("raw_rx", pc.raw_rx_cum, sc.raw_rx_cum, "higher-better");
      push("pending_raw", pc.pending_raw, sc.pending_raw, "lower-better");
      push("agg_tx", pc.agg_tx_cum, sc.agg_tx_cum, "higher-better");
      push("relay_forwarded", pc.relay_fwd_cum, sc.relay_fwd_cum, "higher-better");
      push("ch_residual_j", pc.ch_res_j, sc.ch_res_j, "higher-better");
      push("avg_member_residual_j", pc.avg_mem_res_j, sc.avg_mem_res_j, "higher-better");
      push("consumed_j", pc.cluster_consumed_j, sc.cluster_consumed_j, "lower-better");
    });

    q("comparisonClusters").innerHTML = `<h3>Cluster-Level Comparison</h3><div class="table-wrap"><table class="compare-table"><thead><tr><th>Metric</th><th>Primary</th><th>Comparison</th><th>Delta (P-C)</th></tr></thead><tbody>${clusterRows.join("") || "<tr><td colspan='4'>No cluster data</td></tr>"}</tbody></table></div>`;

    const csvLines = ["section,metric,primary,comparison,delta"];
    resultRows.forEach((r) => csvLines.push(`result,${r.metric},${r.primary},${r.secondary},${r.delta}`));
    state.compareCsv = csvLines.join("\n");
  } catch (err) {
    renderError("comparisonSummary", err);
  }
}

function makeReplayMarkerItem(key, time) {
  const entry = replayMarkerStyles[key] || [key, "aggregate"];
  return { key, label: entry[0], css: entry[1], time: toNumber(time, NaN) };
}

function computeReplayMarkers(events) {
  const list = (events || []).slice().sort((a, b) => toNumber(a.sim_time_s) - toNumber(b.sim_time_s) || toNumber(a.event_id) - toNumber(b.event_id));
  const firstBy = (pred) => {
    const x = list.find(pred);
    return x ? toNumber(x.sim_time_s, null) : null;
  };
  return {
    start: 0,
    firstAgg: firstBy((e) => String(e.category || "").toLowerCase() === "aggregate"),
    firstFailure: firstBy((e) => String(e.category || "").toLowerCase() === "failure"),
    recoveryStart: firstBy((e) => String(e.category || "").toLowerCase() === "recovery"),
    recoveryApplied: firstBy((e) => /applied|recovered/i.test(`${e.event_type || ""} ${e.message || ""}`)),
    firstRecoveredRaw: firstBy((e) => /raw/i.test(`${e.event_type || ""} ${e.message || ""}`) && /recover/i.test(`${e.event_type || ""} ${e.message || ""}`)),
    firstRecoveredAgg: firstBy((e) => String(e.category || "").toLowerCase() === "aggregate" && /recover/i.test(`${e.event_type || ""} ${e.message || ""}`)),
    end: state.replayMaxTime,
  };
}

async function loadReplayMarkers() {
  const runId = getSelectedRun();
  if (!runId) return null;
  if (state.replayMarkers && state.replayMarkersRunId === runId) return state.replayMarkers;
  const data = await api(`/api/run/${runId}/events?sort=sim_time_s&order=asc&page=1&size=1500`);
  state.replayMarkers = computeReplayMarkers(data.items || []);
  state.replayMarkersRunId = runId;
  return state.replayMarkers;
}

function renderReplayBarMarkers(markers) {
  const host = q("replayBarMarkers");
  const items = [
    makeReplayMarkerItem("firstAgg", markers.firstAgg),
    makeReplayMarkerItem("firstFailure", markers.firstFailure),
    makeReplayMarkerItem("recoveryStart", markers.recoveryStart),
    makeReplayMarkerItem("recoveryApplied", markers.recoveryApplied),
    makeReplayMarkerItem("firstRecoveredRaw", markers.firstRecoveredRaw),
    makeReplayMarkerItem("firstRecoveredAgg", markers.firstRecoveredAgg),
    makeReplayMarkerItem("end", markers.end),
  ].filter((x) => Number.isFinite(x.time));

  const markerLanes = new Map();

  host.innerHTML = items.map((x) => {
    const pct = (100 * x.time) / Math.max(state.replayMaxTime, 1);
    const key = String(Number(x.time).toFixed(2));
    const lane = markerLanes.get(key) || 0;
    markerLanes.set(key, lane + 1);
    return `<span class="replay-marker ${x.css}" data-time="${x.time}" title="${escapeHtml(x.label)} @ ${fmt(x.time, 2)}s" style="left:${pct}%; --marker-level:${lane}; --marker-x-offset:${lane * 7}px"></span>`;
  }).join("");
  host.querySelectorAll(".replay-marker").forEach((m) => {
    m.onclick = () => jumpReplay(Number(m.getAttribute("data-time")));
  });
}

function setReplayBarPosition(t) {
  const pct = 100 * clamp(t / Math.max(state.replayMaxTime, 1), 0, 1);
  q("replayBarFill").style.width = `${pct}%`;
  q("replayBarCursor").style.left = `${pct}%`;
  q("replayBar").setAttribute("aria-valuenow", String(fmt(t, 2)));
}

function replayTopologySvg(snapshot) {
  const clusters = snapshot.clusters || [];
  const width = 1200;
  const height = Math.max(520, 260 + Math.ceil(clusters.length / 4) * 190);
  const cols = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(Math.max(clusters.length, 1)))));
  const cardW = 245;
  const cardH = 150;
  const xGap = clusters.length <= 1 ? 0 : Math.max(20, (width - 120 - cols * cardW) / Math.max(cols - 1, 1));
  const yStart = 170;
  const yGap = 48;
  const bs = { x: width / 2, y: 82 };

  const positions = new Map();
  clusters.forEach((c, idx) => {
    const row = Math.floor(idx / cols);
    const col = idx % cols;
    const x = 60 + col * (cardW + xGap);
    const y = yStart + row * (cardH + yGap);
    positions.set(Number(c.cluster_id), { x, y, centerX: x + cardW / 2, centerY: y + cardH / 2 });
  });

  const edges = [];
  const nodeGroups = [];

  clusters.forEach((c) => {
    const pos = positions.get(Number(c.cluster_id));
    const status = statusClassForCluster(c.status);
    const prevStatus = state.replayPrevClusterStatus[c.cluster_id];
    const flashCls = prevStatus && prevStatus !== status ? "node-flash" : "";

    const hopChId = parseNextHopId(c.next_hop);
    const hopTarget = hopChId !== null
      ? [...positions.values()].find((p, idx) => Number(clusters[idx].current_ch_id) === hopChId)
      : null;
    const targetX = hopTarget ? hopTarget.centerX : bs.x;
    const targetY = hopTarget ? hopTarget.y : bs.y + 28;
    const activeCls = Number(c.original_ch_id) !== Number(c.current_ch_id) ? "route-active" : "";

    edges.push(`<line x1="${pos.centerX}" y1="${pos.y + 34}" x2="${targetX}" y2="${targetY}" class="replay-edge ${activeCls}"></line>`);

    const members = Math.max(0, Number(c.members_count || 0));
    const memberCount = Math.min(members, 6);
    const memberDots = [];
    for (let i = 0; i < memberCount; i += 1) {
      const angle = (Math.PI * (i + 1)) / (memberCount + 1);
      const mx = pos.centerX + Math.cos(angle) * 50;
      const my = pos.centerY + 28 + Math.sin(angle) * 28;
      memberDots.push(`<line x1="${mx}" y1="${my}" x2="${pos.centerX}" y2="${pos.centerY - 6}" stroke="rgba(70,110,140,0.35)" stroke-width="1"></line>`);
      memberDots.push(`<circle class="state-member" cx="${mx}" cy="${my}" r="6"></circle>`);
    }

    const ghost = Number(c.original_ch_id) !== Number(c.current_ch_id)
      ? `<circle cx="${pos.centerX - 30}" cy="${pos.centerY - 22}" r="12" fill="none" stroke="#a36464" stroke-dasharray="4 3"></circle>
         <text x="${pos.centerX - 30}" y="${pos.centerY - 18}" text-anchor="middle" font-size="10" fill="#8d4545">${escapeHtml(c.original_ch_id)}</text>
         <line x1="${pos.centerX - 18}" y1="${pos.centerY - 16}" x2="${pos.centerX - 4}" y2="${pos.centerY - 11}" class="replay-edge route-active"></line>`
      : "";

    nodeGroups.push(`
      <g>
        <rect class="cluster-shell" x="${pos.x}" y="${pos.y}" width="${cardW}" height="${cardH}" rx="16" ry="16" fill="rgba(255,255,255,0.96)" stroke="${status === "failed" ? "#d94a4a" : status === "recovering" ? "#f2a74a" : status === "recovered" ? "#c8a323" : "#47a16d"}" stroke-width="3"></rect>
        <text x="${pos.centerX}" y="${pos.y + 18}" text-anchor="middle" class="replay-node-label">Cluster ${escapeHtml(c.cluster_id)} | ${escapeHtml(c.status || "normal")}</text>
        <text x="${pos.centerX}" y="${pos.y + 34}" text-anchor="middle" class="replay-node-label">CH ${escapeHtml(c.current_ch_id)} | next: ${escapeHtml(c.next_hop || "BS")}</text>
        ${memberDots.join("")}
        ${ghost}
        <circle class="state-${status} ${flashCls}" cx="${pos.centerX}" cy="${pos.centerY - 10}" r="22"></circle>
        <text x="${pos.centerX}" y="${pos.centerY - 5}" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">CH</text>
        <text x="${pos.centerX}" y="${pos.y + cardH - 10}" text-anchor="middle" class="replay-node-label">pending: ${escapeHtml(c.pending_raw)} | agg: ${escapeHtml(c.agg_tx_cum)} | relay: ${escapeHtml(c.relay_fwd_cum)}</text>
      </g>`);

    state.replayPrevClusterStatus[c.cluster_id] = status;
  });

  return `
    <svg class="topology-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMin meet">
      <defs>
        <marker id="arrowHead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="rgba(35,63,78,0.45)"></path>
        </marker>
      </defs>
      <circle cx="${bs.x}" cy="${bs.y}" r="30" class="state-bs"></circle>
      <text x="${bs.x}" y="${bs.y + 5}" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">BS</text>
      <text x="${bs.x}" y="${bs.y + 50}" text-anchor="middle" class="replay-node-label">Base Station</text>
      ${edges.join("")}
      ${nodeGroups.join("")}
    </svg>
    <div class="legend-row">
      <span class="legend-item"><span class="legend-swatch" style="background:#47a16d"></span>Normal</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#d94a4a"></span>Failed</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#f2a74a"></span>Recovering</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#c8a323"></span>Recovered</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#2f8bbd"></span>Relay/Route highlight</span>
    </div>`;
}

function renderReplayClusterState(clusters) {
  const rows = (clusters || []).map((c) => ({
    cluster_id: c.cluster_id,
    status: c.status,
    current_ch: c.current_ch_id,
    mode: c.mode,
    next_hop: c.next_hop,
    pending_raw: c.pending_raw,
    agg_tx: c.agg_tx_cum,
    relay_forwarded: c.relay_fwd_cum,
    ch_residual_j: c.ch_res_j,
  }));
  q("replayClusterStatePanel").innerHTML = "<h3>Cluster Detail Panel</h3>";
  renderTable("replayClusterStatePanel", rows, null, ["cluster_id", "status", "current_ch", "mode", "next_hop", "pending_raw", "agg_tx", "relay_forwarded", "ch_residual_j"]);
}

function renderReplayEvents(events, selectedTime) {
  const host = q("replayEventPanel");
  if (!events || !events.length) {
    host.innerHTML = "<h3>Nearby Events</h3><div class='empty-state'>No events near selected time.</div>";
    return;
  }
  const sorted = [...events].sort((a, b) => Math.abs(toNumber(a.sim_time_s) - selectedTime) - Math.abs(toNumber(b.sim_time_s) - selectedTime) || toNumber(a.sim_time_s) - toNumber(b.sim_time_s)).slice(0, 40);
  const nearest = sorted[0]?.event_id;
  host.innerHTML = `<h3>Nearby Events</h3><div class="timeline-strip">${sorted.map((e) => `<div class="event-chip ${categoryClass(e.category)} ${e.event_id === nearest ? "nearest-event" : ""}"><span class="time">t=${fmt(e.sim_time_s, 2)}</span><span class="type">${escapeHtml(e.event_type || "event")}</span><span class="msg">${escapeHtml(e.message || "")}</span></div>`).join("")}</div>`;
}

function renderReplaySummary(snapshot) {
  const g = snapshot.global || {};
  const clusters = snapshot.clusters || [];
  const counts = formatStatusCounts(clusters);
  const context = counts.failed > 0 ? "Failure handling" : (counts.recovered > 0 ? "Recovered operation" : "Normal operation");
  renderCards("replaySummary", [
    { label: "Requested", value: fmt(snapshot.requested_time_s ?? snapshot.requested_time, 2) },
    { label: "Selected Snapshot", value: fmt(snapshot.selected_time_s ?? snapshot.selected_time, 2) },
    { label: "Phase", value: context },
    { label: "Nearby Events", value: (snapshot.events || []).length },
    { label: "Normal", value: counts.normal },
    { label: "Failed", value: counts.failed },
    { label: "Recovering", value: counts.recovering },
    { label: "Recovered", value: counts.recovered },
    { label: "Pending Raw", value: g.pending_raw_total ?? clusters.reduce((s, c) => s + toNumber(c.pending_raw), 0) },
    { label: "Raw RX", value: g.raw_rx_cum ?? 0 },
    { label: "Agg RX", value: g.agg_rx_cum ?? 0 },
    { label: "Active Path", value: buildPathSummary(clusters) },
  ]);
}

async function fetchReplaySnapshot(runId, time, window = 2) {
  const key = `${runId}:${fmt(time, 2)}:${window}`;
  if (state.snapshotCache.has(key)) return state.snapshotCache.get(key);
  const data = await api(`/api/run/${runId}/replay-snapshot?time=${encodeURIComponent(time)}&window=${window}`);
  state.snapshotCache.set(key, data);
  if (state.snapshotCache.size > 500) {
    const firstKey = state.snapshotCache.keys().next().value;
    state.snapshotCache.delete(firstKey);
  }
  return data;
}

async function loadReplaySnapshot(time = state.replayCurrentTime || 0, options = {}) {
  const runId = getSelectedRun();
  if (!runId) return;

  const requested = clamp(toNumber(time, 0), 0, state.replayMaxTime);
  state.replayCurrentTime = requested;
  if (!options.skipUi) {
    q("replayTimeRange").value = String(requested);
    q("replayExactTime").value = String(requested);
    q("replayTimeLabel").textContent = `t=${fmt(requested, 2)} s`;
    setReplayBarPosition(requested);
  }

  if (state.replayFetchInFlight) return;
  state.replayFetchInFlight = true;
  try {
    const markers = await loadReplayMarkers();
    renderReplayBarMarkers(markers);
    const data = await fetchReplaySnapshot(runId, requested, 2);
    state.replayCurrentTime = requested;
    q("replayTimeRange").value = String(requested);
    q("replayExactTime").value = String(requested);
    q("replayTimeLabel").textContent = `t=${fmt(requested, 2)} s`;
    setReplayBarPosition(requested);
    renderReplaySummary(data);
    q("replayTopology").innerHTML = replayTopologySvg(data);
    renderReplayClusterState(data.clusters || []);
    renderReplayEvents(data.events || [], selected);
    q("snapshotPanel").innerHTML = `<h3>Raw Snapshot</h3><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
  } catch (err) {
    renderError("replaySummary", err);
  } finally {
    state.replayFetchInFlight = false;
  }
}

function setReplayTime(time, immediate = false) {
  const t = clamp(toNumber(time, 0), 0, state.replayMaxTime);
  state.replayCurrentTime = t;
  q("replayTimeRange").value = String(t);
  q("replayExactTime").value = String(t);
  q("replayTimeLabel").textContent = `t=${fmt(t, 2)} s`;
  setReplayBarPosition(t);

  if (!immediate) {
    if (state.replaySliderTimer) clearTimeout(state.replaySliderTimer);
    state.replaySliderTimer = setTimeout(() => loadReplaySnapshot(t, { skipUi: true }).catch(console.error), 180);
  } else {
    loadReplaySnapshot(t, { skipUi: true }).catch(console.error);
  }
}

function stopReplayPlayback() {
  if (state.replayRafId) cancelAnimationFrame(state.replayRafId);
  state.replayRafId = null;
  state.replayLastFrameTs = null;
  state.replayPlaying = false;
  q("replayPlayBtn").textContent = "Play";
}

function replayFrame(ts) {
  if (!state.replayPlaying) return;
  if (state.replayLastFrameTs === null) state.replayLastFrameTs = ts;
  const dt = (ts - state.replayLastFrameTs) / 1000;
  state.replayLastFrameTs = ts;

  const nextTime = state.replayCurrentTime + dt * state.replaySpeed;
  if (nextTime >= state.replayMaxTime) {
    setReplayTime(state.replayMaxTime, true);
    stopReplayPlayback();
    return;
  }

  state.replayCurrentTime = nextTime;
  q("replayTimeRange").value = String(nextTime);
  q("replayExactTime").value = String(nextTime);
  q("replayTimeLabel").textContent = `t=${fmt(nextTime, 2)} s`;
  setReplayBarPosition(nextTime);

  if (ts - state.replayLastFetchTs > 260) {
    state.replayLastFetchTs = ts;
    loadReplaySnapshot(nextTime, { skipUi: true }).catch(console.error);
  }
  state.replayRafId = requestAnimationFrame(replayFrame);
}

function startReplayPlayback() {
  stopReplayPlayback();
  state.replayPlaying = true;
  q("replayPlayBtn").textContent = "Pause";
  state.replayRafId = requestAnimationFrame(replayFrame);
}

function jumpReplay(time) {
  stopReplayPlayback();
  setReplayTime(time, true);
}

function bindReplayTimelineBar() {
  const bar = q("replayBar");
  bar.onclick = (ev) => {
    const rect = bar.getBoundingClientRect();
    const pct = clamp((ev.clientX - rect.left) / Math.max(rect.width, 1), 0, 1);
    jumpReplay(pct * state.replayMaxTime);
  };
  bar.onkeydown = (ev) => {
    if (ev.key === "ArrowLeft") jumpReplay(state.replayCurrentTime - 0.5);
    if (ev.key === "ArrowRight") jumpReplay(state.replayCurrentTime + 0.5);
  };
}

const analyticsMetricDefs = [
  ["raw_delivery_pct", "Raw Delivery %", "#2f8bbd"],
  ["agg_rx_total", "Agg RX Total", "#0f9d8d"],
  ["total_consumed_j", "Total Consumed J", "#d17b21"],
  ["min_residual_j", "Min Residual J", "#79b43c"],
  ["recovered_clusters", "Recovered Clusters", "#c8a323"],
];

function getAnalyticsFilters() {
  return {
    experiment_version: valueOrNull("analyticsFilterExperimentVersion"),
    scenario_name: valueOrNull("analyticsFilterScenarioName"),
    recovery_enabled: valueOrNull("analyticsFilterRecoveryEnabled"),
    failure_time_s: valueOrNull("analyticsFilterFailureTime"),
    recovery_delay_s: valueOrNull("analyticsFilterRecoveryDelay"),
    sim_time_s: valueOrNull("analyticsFilterSimTime"),
    node_count: valueOrNull("analyticsFilterNodeCount"),
    cluster_count: valueOrNull("analyticsFilterClusterCount"),
    started_from: valueOrNull("analyticsFilterStartedFrom"),
    started_to: valueOrNull("analyticsFilterStartedTo"),
  };
}

function getAnalyticsSelectionParams() {
  const selected = idsCsv(state.analyticsSelectedRunIds);
  return selected ? { selected_run_ids: selected } : {};
}

async function fetchAllFilteredAnalyticsRunIds() {
  const filters = getAnalyticsFilters();
  const sort = q("analyticsSortBy").value;
  const order = q("analyticsSortOrder").value;
  const size = 500;
  let page = 1;
  let pages = 1;
  const ids = new Set();
  while (page <= pages) {
    const qs = queryString({ ...filters, sort, order, page, size });
    const data = await api(`/api/analytics/runs?${qs}`);
    (data.items || []).forEach((r) => ids.add(Number(r.run_id)));
    pages = Number(data.pages || 1);
    page += 1;
  }
  return ids;
}

function updateAnalyticsSelectionInfo(totalFiltered = null) {
  const selectedCount = state.analyticsSelectedRunIds.size;
  const suffix = totalFiltered !== null ? ` | filtered: ${totalFiltered}` : "";
  q("analyticsSelectionInfo").textContent = `${selectedCount} selected${suffix}`;
}

function renderAnalyticsRunsTable(rows, totalFiltered) {
  const host = q("analyticsRunsTable");
  if (!rows || rows.length === 0) {
    host.innerHTML = "<h3>Run Explorer</h3><div class='empty-state'>No runs match current filters.</div>";
    updateAnalyticsSelectionInfo(totalFiltered || 0);
    return;
  }

  const tableRows = rows.map((r) => {
    const runId = Number(r.run_id);
    const checked = state.analyticsSelectedRunIds.has(runId) ? "checked" : "";
    const tags = (r.tags || []).map((t) => `<span class="analytics-tag">${escapeHtml(t)}</span>`).join("");
    return `
      <tr>
        <td><input type="checkbox" class="analytics-row-select" data-run-id="${runId}" ${checked} /></td>
        <td>
          <div class="analytics-table-run">
            <span><strong>${runId}</strong></span>
            <span>${tags || '<span class="analytics-inline-note">no tags</span>'}</span>
          </div>
        </td>
        <td>${escapeHtml(r.experiment_version)}</td>
        <td>${escapeHtml(r.started_at)}</td>
        <td>${escapeHtml(r.node_count)}</td>
        <td>${escapeHtml(r.cluster_count)}</td>
        <td>${escapeHtml(r.recovery_enabled)}</td>
        <td>${escapeHtml(r.failure_time_s)}</td>
        <td>${escapeHtml(r.recovery_delay_s)}</td>
        <td>${escapeHtml(fmt(r.raw_delivery_pct, 3))}</td>
        <td>${escapeHtml(fmt(r.agg_rx_total, 3))}</td>
        <td>${escapeHtml(fmt(r.total_consumed_j, 3))}</td>
        <td>${escapeHtml(fmt(r.min_residual_j, 3))}</td>
        <td>${escapeHtml(fmt(r.recovered_clusters, 3))}</td>
      </tr>`;
  }).join("");

  host.innerHTML = `
    <h3>Run Explorer</h3>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>select</th>
            <th>run_id + tags</th>
            <th>experiment_version</th>
            <th>started_at</th>
            <th>node_count</th>
            <th>cluster_count</th>
            <th>recovery_enabled</th>
            <th>failure_time_s</th>
            <th>recovery_delay_s</th>
            <th>raw_delivery_pct</th>
            <th>agg_rx_total</th>
            <th>total_consumed_j</th>
            <th>min_residual_j</th>
            <th>recovered_clusters</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>`;

  host.querySelectorAll(".analytics-row-select").forEach((cb) => {
    cb.onchange = () => {
      const runId = Number(cb.getAttribute("data-run-id"));
      if (cb.checked) state.analyticsSelectedRunIds.add(runId);
      else state.analyticsSelectedRunIds.delete(runId);
      updateAnalyticsSelectionInfo(totalFiltered || null);
      loadAnalyticsSummary().catch(console.error);
      loadAnalyticsCharts().catch(console.error);
    };
  });

  updateAnalyticsSelectionInfo(totalFiltered || null);
}

function renderAnalyticsHighlights(summary) {
  const host = q("analyticsHighlights");
  const h = summary?.highlights || {};
  const cards = [
    ["Best Delivery Run", h.best_delivery_run],
    ["Best Energy Efficiency", h.best_energy_efficiency_run],
    ["Worst Min Residual Run", h.worst_min_residual_run],
    ["Most Recovered Clusters", h.most_recovered_clusters_run],
    ["Highest Consumed Energy", h.highest_consumed_energy_run],
  ];
  host.innerHTML = `<h3>Best/Worst Highlights</h3><div class="analytics-highlight-grid">${cards.map(([label, v]) => {
    if (!v) return `<div class="analytics-highlight-item"><div class="k">${escapeHtml(label)}</div><div class="v">-</div></div>`;
    const val = v.delivery_per_j !== undefined ? `score=${fmt(v.delivery_per_j, 6)}` : fmt(v.value, 3);
    return `<div class="analytics-highlight-item"><div class="k">${escapeHtml(label)}</div><div class="v">Run ${escapeHtml(v.run_id)} | ${escapeHtml(val)}</div></div>`;
  }).join("")}</div>`;
}

async function loadAnalyticsRuns(page = 1) {
  pageState.analytics = page;
  const filters = getAnalyticsFilters();
  const sort = q("analyticsSortBy").value;
  const order = q("analyticsSortOrder").value;
  state.analyticsLastFilters = { ...filters, sort, order };
  renderLoading("analyticsRunsTable");
  try {
    const qs = queryString({ ...filters, sort, order, page, size: 30 });
    const data = await api(`/api/analytics/runs?${qs}`);
    const rows = data.items || [];
    state.analyticsCachedRows = rows;
    state.analyticsRunIdsByPage = rows.map((r) => Number(r.run_id));
    renderAnalyticsRunsTable(rows, Number(data.total || 0));
    renderPager("analyticsPager", "analytics", data, loadAnalyticsRuns);
  } catch (err) {
    renderError("analyticsRunsTable", err);
  }
}

async function loadAnalyticsSummary() {
  const filters = getAnalyticsFilters();
  const active = { ...filters, ...getAnalyticsSelectionParams() };
  renderLoading("analyticsSummaryCards");
  try {
    const qs = queryString(active);
    const summary = await api(`/api/analytics/summary?${qs}`);
    const avg = summary.averages || {};
    renderCards("analyticsSummaryCards", [
      { label: "Filtered Runs", value: summary.filtered_runs },
      { label: "Avg Raw Delivery %", value: fmt(avg.raw_delivery_pct, 3) },
      { label: "Avg Agg RX Total", value: fmt(avg.agg_rx_total, 3) },
      { label: "Avg Total Consumed J", value: fmt(avg.total_consumed_j, 3) },
      { label: "Avg Min Residual J", value: fmt(avg.min_residual_j, 3) },
      { label: "Avg Recovered Clusters", value: fmt(avg.recovered_clusters, 3) },
      { label: "Recovery Success %", value: fmt(summary.recovery_success_rate_pct, 3) },
      { label: "Avg Failed CHs", value: fmt(avg.failed_chs, 3) },
    ]);
    renderAnalyticsHighlights(summary);
  } catch (err) {
    renderError("analyticsSummaryCards", err);
  }
}

async function loadAnalyticsCharts() {
  const filters = getAnalyticsFilters();
  const groupBy = valueOrNull("analyticsGroupBy") || "";
  state.analyticsLastGroupBy = groupBy;
  const active = { ...filters, ...getAnalyticsSelectionParams(), group_by: groupBy || null };
  try {
    const qs = queryString(active);
    const data = await api(`/api/analytics/charts?${qs}`);

    const byRun = data.by_run || {};
    const runRows = (byRun.run_ids || []).map((runId, idx) => ({
      run_idx: idx + 1,
      raw_delivery_pct: byRun.raw_delivery_pct?.[idx] || 0,
      agg_rx_total: byRun.agg_rx_total?.[idx] || 0,
      total_consumed_j: byRun.total_consumed_j?.[idx] || 0,
      min_residual_j: byRun.min_residual_j?.[idx] || 0,
      recovered_clusters: byRun.recovered_clusters?.[idx] || 0,
      run_label: `Run ${runId}`,
    }));
    drawMultiSeriesChart("analyticsBatchChart", runRows, "run_idx", analyticsMetricDefs.map((m) => m[0]), analyticsMetricDefs, "analyticsBatchLegend", "analyticsBatchHoverStats");

    const grouped = data.grouped || [];
    drawGroupedBarChart(
      "analyticsGroupedChart",
      grouped.map((g) => String(g.group)),
      grouped.map((g) => toNumber(g.avg_raw_delivery_pct)),
      grouped.map((g) => toNumber(g.avg_total_consumed_j)),
      ["#2f8bbd", "#d17b21"],
    );
    q("analyticsGroupedLegend").innerHTML = grouped.length
      ? '<span class="legend-item"><span class="legend-swatch" style="background:#2f8bbd"></span>avg_raw_delivery_pct</span><span class="legend-item"><span class="legend-swatch" style="background:#d17b21"></span>avg_total_consumed_j</span>'
      : '<span class="analytics-inline-note">No grouped results. Choose a Group By option.</span>';
  } catch (err) {
    renderPanelMessage("analyticsBatchLegend", `Error loading charts: ${String(err)}`);
  }
}

function analyticsExportUrl(path) {
  const filters = getAnalyticsFilters();
  const groupBy = valueOrNull("analyticsGroupBy") || null;
  const params = { ...filters, ...getAnalyticsSelectionParams(), group_by: groupBy };
  const qs = queryString(params);
  return `${apiBase}${path}${qs ? `?${qs}` : ""}`;
}

async function loadAnalyticsTab() {
  await loadAnalyticsRuns(pageState.analytics);
  await loadAnalyticsSummary();
  await loadAnalyticsCharts();
}

async function loadReplayTab() {
  await loadReplaySnapshot(state.replayCurrentTime || 0);
}

async function refreshCurrentTab() {
  switch (state.currentTab) {
    case "overview": await loadOverview(); break;
    case "global": await loadGlobal(); break;
    case "clusters": await loadClusters(); break;
    case "events": await loadEvents(pageState.events); break;
    case "nodesstatic": await loadNodesStatic(pageState.nodesstatic); break;
    case "runsummary": await loadRunSummary(); break;
    case "nodefinal": await loadNodeFinal(pageState.nodefinal); break;
    case "raw": await loadRaw(pageState.raw); break;
    case "comparison": await loadComparison(); break;
    case "analytics": await loadAnalyticsTab(); break;
    case "replay": await loadReplayTab(); break;
    default: await loadOverview();
  }
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.onclick = async () => {
      setActiveTab(btn.dataset.tab);
      await refreshCurrentTab();
    };
  });
}

function setupAutoRefresh() {
  const toggle = q("autoRefreshToggle");
  toggle.checked = localStorage.getItem(LS_AUTO_REFRESH) === "1";
  toggle.onchange = () => {
    localStorage.setItem(LS_AUTO_REFRESH, toggle.checked ? "1" : "0");
    if (state.refreshTimer) clearInterval(state.refreshTimer);
    if (toggle.checked) state.refreshTimer = setInterval(() => refreshCurrentTab().catch(console.error), 5000);
  };
  if (toggle.checked) state.refreshTimer = setInterval(() => refreshCurrentTab().catch(console.error), 5000);
}

function setReplayButtons() {
  const jumpToMarker = async (key) => {
    if (!state.replayMarkers || state.replayMarkersRunId !== getSelectedRun()) {
      try {
        await loadReplayMarkers();
      } catch {
        return;
      }
    }
    const markerTime = key === "start" ? 0 : toNumber(state.replayMarkers?.[key], NaN);
    if (Number.isFinite(markerTime)) jumpReplay(markerTime);
  };

  q("replayPlayBtn").onclick = () => (state.replayPlaying ? stopReplayPlayback() : startReplayPlayback());
  q("replayBackBtn").onclick = () => jumpReplay(state.replayCurrentTime - 0.5);
  q("replayForwardBtn").onclick = () => jumpReplay(state.replayCurrentTime + 0.5);
  q("replaySpeedSelect").onchange = (e) => {
    state.replaySpeed = Math.max(0.25, toNumber(e.target.value, 1));
  };
  q("replayTimeRange").oninput = (e) => {
    stopReplayPlayback();
    setReplayTime(Number(e.target.value), false);
  };
  q("replayExactJumpBtn").onclick = () => jumpReplay(Number(q("replayExactTime").value));
  q("replayJumpStartBtn").onclick = () => jumpToMarker("start");
  q("replayJumpFirstAggBtn").onclick = () => jumpToMarker("firstAgg");
  q("replayJumpFailureBtn").onclick = () => jumpToMarker("firstFailure");
  q("replayJumpRecoveryStartBtn").onclick = () => jumpToMarker("recoveryStart");
  q("replayJumpRecoveryAppliedBtn").onclick = () => jumpToMarker("recoveryApplied");
  q("replayJumpRecoveredRawBtn").onclick = () => jumpToMarker("firstRecoveredRaw");
  q("replayJumpRecoveredAggBtn").onclick = () => jumpToMarker("firstRecoveredAgg");
  q("replayJumpEndBtn").onclick = () => jumpToMarker("end");
  bindReplayTimelineBar();
}

function bindActions() {
  q("refreshRunsBtn").onclick = async () => {
    await loadRuns();
    await refreshCurrentTab();
  };
  q("runSelect").onchange = async (e) => {
    saveRunSelection(Number(e.target.value));
    state.replayMarkers = null;
    state.replayMarkersRunId = null;
    state.snapshotCache.clear();
    state.replayCurrentTime = 0;
    q("comparePrimaryRun").value = String(state.selectedRunId);
    await refreshCurrentTab();
  };

  q("comparePrimaryRun").onchange = () => {
    state.selectedRunId = Number(q("comparePrimaryRun").value);
    q("runSelect").value = String(state.selectedRunId);
  };
  q("compareSecondaryRun").onchange = () => {
    state.compareSecondaryRunId = Number(q("compareSecondaryRun").value);
  };
  q("compareApplyBtn").onclick = () => loadComparison();
  q("comparisonExportCsvBtn").onclick = () => {
    if (!state.compareCsv) return;
    const blob = new Blob([state.compareCsv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `run-comparison-${q("comparePrimaryRun").value || "p"}-vs-${q("compareSecondaryRun").value || "s"}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  q("globalApplyBtn").onclick = () => loadGlobal();
  q("clusterApplyBtn").onclick = () => loadClusters();
  q("eventApplyBtn").onclick = () => loadEvents(1);
  q("nodesStaticApplyBtn").onclick = () => loadNodesStatic(1);
  q("nodeApplyBtn").onclick = () => loadNodeFinal(1);
  q("rawApplyBtn").onclick = () => loadRaw(1);

  q("analyticsApplyBtn").onclick = async () => {
    pageState.analytics = 1;
    await loadAnalyticsTab();
  };
  q("analyticsResetBtn").onclick = async () => {
    [
      "analyticsFilterExperimentVersion",
      "analyticsFilterScenarioName",
      "analyticsFilterRecoveryEnabled",
      "analyticsFilterFailureTime",
      "analyticsFilterRecoveryDelay",
      "analyticsFilterSimTime",
      "analyticsFilterNodeCount",
      "analyticsFilterClusterCount",
      "analyticsFilterStartedFrom",
      "analyticsFilterStartedTo",
      "analyticsGroupBy",
    ].forEach((id) => {
      const el = q(id);
      if (el) el.value = "";
    });
    q("analyticsSortBy").value = "newest";
    q("analyticsSortOrder").value = "desc";
    state.analyticsSelectedRunIds.clear();
    q("analyticsSelectAllVisible").checked = false;
    pageState.analytics = 1;
    await loadAnalyticsTab();
  };

  q("analyticsSelectAllVisible").onchange = async (e) => {
    if (e.target.checked) {
      const all = await fetchAllFilteredAnalyticsRunIds();
      state.analyticsSelectedRunIds = all;
    } else {
      state.analyticsSelectedRunIds.clear();
    }
    await loadAnalyticsRuns(pageState.analytics);
    await loadAnalyticsSummary();
    await loadAnalyticsCharts();
  };

  q("analyticsExportRunsCsvBtn").onclick = () => triggerDownload(analyticsExportUrl("/api/analytics/export/runs.csv"));
  q("analyticsExportSummaryCsvBtn").onclick = () => triggerDownload(analyticsExportUrl("/api/analytics/export/summary.csv"));
  q("analyticsExportSelectedJsonBtn").onclick = () => triggerDownload(analyticsExportUrl("/api/analytics/export/selected.json"));
  q("analyticsExportClusterCsvBtn").onclick = async () => {
    if (state.analyticsSelectedRunIds.size === 0) {
      const all = await fetchAllFilteredAnalyticsRunIds();
      state.analyticsSelectedRunIds = all;
      await loadAnalyticsRuns(pageState.analytics);
    }
    triggerDownload(analyticsExportUrl("/api/analytics/export/cluster-summary.csv"));
  };
}

async function initialize() {
  try {
    setupTabs();
    setupAutoRefresh();
    bindActions();
    setReplayButtons();

    setupGlobalPreset();
    initMetricChecklist("globalMetricChecklist", globalMetricDefs, state.globalSelectedMetrics, () => loadGlobal());
    initMetricChecklist("clusterMetricChecklist", clusterMetricDefs, state.clusterSelectedMetrics, () => loadClusters());

    const savedTab = localStorage.getItem(LS_CURRENT_TAB);
    setActiveTab(savedTab || "overview");

    await loadHealth();
    await loadRuns();
    await loadRawTables();

    if (state.selectedRunId) {
      q("runSelect").value = String(state.selectedRunId);
      await loadOverview();
      await refreshCurrentTab();
    }
  } catch (err) {
    renderError("tab-overview", err);
  }
}

initialize();

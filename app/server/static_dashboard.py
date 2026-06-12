DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Codex 监控</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 0; }

/* Nav */
.nav { display: flex; align-items: center; background: #161b22; border-bottom: 1px solid #30363d; padding: 0 24px; height: 52px; position: sticky; top: 0; z-index: 100; }
.nav-title { font-size: 18px; font-weight: 700; color: #f0f6fc; margin-right: 32px; }
.nav-item { padding: 0 16px; height: 52px; display: flex; align-items: center; color: #8b949e; cursor: pointer; font-size: 14px; border-bottom: 2px solid transparent; transition: all 0.15s; }
.nav-item:hover { color: #c9d1d9; background: #1c2128; }
.nav-item.active { color: #f0f6fc; border-bottom-color: #58a6ff; background: transparent; }

.content { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page { display: none; }
.page.active { display: block; }

h2 { font-size: 16px; margin-bottom: 12px; color: #f0f6fc; }
.cards { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; min-width: 160px; flex: 1; }
.card .label { font-size: 12px; color: #8b949e; text-transform: uppercase; }
.card .value { font-size: 28px; font-weight: 600; margin-top: 4px; color: #f0f6fc; }
.card .sub { font-size: 13px; color: #8b949e; margin-top: 4px; }
.token-row { display: flex; gap: 24px; margin-top: 12px; }
.token-row > div { text-align: center; flex: 1; }
.token-row .num { font-size: 18px; font-weight: 600; color: #f0f6fc; }
.token-row .lbl { font-size: 11px; color: #8b949e; text-transform: uppercase; }
.bar-stack { display: flex; height: 6px; overflow: hidden; margin-top: 8px; }
.bar-stack > div { min-width: 2px; }
.bar-stack > div:first-child { border-radius: 3px 0 0 3px; }
.bar-stack > div:last-child { border-radius: 0 3px 3px 0; }
.chart-container { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 24px; }
.charts-2col { display: grid; grid-template-columns: 340px 1fr; gap: 16px; margin-bottom: 24px; }
.charts-2col > .chart-container { margin-bottom: 0; height: 300px; }
#events { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
#events h3 { margin-bottom: 8px; }
#events ul { list-style: none; }
#events li { padding: 4px 0; font-size: 13px; border-bottom: 1px solid #21262d; }
.section-label { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.section-label span { font-size: 14px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
.section-label .line { flex: 1; height: 1px; background: #21262d; }
.quota-cards .card { text-align: center; min-width: 140px; }

/* Window selector */
.window-selector { display: flex; gap: 8px; margin-bottom: 16px; }
.window-btn { padding: 6px 16px; border-radius: 6px; border: 1px solid #30363d; background: #161b22; color: #8b949e; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.window-btn:hover { background: #1c2128; color: #c9d1d9; }
.window-btn.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }

/* Toolbar */
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
</style>
</head>
<body>

<!-- Nav -->
<div class="nav">
  <div class="nav-title">Codex 监控</div>
  <div class="nav-item active" data-page="overview">概览</div>
  <div class="nav-item" data-page="quota">配额</div>
  <div class="nav-item" data-page="events">事件</div>
  <div style="margin-left:auto"><select id="refreshInterval" style="background:#161b22;color:#8b949e;border:1px solid #30363d;border-radius:6px;padding:4px 8px;font-size:13px;cursor:pointer"><option value="10000">10s</option><option value="30000" selected>30s</option><option value="60000">1m</option></select></div>
</div>

<div class="content">

<!-- Page: 概览 -->
<div class="page active" id="page-overview">
  <div class="section-label"><span>当前配额</span><div class="line"></div></div>
  <div class="cards quota-cards" id="ovQuotaCards"></div>
  <div class="section-label"><span>用量概览</span><div class="line"></div></div>
  <div class="cards" id="ovCards"></div>
  <div class="charts-2col">
    <div class="chart-container"><canvas id="ovCostChart"></canvas></div>
    <div class="chart-container"><canvas id="ovModelChart"></canvas></div>
  </div>
  <div class="chart-container" style="height:400px"><canvas id="ovTrendChart"></canvas></div>
</div>

<!-- Page: 配额 -->
<div class="page" id="page-quota">
  <div class="section-label"><span>配额额度</span><div class="line"></div></div>
  <div class="cards quota-cards" id="quotaCards"></div>
  <div class="toolbar">
    <div class="window-selector">
      <button class="window-btn active" data-window="both">全部</button>
      <button class="window-btn" data-window="five_hour">5 小时</button>
      <button class="window-btn" data-window="weekly">周</button>
    </div>
    <div></div>
  </div>
  <div class="chart-container"><canvas id="quotaChart"></canvas></div>
</div>

<!-- Page: 事件 -->
<div class="page" id="page-events">
  <div id="events"><h3>事件日志</h3><ul id="eventList"></ul></div>
</div>

</div>

<script>
// === Nav ===
let currentPage = 'overview';
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => {
    const page = el.dataset.page;
    if (page === currentPage) return;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === page));
    document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + page));
    destroyAllCharts();
    currentPage = page;
    refresh();
  });
});

// === Helpers ===
async function fetchJSON(url) {
  const res = await fetch(url);
  return res.json();
}

const COLORS = ['#58a6ff','#3fb950','#d29922','#f778ba','#a371f7','#db6d28','#8b949e'];
let charts = {};
let lastData = {};

const fmt = (n) => Number(n).toLocaleString('en-US');
const fmt$ = (n) => '$' + Number(n).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:4});
const fmtNum = (n) => (n / 1_000_000).toFixed(2) + 'M';

function destroyChart(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }
function destroyAllCharts() { Object.keys(charts).forEach(k => destroyChart(k)); }

function fmtTime(isoStr) { if (!isoStr) return '-'; return new Date(isoStr).toLocaleString(); }
function gaugeColor(pct) { if (pct == null) return '#30363d'; if (pct <= 15) return '#f85149'; if (pct <= 30) return '#d29922'; return '#3fb950'; }
function gaugeSVG(pct, size) {
  if (pct == null) return `<svg width="${size}" height="${size}" viewBox="0 0 80 80"><circle cx="40" cy="40" r="34" fill="none" stroke="#30363d" stroke-width="6"/><text x="40" y="42" text-anchor="middle" fill="#8b949e" font-size="16" font-weight="700">-</text></svg>`;
  const r = 34, circ = 2 * Math.PI * r;
  const color = gaugeColor(pct);
  const offset = circ * (1 - pct / 100);
  return `<svg width="${size}" height="${size}" viewBox="0 0 80 80">
    <circle cx="40" cy="40" r="${r}" fill="none" stroke="#21262d" stroke-width="6"/>
    <circle cx="40" cy="40" r="${r}" fill="none" stroke="${color}" stroke-width="6"
      stroke-dasharray="${circ}" stroke-dashoffset="${offset}"
      transform="rotate(-90 40 40)" stroke-linecap="round"/>
    <text x="40" y="42" text-anchor="middle" fill="${color}" font-size="18" font-weight="700">${Math.round(pct)}%</text>
  </svg>`;
}

// === Refresh ===
async function refresh() {
    const data = await Promise.all([
      fetchJSON('/api/status'),
      fetchJSON('/api/token-usage'),
      fetchJSON('/api/events'),
      fetchJSON('/api/usage/windowed'),
      fetchJSON('/api/quota/status'),
      fetchJSON('/api/quota/history?limit=20'),
      fetchJSON('/api/quota/estimated-costs?limit=20'),
    ]);
    lastData = { status: data[0], tokenUsage: data[1], events: data[2], windowed: data[3], quotaStatus: data[4], quotaHistory: data[5], estimatedCosts: data[6] };

  if (currentPage === 'overview') renderOverview(lastData);
  else if (currentPage === 'quota') renderQuota(lastData);
  else if (currentPage === 'events') renderEvents(lastData);
}

// === Overview ===
function renderOverview(d) {
  const q = d.quotaStatus || {};
  document.getElementById('ovQuotaCards').innerHTML = `
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">套餐</div><div style="flex:1;display:flex;align-items:center"><div class="value" style="font-size:22px">${q.plan_type || '-'}</div></div></div>
    <div class="card">
      <div class="label">5 小时剩余</div>
      <div style="display:flex;flex-direction:column;align-items:center;margin-top:8px">
        ${gaugeSVG(q.five_hour_remaining_pct, 80)}
        <div style="font-size:11px;color:#8b949e">重置: ${fmtTime(q.five_hour_reset_at)}</div>
      </div>
    </div>
    <div class="card">
      <div class="label">周剩余</div>
      <div style="display:flex;flex-direction:column;align-items:center;margin-top:8px">
        ${gaugeSVG(q.weekly_remaining_pct, 80)}
        <div style="font-size:11px;color:#8b949e">重置: ${fmtTime(q.weekly_reset_at)}</div>
      </div>
    </div>
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">最后采集</div><div style="flex:1;display:flex;align-items:center"><div class="value" style="font-size:16px">${fmtTime(q.captured_at)}</div></div></div>
  `;

  const s = d.status.summary || {};
  const today = d.status.today || {};
  const w = d.windowed || {};
  const fh = w.five_hour?.usage || {};
  const wk = w.weekly?.usage || {};
  const fhEstTotal = q.five_hour_used_pct > 0 ? (fh.total_cost || 0) / (q.five_hour_used_pct / 100) : 0;
  const wkEstTotal = q.weekly_used_pct > 0 ? (wk.total_cost || 0) / (q.weekly_used_pct / 100) : 0;
  const uncached = s.total_input - s.total_cached;
  const pct = (v) => s.total_tokens > 0 ? (v / s.total_tokens * 100).toFixed(0) : 0;
  document.getElementById('ovCards').innerHTML = `
    <div class="card" style="flex:2;min-width:320px">
      <div class="label">总计</div>
      <div style="display:flex;justify-content:space-between;align-items:baseline"><div class="value">${fmtNum(s.total_tokens)}</div><div class="value" style="color:#d29922;font-size:22px">${fmt$(s.total_cost)}</div></div>
      <div class="sub">${fmt(s.total_entries)} 次请求</div>
      <div class="bar-stack"><div style="width:${pct(uncached)}%;background:#58a6ff"></div><div style="width:${pct(s.total_cached)}%;background:#a371f7"></div><div style="width:${pct(s.total_output)}%;background:#f85149"></div></div>
      <div class="token-row"><div><div class="num">${fmtNum(uncached)}</div><div class="lbl">输入</div></div><div><div class="num">${fmtNum(s.total_cached)}</div><div class="lbl">缓存读取</div></div><div><div class="num">${fmtNum(s.total_output)}</div><div class="lbl">输出</div></div></div>
    </div>
    <div class="card" style="flex:2;min-width:320px">
      <div class="label">今日</div>
      <div style="display:flex;justify-content:space-between;align-items:baseline"><div class="value">${fmtNum(today.total_tokens)}</div><div class="value" style="color:#d29922;font-size:22px">${fmt$(today.estimated_cost_usd)}</div></div>
      <div class="sub">${fmt(today.entries)} 次请求</div>
      <div class="bar-stack"><div style="width:${today.total_tokens > 0 ? ((today.input_tokens - today.cached_input_tokens) / today.total_tokens * 100).toFixed(0) : 0}%;background:#58a6ff"></div><div style="width:${today.total_tokens > 0 ? (today.cached_input_tokens / today.total_tokens * 100).toFixed(0) : 0}%;background:#a371f7"></div><div style="width:${today.total_tokens > 0 ? (today.output_tokens / today.total_tokens * 100).toFixed(0) : 0}%;background:#f85149"></div></div>
      <div class="token-row"><div><div class="num">${fmtNum(today.input_tokens - today.cached_input_tokens)}</div><div class="lbl">输入</div></div><div><div class="num">${fmtNum(today.cached_input_tokens)}</div><div class="lbl">缓存读取</div></div><div><div class="num">${fmtNum(today.output_tokens)}</div><div class="lbl">输出</div></div></div>
    </div>
    <div class="card"><div class="label">5h 窗口 Token</div><div class="value">${fmtNum(fh.total_tokens || 0)}</div><div class="sub">${fmt$(fh.total_cost || 0)} / ${fmt$(fhEstTotal)}</div><div class="sub" style="font-size:11px">开始: ${w.five_hour ? fmtTime(w.five_hour.window_start) : '-'}</div><div class="sub" style="font-size:11px">结束: ${w.five_hour ? fmtTime(w.five_hour.window_end) : '-'}</div></div>
    <div class="card"><div class="label">周窗口 Token</div><div class="value">${fmtNum(wk.total_tokens || 0)}</div><div class="sub">${fmt$(wk.total_cost || 0)} / ${fmt$(wkEstTotal)}</div><div class="sub" style="font-size:11px">开始: ${w.weekly ? fmtTime(w.weekly.window_start) : '-'}</div><div class="sub" style="font-size:11px">结束: ${w.weekly ? fmtTime(w.weekly.window_end) : '-'}</div></div>
  `;

  // Doughnut
  destroyChart('ovCostChart');
  if ((d.status.models || []).length > 0) {
    charts.ovCostChart = new Chart(document.getElementById('ovCostChart'), {
      type: 'doughnut',
      data: { labels: d.status.models.map(m => m.model), datasets: [{ data: d.status.models.map(m => Number(m.total_cost)), backgroundColor: COLORS.slice(0, d.status.models.length), borderWidth: 0 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { title: { display: true, text: '模型成本分布', color: '#c9d1d9' }, legend: { position: 'bottom', labels: { color: '#c9d1d9', boxWidth: 12, padding: 8 } }, tooltip: { callbacks: { label: (ctx) => fmt$(ctx.parsed) } } } },
    });
  }

  // Model bar
  destroyChart('ovModelChart');
  if ((d.status.models || []).length > 0) {
    charts.ovModelChart = new Chart(document.getElementById('ovModelChart'), {
      type: 'bar',
      data: {
        labels: d.status.models.map(m => m.model),
        datasets: [
          { label: 'Input', data: d.status.models.map(m => Number(m.input_tokens) - Number(m.cached_input_tokens)), backgroundColor: '#58a6ff' },
          { label: 'Cache', data: d.status.models.map(m => Number(m.cached_input_tokens)), backgroundColor: '#a371f7' },
          { label: 'Output', data: d.status.models.map(m => Number(m.output_tokens)), backgroundColor: '#3fb950' },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { title: { display: true, text: '模型 Token 分布', color: '#c9d1d9' }, legend: { labels: { color: '#c9d1d9' } } },
        scales: { x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }, y: { ticks: { color: '#8b949e', callback: (v) => fmt(v) }, grid: { color: '#21262d' } } },
      },
    });
  }

  // Trend (last 24h, continuous hourly slots)
  const now = new Date();
  const labels = [];
  const tokenData = [];
  const costData = [];
  const buckets = {};
  for (const r of d.tokenUsage) {
    const date = new Date(r.event_time);
    if (date.getTime() < now.getTime() - 24 * 3600 * 1000) continue;
    const key = date.toLocaleDateString() + ' ' + date.getHours() + ':00';
    if (!buckets[key]) buckets[key] = { tokens: 0, cost: 0 };
    buckets[key].tokens += (r.input_tokens + r.output_tokens);
    buckets[key].cost += (r.estimated_cost_usd || 0);
  }
  for (let i = 23; i >= 0; i--) {
    const h = new Date(now.getTime() - i * 3600 * 1000);
    const key = h.toLocaleDateString() + ' ' + h.getHours() + ':00';
    labels.push(key);
    const b = buckets[key];
    tokenData.push(b ? b.tokens : 0);
    costData.push(b ? Number(b.cost.toFixed(4)) : 0);
  }
  destroyChart('ovTrendChart');
  {
    charts.ovTrendChart = new Chart(document.getElementById('ovTrendChart'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Token', data: tokenData, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', yAxisID: 'y', tension: 0.3, fill: true },
          { label: 'Cost $', data: costData, borderColor: '#d29922', backgroundColor: 'rgba(210,153,34,0.1)', yAxisID: 'y1', tension: 0.3, fill: true },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { title: { display: true, text: 'Token 和成本趋势（按小时）', color: '#c9d1d9' }, legend: { labels: { color: '#c9d1d9' } } },
        scales: {
          x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
          y: { type: 'linear', position: 'left', ticks: { color: '#58a6ff', callback: (v) => fmt(v) }, grid: { color: '#21262d' } },
          y1: { type: 'linear', position: 'right', ticks: { color: '#d29922', callback: (v) => fmt$(v) }, grid: { display: false } },
        },
      },
    });
  }
}

// === Quota ===
let selectedWindow = 'both';
document.querySelectorAll('.window-btn').forEach(el => {
  el.addEventListener('click', () => {
    selectedWindow = el.dataset.window;
    document.querySelectorAll('.window-btn').forEach(b => b.classList.toggle('active', b.dataset.window === selectedWindow));
    if (currentPage === 'quota') renderQuota(lastData);
  });
});

function renderQuota(d) {
  const q = d.quotaStatus;
  document.getElementById('quotaCards').innerHTML = `
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">套餐</div><div style="flex:1;display:flex;align-items:center"><div class="value" style="font-size:22px">${q.plan_type || '-'}</div></div></div>
    <div class="card">
      <div class="label">5 小时剩余</div>
      <div style="display:flex;flex-direction:column;align-items:center;margin-top:8px">
        ${gaugeSVG(q.five_hour_remaining_pct, 80)}
      </div>
      <div class="sub" style="text-align:center;margin-top:6px">重置: ${fmtTime(q.five_hour_reset_at)}</div>
    </div>
    <div class="card">
      <div class="label">周剩余</div>
      <div style="display:flex;flex-direction:column;align-items:center;margin-top:8px">
        ${gaugeSVG(q.weekly_remaining_pct, 80)}
      </div>
      <div class="sub" style="text-align:center;margin-top:6px">重置: ${fmtTime(q.weekly_reset_at)}</div>
    </div>
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">最后采集</div><div style="flex:1;display:flex;align-items:center"><div class="value" style="font-size:16px">${fmtTime(q.captured_at)}</div></div></div>
  `;

  const history = d.quotaHistory;
  const estCosts = d.estimatedCosts || [];
  destroyChart('quotaChart');
  if (history.length > 0) {
    const labels = history.map(r => new Date(r.captured_at).toLocaleString());
    const datasets = [];
    if (selectedWindow === 'both' || selectedWindow === 'five_hour') {
      datasets.push({ label: '5 小时剩余 %', data: history.map(r => r.five_hour_remaining_pct), borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.08)', tension: 0.3, fill: true, pointRadius: 2, yAxisID: 'y' });
      datasets.push({ label: '5h 估算总额 $', data: estCosts.map(r => r.five_hour_est_total), borderColor: '#d29922', backgroundColor: 'rgba(210,153,34,0.08)', tension: 0.3, fill: false, pointRadius: 2, yAxisID: 'y1', borderDash: [5, 3] });
    }
    if (selectedWindow === 'both' || selectedWindow === 'weekly') {
      datasets.push({ label: '周剩余 %', data: history.map(r => r.weekly_remaining_pct), borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.08)', tension: 0.3, fill: true, pointRadius: 2, yAxisID: 'y' });
      datasets.push({ label: '周估算总额 $', data: estCosts.map(r => r.weekly_est_total), borderColor: '#f778ba', backgroundColor: 'rgba(247,120,186,0.08)', tension: 0.3, fill: false, pointRadius: 2, yAxisID: 'y1', borderDash: [5, 3] });
    }
    charts.quotaChart = new Chart(document.getElementById('quotaChart'), {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: { title: { display: true, text: selectedWindow === 'both' ? '配额剩余趋势（全部）' : selectedWindow === 'five_hour' ? '5 小时剩余趋势' : '周剩余趋势', color: '#c9d1d9' }, legend: { labels: { color: '#c9d1d9' } }, tooltip: { callbacks: { label: (ctx) => ctx.dataset.yAxisID === 'y1' ? ctx.dataset.label + ': ' + fmt$(ctx.parsed.y) : ctx.dataset.label + ': ' + ctx.parsed.y + '%' } } },
        scales: {
          x: { ticks: { color: '#8b949e', maxRotation: 45 }, grid: { color: '#21262d' } },
          y: { min: 0, max: 100, position: 'left', ticks: { color: '#8b949e', callback: (v) => v + '%' }, grid: { color: '#21262d' }, title: { display: true, text: '剩余 %', color: '#8b949e' } },
          y1: { position: 'right', ticks: { color: '#d29922', callback: (v) => fmt$(v) }, grid: { display: false }, title: { display: true, text: '估算总额 $', color: '#d29922' } },
        },
      },
    });
  }
}

// === Events ===
function renderEvents(d) {
  document.getElementById('eventList').innerHTML = d.events.slice(0, 50).map(e =>
    `<li>[${new Date(e.event_at).toLocaleString()}] <strong>${e.event_type}</strong>: ${e.message || ''}</li>`
  ).join('');
}

// === Init ===
let refreshTimer;
function startRefresh() {
  clearInterval(refreshTimer);
  refreshTimer = setInterval(refresh, parseInt(document.getElementById('refreshInterval').value));
}
document.getElementById('refreshInterval').addEventListener('change', startRefresh);
refresh();
startRefresh();
</script>
</body>
</html>"""
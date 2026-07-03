DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Codex 监控</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect x='4' y='4' width='56' height='56' rx='12' fill='%231f6feb'/%3E%3Cpolyline points='16,40 24,28 32,34 40,20 48,26' fill='none' stroke='white' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3Ccircle cx='24' cy='28' r='2.5' fill='white'/%3E%3Ccircle cx='32' cy='34' r='2.5' fill='white'/%3E%3Ccircle cx='40' cy='20' r='2.5' fill='white'/%3E%3Cline x1='16' y1='44' x2='48' y2='44' stroke='white' stroke-width='1.5' stroke-linecap='round'/%3E%3Cline x1='16' y1='20' x2='16' y2='44' stroke='white' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E">
<script src="/static/chart.umd.min.js"></script>
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
.usage-btn { padding: 6px 16px; border-radius: 6px; border: 1px solid #30363d; background: #161b22; color: #8b949e; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.usage-btn:hover { background: #1c2128; color: #c9d1d9; }
.usage-btn.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }
.quota-range-btn { padding: 6px 16px; border-radius: 6px; border: 1px solid #30363d; background: #161b22; color: #8b949e; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.quota-range-btn:hover { background: #1c2128; color: #c9d1d9; }
.quota-range-btn.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }
.trend-btn { padding: 6px 16px; border-radius: 6px; border: 1px solid #30363d; background: #161b22; color: #8b949e; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.trend-btn:hover { background: #1c2128; color: #c9d1d9; }
.trend-btn.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }

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
  <div class="nav-item" data-page="usage">用量</div>
  <div class="nav-item" data-page="events">事件</div>
  <div style="margin-left:auto;display:flex;gap:12px;align-items:center">
    <button id="refreshAll" style="background:#1f6feb;color:#fff;border:none;border-radius:6px;padding:4px 12px;font-size:13px;cursor:pointer">全部刷新</button>
    <span style="color:#8b949e;font-size:12px">限额刷新 <select id="quotaInterval" style="background:#161b22;color:#8b949e;border:1px solid #30363d;border-radius:6px;padding:4px 8px;font-size:13px;cursor:pointer"><option value="5">5m</option><option value="10" selected>10m</option><option value="15">15m</option><option value="30">30m</option></select></span>
    <span style="color:#8b949e;font-size:12px">token刷新 <select id="pollInterval" style="background:#161b22;color:#8b949e;border:1px solid #30363d;border-radius:6px;padding:4px 8px;font-size:13px;cursor:pointer"><option value="10">10s</option><option value="30">30s</option><option value="60">1m</option><option value="300">5m</option><option value="600" selected>10m</option></select></span>
    <span style="color:#8b949e;font-size:12px">刷新 <select id="refreshInterval" style="background:#161b22;color:#8b949e;border:1px solid #30363d;border-radius:6px;padding:4px 8px;font-size:13px;cursor:pointer"><option value="10000">10s</option><option value="30000" selected>30s</option><option value="60000">1m</option></select></span>
  </div>
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
  <div class="chart-container" style="height:400px">
    <div style="display:flex;justify-content:flex-end;margin-bottom:8px">
      <div class="window-selector">
        <button class="trend-btn active" data-gran="hour">按小时</button>
        <button class="trend-btn" data-gran="day">按天</button>
      </div>
    </div>
    <canvas id="ovTrendChart"></canvas>
  </div>
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
    <div class="window-selector">
      <button class="quota-range-btn active" data-range="24h">近 24h</button>
      <button class="quota-range-btn" data-range="7d">近 7 天</button>
      <button class="quota-range-btn" data-range="30d">近 30 天</button>
      <button class="quota-range-btn" data-range="all">全部</button>
    </div>
  </div>
  <div class="chart-container"><canvas id="quotaChart"></canvas></div>
</div>

<!-- Page: 用量 -->
<div class="page" id="page-usage">
  <div class="toolbar">
    <div class="window-selector">
      <button class="usage-btn active" data-preset="24h">近 24h</button>
      <button class="usage-btn" data-preset="7d">近 7 天</button>
      <button class="usage-btn" data-preset="30d">近 30 天</button>
      <button class="usage-btn" data-preset="today">今天</button>
      <button class="usage-btn" data-preset="week">这周</button>
      <button class="usage-btn" data-preset="month">这月</button>
    </div>
    <div></div>
  </div>
  <div class="cards" id="usageCards"></div>
  <div class="charts-2col">
    <div class="chart-container"><canvas id="usageModelChart"></canvas></div>
    <div class="chart-container"><canvas id="usageCostChart"></canvas></div>
  </div>
  <div class="chart-container" style="height:400px"><canvas id="usageTrendChart"></canvas></div>
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
// 按天聚合的接口返回 date-only 串，直接 new Date('YYYY-MM-DD') 会按 UTC 0 点解析导致日期偏移，补上本地 0 点
const parseEventTime = (s) => /^\\d{4}-\\d{2}-\\d{2}$/.test(s) ? new Date(s + 'T00:00:00') : new Date(s);
function fmtCountdown(isoStr) {
  if (!isoStr) return '-';
  const diff = new Date(isoStr) - new Date();
  if (diff <= 0) return '已重置';
  const totalMin = Math.floor(diff / 60000);
  const days = Math.floor(totalMin / 1440);
  const hours = Math.floor((totalMin % 1440) / 60);
  const mins = totalMin % 60;
  if (days > 0) return `还剩 ${days}天${hours}小时${mins}分钟`;
  if (hours > 0) return `还剩 ${hours}小时${mins}分钟`;
  return `还剩 ${mins}分钟`;
}
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

// === 重置卡（概览页 / 配额页共用） ===
function availableResetCards(rc) { return ((rc || {}).credits || []).filter(c => c.status === 'available'); }
function resetCardRow(c) {
  const exp = c.expires_at ? new Date(c.expires_at).toLocaleDateString() : '';
  const days = c.expires_at ? Math.ceil((new Date(c.expires_at) - new Date()) / 86400000) : null;
  return `<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #21262d"><div><div style="font-size:13px">${c.title || '重置卡'}</div><div style="font-size:11px;color:#8b949e">${c.description || ''}</div></div><div style="text-align:right"><div style="font-size:12px;color:#8b949e">${exp}</div><div style="font-size:11px;color:${days !== null && days <= 7 ? '#d29922' : '#8b949e'}">${days !== null ? days + '天后过期' : ''}</div></div></div>`;
}
function updateRcModal(rcList) {
  let modal = document.getElementById('rcModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'rcModal';
    modal.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:1000';
    modal.onclick = e => { if (e.target === modal) modal.style.display = 'none'; };
    document.body.appendChild(modal);
  }
  modal.innerHTML = `<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;width:480px;height:400px;overflow-y:auto;overflow-x:hidden"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><div style="font-size:15px;font-weight:600">重置卡详情</div><button onclick="this.closest('#rcModal').style.display='none'" style="background:none;border:none;color:#8b949e;font-size:18px;cursor:pointer">&times;</button></div>${rcList.map(resetCardRow).join('') || '<div style="color:#8b949e;font-size:13px">暂无可用重置卡</div>'}</div>`;
}

// === Refresh ===
async function refresh() {
    const trendDays = selectedTrendGran === 'hour' ? 1 : 30;
    const trendFrom = new Date(Date.now() - trendDays * 24 * 3600 * 1000).toISOString();
    const dailyParam = selectedTrendGran === 'day' ? '&daily=true' : '';
    const data = await Promise.all([
      fetchJSON('/api/status'),
      fetchJSON('/api/token-usage?from_dt=' + encodeURIComponent(trendFrom) + dailyParam),
      fetchJSON('/api/events'),
      fetchJSON('/api/usage/windowed'),
      fetchJSON('/api/quota/status'),
      fetchJSON('/api/quota/history?limit=20'),
      fetchJSON('/api/quota/estimated-costs?limit=20'),
      fetchJSON('/api/quota/reset-credits'),
    ]);
    lastData = { status: data[0], tokenUsage: data[1], events: data[2], windowed: data[3], quotaStatus: data[4], quotaHistory: data[5], estimatedCosts: data[6], resetCredits: data[7] };

  if (currentPage === 'overview') renderOverview(lastData);
  else if (currentPage === 'quota') loadQuotaData();
  else if (currentPage === 'usage') loadUsageData();
  else if (currentPage === 'events') renderEvents(lastData);
}

// === Overview ===
function renderOverview(d) {
  const q = d.quotaStatus || {};
  const rc = d.resetCredits || {};
  const rcCount = rc.available_count || 0;
  const rcList = availableResetCards(rc);
  const planLabel = q.plan_type ? q.plan_type.charAt(0).toUpperCase() + q.plan_type.slice(1) : '-';
  document.getElementById('ovQuotaCards').innerHTML = `
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">账号</div><div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center"><div style="font-size:13px;color:#8b949e">${q.email || ''}</div><div class="value" style="font-size:22px">${planLabel}</div><div class="sub" style="margin-top:4px">重置卡: <span style="color:${rcCount > 0 ? '#3fb950' : '#8b949e'}">${rcCount}</span>${rcList.length > 0 ? ` <a href="javascript:void(0)" onclick="document.getElementById('rcModal').style.display='block'" style="color:#58a6ff;font-size:11px;margin-left:4px">查看详情</a>` : ''}</div></div></div>
    <div class="card">
      <div class="label">5 小时剩余</div>
      <div style="display:flex;flex-direction:column;align-items:center;margin-top:8px">
        ${gaugeSVG(q.five_hour_remaining_pct, 80)}
        <div style="font-size:11px;color:#8b949e">${fmtCountdown(q.five_hour_reset_at)}</div>
      </div>
    </div>
    <div class="card">
      <div class="label">周剩余</div>
      <div style="display:flex;flex-direction:column;align-items:center;margin-top:8px">
        ${gaugeSVG(q.weekly_remaining_pct, 80)}
        <div style="font-size:11px;color:#8b949e">${fmtCountdown(q.weekly_reset_at)}</div>
      </div>
    </div>
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">最后采集</div><div style="flex:1;display:flex;align-items:center"><div class="value" style="font-size:16px">${fmtTime(q.captured_at)}</div></div></div>
  `;
  updateRcModal(rcList);

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
      <div class="sub">${fmt(s.total_entries)} 次请求${s.total_input > 0 ? ` · <span style="color:#a371f7">缓存命中 ${(s.total_cached / s.total_input * 100).toFixed(1)}%</span>` : ''}</div>
      <div class="bar-stack"><div style="width:${pct(uncached)}%;background:#58a6ff"></div><div style="width:${pct(s.total_cached)}%;background:#a371f7"></div><div style="width:${pct(s.total_output)}%;background:#f85149"></div></div>
      <div class="token-row"><div><div class="num">${fmtNum(uncached)}</div><div class="lbl">输入</div></div><div><div class="num">${fmtNum(s.total_cached)}</div><div class="lbl">缓存读取</div></div><div><div class="num">${fmtNum(s.total_output)}</div><div class="lbl">输出</div></div></div>
    </div>
    <div class="card" style="flex:2;min-width:320px">
      <div class="label">今日</div>
      <div style="display:flex;justify-content:space-between;align-items:baseline"><div class="value">${fmtNum(today.total_tokens)}</div><div class="value" style="color:#d29922;font-size:22px">${fmt$(today.estimated_cost_usd)}</div></div>
      <div class="sub">${fmt(today.entries)} 次请求${today.input_tokens > 0 ? ` · <span style="color:#a371f7">缓存命中 ${(today.cached_input_tokens / today.input_tokens * 100).toFixed(1)}%</span>` : ''}</div>
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

  // Trend
  renderTrendChart(d.tokenUsage);
}

// === Trend Chart ===
let selectedTrendGran = 'hour';
document.querySelectorAll('.trend-btn').forEach(el => {
  el.addEventListener('click', () => {
    selectedTrendGran = el.dataset.gran;
    document.querySelectorAll('.trend-btn').forEach(b => b.classList.toggle('active', b.dataset.gran === selectedTrendGran));
    refresh();
  });
});

function renderTrendChart(tokenUsage) {
  const now = new Date();
  const labels = [];
  const tokenData = [];
  const costData = [];
  const buckets = {};

  if (selectedTrendGran === 'hour') {
    for (const r of tokenUsage) {
      const date = parseEventTime(r.event_time);
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
  } else {
    for (const r of tokenUsage) {
      const date = parseEventTime(r.event_time);
      const key = date.toLocaleDateString();
      if (!buckets[key]) buckets[key] = { tokens: 0, cost: 0 };
      buckets[key].tokens += (r.input_tokens + r.output_tokens);
      buckets[key].cost += (r.estimated_cost_usd || 0);
    }
    for (let i = 29; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 24 * 3600 * 1000);
      const key = d.toLocaleDateString();
      labels.push(key);
      const b = buckets[key];
      tokenData.push(b ? b.tokens : 0);
      costData.push(b ? Number(b.cost.toFixed(4)) : 0);
    }
  }

  destroyChart('ovTrendChart');
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
      plugins: { title: { display: true, text: selectedTrendGran === 'hour' ? 'Token 和成本趋势（按小时）' : 'Token 和成本趋势（按天）', color: '#c9d1d9' }, legend: { labels: { color: '#c9d1d9' } } },
      scales: {
        x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
        y: { type: 'linear', position: 'left', ticks: { color: '#58a6ff', callback: (v) => fmt(v) }, grid: { color: '#21262d' } },
        y1: { type: 'linear', position: 'right', ticks: { color: '#d29922', callback: (v) => fmt$(v) }, grid: { display: false } },
      },
    },
  });
}

// === Quota ===
let selectedWindow = 'both';
let selectedQuotaRange = '24h';
document.querySelectorAll('.window-btn').forEach(el => {
  el.addEventListener('click', () => {
    selectedWindow = el.dataset.window;
    document.querySelectorAll('.window-btn').forEach(b => b.classList.toggle('active', b.dataset.window === selectedWindow));
    if (currentPage === 'quota') renderQuota(lastData);
  });
});
document.querySelectorAll('.quota-range-btn').forEach(el => {
  el.addEventListener('click', () => {
    selectedQuotaRange = el.dataset.range;
    document.querySelectorAll('.quota-range-btn').forEach(b => b.classList.toggle('active', b.dataset.range === selectedQuotaRange));
    if (currentPage === 'quota') loadQuotaData();
  });
});

function getQuotaRange() {
  const now = new Date();
  if (selectedQuotaRange === 'all') return { from: null, to: null };
  let from;
  if (selectedQuotaRange === '24h') from = new Date(now.getTime() - 24 * 3600 * 1000);
  else if (selectedQuotaRange === '7d') from = new Date(now.getTime() - 7 * 24 * 3600 * 1000);
  else if (selectedQuotaRange === '30d') from = new Date(now.getTime() - 30 * 24 * 3600 * 1000);
  return { from: from.toISOString(), to: now.toISOString() };
}

async function loadQuotaData() {
  const { from, to } = getQuotaRange();
  const params = new URLSearchParams();
  if (from) params.set('from_dt', from);
  if (to) params.set('to_dt', to);
  if (!from && !to) params.set('limit', '500');
  if (selectedQuotaRange === '30d') params.set('daily', 'true');
  const qs = params.toString();
  const data = await Promise.all([
    fetchJSON('/api/quota/status'),
    fetchJSON('/api/quota/history?' + qs),
    fetchJSON('/api/quota/estimated-costs?' + qs),
    fetchJSON('/api/quota/reset-credits'),
  ]);
  lastData.quotaStatus = data[0];
  lastData.quotaHistory = data[1];
  lastData.estimatedCosts = data[2];
  lastData.resetCredits = data[3];
  renderQuota(lastData);
}

function renderQuota(d) {
  const q = d.quotaStatus;
  const estCosts = d.estimatedCosts || [];
  const lastEst = estCosts.length > 0 ? estCosts[estCosts.length - 1] : {};
  const rc = d.resetCredits || {};
  const rcCount = rc.available_count || 0;
  const rcList = availableResetCards(rc);
  const nextExpiring = rcList.slice().sort((a, b) => new Date(a.expires_at) - new Date(b.expires_at))[0];
  const nextExpStr = nextExpiring ? new Date(nextExpiring.expires_at).toLocaleDateString() : '';
  const nextExpDays = nextExpiring ? Math.ceil((new Date(nextExpiring.expires_at) - new Date()) / 86400000) : null;
  document.getElementById('quotaCards').innerHTML = `
    <div class="card">
      <div class="label">周剩余</div>
      <div style="display:flex;flex-direction:column;align-items:center;margin-top:8px">
        ${gaugeSVG(q.weekly_remaining_pct, 80)}
      </div>
    </div>
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">周估算额度</div><div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center"><div class="value" style="font-size:22px">${lastEst.weekly_est_total != null ? fmt$(lastEst.weekly_est_total) : '-'}</div></div></div>
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">5 小时估算额度</div><div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center"><div class="value" style="font-size:22px">${lastEst.five_hour_est_total != null ? fmt$(lastEst.five_hour_est_total) : '-'}</div></div></div>
    <div class="card" style="display:flex;flex-direction:column;align-items:center"><div class="label">重置卡</div><div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center"><div class="value" style="font-size:22px;color:${rcCount > 0 ? '#3fb950' : '#8b949e'}">${rcCount}</div>${nextExpiring ? `<div class="sub" style="margin-top:4px">最近过期: ${nextExpStr} <span style="color:${nextExpDays !== null && nextExpDays <= 7 ? '#d29922' : '#8b949e'}">(${nextExpDays}天)</span></div>` : ''}${rcList.length > 0 ? `<div style="margin-top:6px"><button onclick="document.getElementById('rcModal').style.display='block'" style="background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer">查看详情</button></div>` : ''}</div></div>
  `;
  updateRcModal(rcList);

  const history = d.quotaHistory;
  destroyChart('quotaChart');
  if (history.length > 0) {
    const labels = history.map(r => new Date(r.captured_at).toLocaleString());

    const resetLines = [];
    let prevFhReset = null;
    let prevWkReset = null;
    let fhConfirmCount = 0;
    let wkConfirmCount = 0;
    for (let i = 0; i < history.length; i++) {
      const r = history[i];
      const fhReset = r.five_hour_reset_at;
      const wkReset = r.weekly_reset_at;

      if (selectedQuotaRange !== '30d' && fhReset && prevFhReset) {
        const diffMs = Math.abs(new Date(fhReset) - new Date(prevFhReset));
        if (diffMs < 120000) {
          fhConfirmCount++;
        } else {
          if (fhConfirmCount >= 3 || diffMs >= 2 * 3600 * 1000) {
            resetLines.push({ index: i, label: '5h 重置', color: '#58a6ff' });
          }
          fhConfirmCount = 0;
        }
      }
      if (wkReset && prevWkReset) {
        const diffMs = Math.abs(new Date(wkReset) - new Date(prevWkReset));
        if (diffMs < 120000) {
          wkConfirmCount++;
        } else {
          if (wkConfirmCount >= 3 || diffMs >= 2 * 3600 * 1000) {
            resetLines.push({ index: i, label: '周重置', color: '#3fb950' });
          }
          wkConfirmCount = 0;
        }
      }
      if (fhReset) prevFhReset = fhReset;
      if (wkReset) prevWkReset = wkReset;
    }

    const resetPlugin = {
      id: 'resetLines',
      afterDraw(chart) {
        const { ctx, chartArea, scales } = chart;
        const xScale = scales.x;
        resetLines.forEach(line => {
          const x = xScale.getPixelForValue(line.index);
          if (x < chartArea.left || x > chartArea.right) return;
          ctx.save();
          ctx.beginPath();
          ctx.setLineDash([6, 4]);
          ctx.strokeStyle = line.color;
          ctx.globalAlpha = 0.6;
          ctx.lineWidth = 1.5;
          ctx.moveTo(x, chartArea.top);
          ctx.lineTo(x, chartArea.bottom);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.globalAlpha = 0.8;
          ctx.fillStyle = line.color;
          ctx.font = '11px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(line.label, x, chartArea.top - 4);
          ctx.restore();
        });
      },
    };

    function fillCarryForward(arr) {
      const filled = [];
      const isCarried = [];
      let lastValid = null;
      for (const v of arr) {
        if (v !== null && v !== undefined) {
          lastValid = v;
          filled.push(v);
          isCarried.push(false);
        } else {
          filled.push(lastValid);
          isCarried.push(lastValid !== null);
        }
      }
      return { filled, isCarried };
    }

    const datasets = [];
    if (selectedWindow === 'both' || selectedWindow === 'five_hour') {
      datasets.push({ label: '5 小时剩余 %', data: history.map(r => r.five_hour_remaining_pct), borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.08)', tension: 0.3, fill: true, pointRadius: 2, yAxisID: 'y' });
      const fh5 = fillCarryForward(estCosts.map(r => r.five_hour_est_total));
      datasets.push({ label: '5h 估算总额 $', data: fh5.filled, borderColor: '#d29922', backgroundColor: 'rgba(210,153,34,0.08)', tension: 0.3, fill: false, pointRadius: 2, yAxisID: 'y1', borderDash: [5, 3], segment: { borderDash: ctx => fh5.isCarried[ctx.p1DataIndex] ? [2, 3] : [5, 3], borderColor: ctx => fh5.isCarried[ctx.p1DataIndex] ? '#6e7681' : '#d29922' } });
    }
    if (selectedWindow === 'both' || selectedWindow === 'weekly') {
      datasets.push({ label: '周剩余 %', data: history.map(r => r.weekly_remaining_pct), borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.08)', tension: 0.3, fill: true, pointRadius: 2, yAxisID: 'y' });
      const wk = fillCarryForward(estCosts.map(r => r.weekly_est_total));
      datasets.push({ label: '周估算总额 $', data: wk.filled, borderColor: '#f778ba', backgroundColor: 'rgba(247,120,186,0.08)', tension: 0.3, fill: false, pointRadius: 2, yAxisID: 'y1', borderDash: [5, 3], segment: { borderDash: ctx => wk.isCarried[ctx.p1DataIndex] ? [2, 3] : [5, 3], borderColor: ctx => wk.isCarried[ctx.p1DataIndex] ? '#6e7681' : '#f778ba' } });
    }
    charts.quotaChart = new Chart(document.getElementById('quotaChart'), {
      type: 'line',
      data: { labels, datasets },
      plugins: [resetPlugin],
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

// === Usage ===
let selectedPreset = '24h';
document.querySelectorAll('.usage-btn').forEach(el => {
  el.addEventListener('click', () => {
    selectedPreset = el.dataset.preset;
    document.querySelectorAll('.usage-btn').forEach(b => b.classList.toggle('active', b.dataset.preset === selectedPreset));
    if (currentPage === 'usage') loadUsageData();
  });
});

function getUsageRange() {
  const now = new Date();
  let from, to;
  to = now.toISOString();
  if (selectedPreset === '24h') {
    from = new Date(now.getTime() - 24 * 3600 * 1000).toISOString();
  } else if (selectedPreset === '7d') {
    from = new Date(now.getTime() - 7 * 24 * 3600 * 1000).toISOString();
  } else if (selectedPreset === '30d') {
    from = new Date(now.getTime() - 30 * 24 * 3600 * 1000).toISOString();
  } else if (selectedPreset === 'today') {
    const start = new Date(now);
    start.setHours(0, 0, 0, 0);
    from = start.toISOString();
  } else if (selectedPreset === 'week') {
    const start = new Date(now);
    start.setDate(start.getDate() - start.getDay());
    start.setHours(0, 0, 0, 0);
    from = start.toISOString();
  } else if (selectedPreset === 'month') {
    const start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
    from = start.toISOString();
  }
  return { from, to };
}

async function loadUsageData() {
  const { from, to } = getUsageRange();
  const params = new URLSearchParams({ from_dt: from, to_dt: to });
  if (selectedPreset === '30d' || selectedPreset === 'month') params.set('daily', 'true');
  const rows = await fetchJSON('/api/token-usage?' + params);
  const d = { rows };
  renderUsage(d);
}

function renderUsage(d) {
  const rows = d.rows || d.tokenUsage || [];
  // 跨度 > 7 天则按天聚合，避免趋势图 X 轴过密
  const longRange = selectedPreset === '30d' || selectedPreset === 'month';
  let input = 0, cached = 0, output = 0, reasoning = 0, cost = 0;
  const models = {};
  const buckets = {};
  for (const r of rows) {
    const inp = r.input_tokens || 0;
    const cac = r.cached_input_tokens || 0;
    const out = r.output_tokens || 0;
    const rea = r.reasoning_tokens || 0;
    const cst = r.estimated_cost_usd || 0;
    input += inp; cached += cac; output += out; reasoning += rea; cost += cst;
    const m = r.model || 'unknown';
    if (!models[m]) models[m] = { input: 0, cached: 0, output: 0, cost: 0 };
    models[m].input += inp; models[m].cached += cac; models[m].output += out; models[m].cost += cst;
    const date = parseEventTime(r.event_time);
    const key = longRange
      ? date.toLocaleDateString()
      : date.toLocaleDateString() + ' ' + date.getHours() + ':00';
    if (!buckets[key]) buckets[key] = { tokens: 0, cost: 0 };
    buckets[key].tokens += (inp + out);
    buckets[key].cost += cst;
  }
  const total = input + output;
  const uncached = input - cached;

  const modelNames = Object.keys(models).sort((a, b) => models[b].cost - models[a].cost);

  document.getElementById('usageCards').innerHTML = `
    <div class="card" style="flex:2;min-width:320px">
      <div class="label">用量统计</div>
      <div style="display:flex;justify-content:space-between;align-items:baseline"><div class="value">${fmtNum(total)}</div><div class="value" style="color:#d29922;font-size:22px">${fmt$(cost)}</div></div>
      <div class="sub">${rows.length} 次请求${input > 0 ? ` · <span style="color:#a371f7">缓存命中 ${(cached / input * 100).toFixed(1)}%</span>` : ''}</div>
      <div class="bar-stack"><div style="width:${total > 0 ? (uncached / total * 100).toFixed(0) : 0}%;background:#58a6ff"></div><div style="width:${total > 0 ? (cached / total * 100).toFixed(0) : 0}%;background:#a371f7"></div><div style="width:${total > 0 ? (output / total * 100).toFixed(0) : 0}%;background:#f85149"></div></div>
      <div class="token-row"><div><div class="num">${fmtNum(uncached)}</div><div class="lbl">输入</div></div><div><div class="num">${fmtNum(cached)}</div><div class="lbl">缓存读取</div></div><div><div class="num">${fmtNum(output)}</div><div class="lbl">输出</div></div></div>
    </div>
    <div class="card" style="display:flex;flex-direction:column">
      <div class="label">使用模型 (${modelNames.length})</div>
      <div style="margin-top:8px;display:flex;flex-direction:column;gap:6px;flex:1;overflow:hidden">
        ${modelNames.map((m, i) => `
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:13px;line-height:1.4">
            <span style="display:flex;align-items:center;gap:8px;color:#c9d1d9;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${COLORS[i % COLORS.length]};flex-shrink:0"></span>
              ${m}
            </span>
            <span style="color:#d29922;font-variant-numeric:tabular-nums;flex-shrink:0;margin-left:8px">${fmt$(models[m].cost)}</span>
          </div>
        `).join('') || '<div style="color:#6e7681;font-size:13px">暂无数据</div>'}
      </div>
    </div>
  `;

  destroyChart('usageModelChart');
  if (modelNames.length > 0) {
    charts.usageModelChart = new Chart(document.getElementById('usageModelChart'), {
      type: 'bar',
      data: {
        labels: modelNames,
        datasets: [
          { label: 'Input', data: modelNames.map(m => models[m].input - models[m].cached), backgroundColor: '#58a6ff' },
          { label: 'Cache', data: modelNames.map(m => models[m].cached), backgroundColor: '#a371f7' },
          { label: 'Output', data: modelNames.map(m => models[m].output), backgroundColor: '#3fb950' },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: '模型 Token 分布', color: '#c9d1d9' }, legend: { labels: { color: '#c9d1d9' } } }, scales: { x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }, y: { ticks: { color: '#8b949e', callback: (v) => fmt(v) }, grid: { color: '#21262d' } } } },
    });
  }

  destroyChart('usageCostChart');
  if (modelNames.length > 0) {
    charts.usageCostChart = new Chart(document.getElementById('usageCostChart'), {
      type: 'doughnut',
      data: { labels: modelNames, datasets: [{ data: modelNames.map(m => Number(models[m].cost.toFixed(4))), backgroundColor: COLORS.slice(0, modelNames.length), borderWidth: 0 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { title: { display: true, text: '模型成本分布', color: '#c9d1d9' }, legend: { position: 'bottom', labels: { color: '#c9d1d9', boxWidth: 12, padding: 8 } }, tooltip: { callbacks: { label: (ctx) => fmt$(ctx.parsed) } } } },
    });
  }

  const labels = Object.keys(buckets);
  destroyChart('usageTrendChart');
  if (labels.length > 0) {
    charts.usageTrendChart = new Chart(document.getElementById('usageTrendChart'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Token', data: labels.map(k => buckets[k].tokens), borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', yAxisID: 'y', tension: 0.3, fill: true },
          { label: 'Cost $', data: labels.map(k => Number(buckets[k].cost.toFixed(4))), borderColor: '#d29922', backgroundColor: 'rgba(210,153,34,0.1)', yAxisID: 'y1', tension: 0.3, fill: true },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { title: { display: true, text: longRange ? 'Token 和成本趋势（按天）' : 'Token 和成本趋势（按小时）', color: '#c9d1d9' }, legend: { labels: { color: '#c9d1d9' } } },
        scales: { x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }, y: { type: 'linear', position: 'left', ticks: { color: '#58a6ff', callback: (v) => fmt(v) }, grid: { color: '#21262d' } }, y1: { type: 'linear', position: 'right', ticks: { color: '#d29922', callback: (v) => fmt$(v) }, grid: { display: false } } },
      },
    });
  }
}

// === Init ===
let refreshTimer;
function startRefresh() {
  clearInterval(refreshTimer);
  refreshTimer = setInterval(refresh, parseInt(document.getElementById('refreshInterval').value));
}
document.getElementById('refreshInterval').addEventListener('change', startRefresh);

document.getElementById('quotaInterval').addEventListener('change', async () => {
  const minutes = parseInt(document.getElementById('quotaInterval').value);
  await fetch('/api/quota/interval', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({minutes}) });
});

async function syncQuotaInterval() {
  try {
    const res = await fetch('/api/quota/interval');
    const data = await res.json();
    const sel = document.getElementById('quotaInterval');
    const value = String(data.minutes);
    // 若值不在预设选项中（GUI 设置面板可填任意分钟），动态插入"自定义"选项
    if (![...sel.options].some(o => o.value === value)) {
      [...sel.options].forEach(o => { if (o.dataset.custom) o.remove(); });
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = `${value}m`;
      opt.dataset.custom = '1';
      sel.appendChild(opt);
    }
    if (sel.value !== value) sel.value = value;
  } catch {}
}
syncQuotaInterval();
// 跟着前端轮询节奏一起同步，让 GUI 设置面板的修改在网页上自动反映
setInterval(syncQuotaInterval, 30000);

document.getElementById('pollInterval').addEventListener('change', async () => {
  const seconds = parseInt(document.getElementById('pollInterval').value);
  await fetch('/api/poll/interval', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({seconds}) });
});

async function syncPollInterval() {
  try {
    const res = await fetch('/api/poll/interval');
    const data = await res.json();
    const sel = document.getElementById('pollInterval');
    const value = String(data.seconds);
    if (![...sel.options].some(o => o.value === value)) {
      [...sel.options].forEach(o => { if (o.dataset.custom) o.remove(); });
      const opt = document.createElement('option');
      opt.value = value;
      // 整分钟显示 Xm，否则显示 Xs
      const sec = data.seconds;
      opt.textContent = (sec >= 60 && sec % 60 === 0) ? `${sec / 60}m` : `${sec}s`;
      opt.dataset.custom = '1';
      sel.appendChild(opt);
    }
    if (sel.value !== value) sel.value = value;
  } catch {}
}
syncPollInterval();
setInterval(syncPollInterval, 30000);

document.getElementById('refreshAll').addEventListener('click', async () => {
  const btn = document.getElementById('refreshAll');
  btn.textContent = '采集中...';
  btn.disabled = true;
  try {
    await fetch('/api/collect-now', { method: 'POST' });
    await refresh();
  } finally {
    btn.textContent = '全部刷新';
    btn.disabled = false;
  }
});

refresh();
startRefresh();
</script>
</body>
</html>"""
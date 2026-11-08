import { svc } from '../service.js';
import { store } from '../store.js';
import { $, ago, download, esc, statusPill, toast } from '../ui.js';

const RANGES = [[60, 'Last hour'], [360, 'Last 6 hours'], [1440, 'Last 24 hours']];
let id, minutes = 360, points = [], stats = {}, statsTimer;

export async function mount([tankId]) {
  id = tankId;
  const tank = store.tank(id);
  if (!tank) { location.hash = '#/'; return; }

  $('#view').innerHTML = `
    <a class="back" href="#/">‹ All tanks</a>
    <h1>${esc(tank.name)}</h1><small>${esc(tank.location)}</small>
    <div class="detail">
      <div class="gauge" role="img" aria-label="Tank level">
        <div class="fill" id="fill"></div>
        <b class="tick" style="bottom:${tank.warn_pct}%"><span>Warning ${tank.warn_pct}%</span></b>
        <b class="tick" style="bottom:${tank.danger_pct}%"><span>Danger ${tank.danger_pct}%</span></b>
      </div>
      <div>
        <div class="big" id="level"></div>
        <div id="status"></div>
        <div class="leds" aria-hidden="true"><i class="led" id="led-safe"></i><i class="led yellow" id="led-warning"></i><i class="led red" id="led-danger"></i></div>
        <dl id="details"></dl>
      </div>
    </div>
    <div class="stats" id="stats"></div>
    <section class="panel chart">
      <div class="row">
        <h2>Level history</h2>
        <select id="range" aria-label="Time range">${RANGES.map(([v, n]) => `<option value="${v}"${v === minutes ? ' selected' : ''}>${n}</option>`).join('')}</select>
        <button class="ghost" id="export">Export CSV</button>
      </div>
      <div id="chart"></div>
    </section>`;

  $('#range').onchange = event => { minutes = +event.target.value; load(); };
  $('#export').onclick = exportCsv;
  paintStatus();
  await load();
  statsTimer = setInterval(loadStats, 30000);
}

export function unmount() { clearInterval(statsTimer); }

export function update(event) {
  if (event.type === 'tank' && event.tankId != id) return;
  if (event.type === 'tank' && event.point) points.push(event.point);
  paintStatus();
  paintChart();
}

async function load() {
  [points, stats] = await Promise.all([svc.history(id, minutes), svc.stats(id, minutes)]);
  paintChart();
  paintStats();
}
async function loadStats() { stats = await svc.stats(id, minutes); paintStats(); }

async function exportCsv() {
  try {
    download(await svc.exportCsv(id, minutes), `${store.tank(id).name.replace(/\s+/g, '_')}.csv`);
  } catch (error) { toast(error.message, 'danger'); }
}

function paintStatus() {
  const tank = store.tank(id);
  if (!tank || !$('#fill')) return;
  $('#fill').style.height = `${tank.level_pct}%`;
  $('#fill').className = `fill ${tank.status}`;
  $('#level').innerHTML = `${Math.round(tank.level_pct)}<i>%</i>`;
  $('#status').innerHTML = statusPill(tank.status);
  ['safe', 'warning', 'danger'].forEach(s => $(`#led-${s}`).classList.toggle('on', tank.status === s));
  const distance = tank.distance_cm ?? Math.round(tank.depth_cm * (1 - tank.level_pct / 100));
  $('#details').innerHTML = `
    <dt>Distance to sewage</dt><dd>${distance} cm</dd>
    <dt>Tank depth</dt><dd>${tank.depth_cm} cm</dd>
    <dt>Last reading</dt><dd>${ago(tank.last_seen)}</dd>
    <dt>Device</dt><dd>${tank.status === 'offline' ? 'Offline' : 'Online'}</dd>
    ${tank.rssi != null ? `<dt>Wi-Fi signal</dt><dd>${tank.rssi} dBm</dd>` : ''}`;
}

function paintStats() {
  if (!$('#stats')) return;
  const pct = v => (v == null ? '—' : `${Math.round(v)}%`);
  const eta = stats.eta_minutes;
  const etaText = eta == null ? 'Not filling' : eta >= 90 ? `${(eta / 60).toFixed(1)} h` : `${eta} min`;
  $('#stats').innerHTML = [
    [pct(stats.peak), 'Peak level'], [pct(stats.avg), 'Average level'],
    [stats.danger_events ?? '—', 'Danger events'], [etaText, 'Estimated time to full'],
  ].map(([value, label]) => `<div><b>${value}</b><small>${label}</small></div>`).join('');
}

function paintChart() {
  const tank = store.tank(id);
  if (!tank || !$('#chart')) return;
  const W = 640, H = 220, span = minutes * 60000, since = Date.now() - span;
  const shown = points.filter(p => p.ts >= since);
  if (shown.length < 2) { $('#chart').innerHTML = '<p class="muted">Not enough readings in this range yet.</p>'; return; }
  const x = p => (p.ts - since) / span * W;
  const y = level => H - level / 100 * H;
  const gridlines = [0, 50].map(v => `<line class="gridline" x1="0" x2="${W}" y1="${y(v)}" y2="${y(v)}"/><text x="4" y="${y(v) - 3}">${v}%</text>`).join('');
  $('#chart').innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Level over time with warning and danger bands">
      <rect class="band-danger" y="0" width="${W}" height="${y(tank.danger_pct)}"/>
      <rect class="band-warning" y="${y(tank.danger_pct)}" width="${W}" height="${y(tank.warn_pct) - y(tank.danger_pct)}"/>
      ${gridlines}
      <text x="4" y="${y(tank.danger_pct) - 3}">${tank.danger_pct}%</text><text x="4" y="${y(tank.warn_pct) - 3}">${tank.warn_pct}%</text>
      <polyline class="series" points="${shown.map(p => `${x(p).toFixed(1)},${y(p.level).toFixed(1)}`).join(' ')}"/>
    </svg>`;
}

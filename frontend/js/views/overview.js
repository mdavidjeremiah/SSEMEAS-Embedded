import { store } from '../store.js';
import { $, ago, esc, pill, statusPill, STATUS_ICON, STATUS_LABEL } from '../ui.js';

const card = t => `
  <a class="card ${t.status}" href="#/tank/${t.id}">
    <div class="row"><b>${esc(t.name)}</b>${statusPill(t.status)}</div>
    <small>${esc(t.location)}</small>
    <div class="level">${Math.round(t.level_pct)}<i>%</i></div>
    <div class="bar"><span style="width:${t.level_pct}%"></span><em style="left:${t.warn_pct}%"></em><em style="left:${t.danger_pct}%"></em></div>
    <small>Updated ${ago(t.last_seen)}</small>
  </a>`;

export function mount() { render(); }
export function update() { render(); }

function render() {
  const counts = { safe: 0, warning: 0, danger: 0, offline: 0 };
  store.tanks.forEach(t => counts[t.status]++);
  $('#view').innerHTML = `
    <h1>Your tanks</h1>
    <div class="summary">${Object.entries(counts).map(([s, n]) => pill(s, `${STATUS_ICON[s]} ${n} ${STATUS_LABEL[s]}`)).join('')}</div>
    <div class="grid">${store.tanks.map(card).join('') || '<p class="muted">No tanks yet. Ask an admin to assign one to you.</p>'}</div>`;
}

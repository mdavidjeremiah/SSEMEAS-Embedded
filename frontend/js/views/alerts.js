import { svc } from '../service.js';
import { store } from '../store.js';
import { $, esc, EVENT_LABEL, pill, toast } from '../ui.js';

let filter = 'all';

export function mount() { render(); }
export function update(event) { if (event.type !== 'tank') render(); }   // live readings do not change this page

function render() {
  const rows = store.alerts.filter(a => filter === 'all' || a.tank_id == filter);
  $('#view').innerHTML = `
    <div class="row">
      <h1>Alerts</h1>
      <select id="filter" style="width:auto" aria-label="Filter by tank">
        <option value="all">All tanks</option>
        ${store.tanks.map(t => `<option value="${t.id}"${t.id == filter ? ' selected' : ''}>${esc(t.name)}</option>`).join('')}
      </select>
    </div>
    <section class="panel">${rows.length ? `
      <table>
        <thead><tr><th>Time</th><th>Tank</th><th>Event</th><th>Level</th><th>WhatsApp</th><th></th></tr></thead>
        <tbody>${rows.map(row).join('')}</tbody>
      </table>` : '<p class="muted">No alerts. Warning and Danger events will appear here.</p>'}
    </section>`;

  $('#filter').onchange = event => { filter = event.target.value; render(); };
  document.querySelectorAll('[data-ack]').forEach(button => {
    button.onclick = async () => {
      try {
        await svc.acknowledge(button.dataset.ack);
        store.alerts.find(a => a.id === button.dataset.ack).acknowledged = true;
        render();
      } catch (error) { toast(error.message, 'danger'); }
    };
  });
}

const row = a => `
  <tr>
    <td>${new Date(a.ts).toLocaleString()}</td>
    <td>${esc(a.tank_name)}</td>
    <td>${pill(a.type === 'recovery' ? 'safe' : a.type, EVENT_LABEL[a.type])}</td>
    <td>${Math.round(a.level_pct)}%</td>
    <td>${esc(a.delivery)}</td>
    <td>${a.acknowledged ? 'Acknowledged' : `<button class="ghost" data-ack="${a.id}">Acknowledge</button>`}</td>
  </tr>`;

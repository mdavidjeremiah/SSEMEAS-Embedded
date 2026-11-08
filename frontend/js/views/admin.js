import { svc } from '../service.js';
import { $, esc, EVENT_LABEL, toast } from '../ui.js';

const NUMBER_FIELDS = [['depth_cm', 'Depth (cm)'], ['sensor_offset_cm', 'Sensor offset (cm)'], ['warn_pct', 'Warning %'],
                       ['danger_pct', 'Danger %'], ['hysteresis_pct', 'Hysteresis %'], ['offline_after_s', 'Offline after (s)']];
const NEW_TANK = { id: 'new', name: '', location: '', depth_cm: 180, sensor_offset_cm: 20, warn_pct: 70, danger_pct: 85, hysteresis_pct: 3, offline_after_s: 120 };

const tankForm = t => `
  <form class="tank-form" data-tank="${t.id}">
    <label>Name<input name="name" value="${esc(t.name)}" required></label>
    <label>Location<input name="location" value="${esc(t.location)}"></label>
    ${NUMBER_FIELDS.map(([key, text]) => `<label>${text}<input name="${key}" type="number" step="any" value="${t[key]}" required></label>`).join('')}
    <div class="row start">
      <button>${t.id === 'new' ? 'Add tank' : 'Save'}</button>
      ${t.id === 'new' ? '' : `<button type="button" class="ghost" data-rotate="${t.id}">New device key</button><button type="button" class="ghost" data-delete="${t.id}">Delete</button>`}
    </div>
  </form>`;

const keyBox = key => `
  <div class="keybox" role="status"><b>Device key (shown once):</b><br><code>${esc(key)}</code><br>
  <small>Put it in firmware/ssmeas_esp32/config.h as DEVICE_KEY.</small></div>`;

const userRow = (u, tanks) => `
  <tr data-user="${esc(u.email)}">
    <td>${esc(u.email)}<br><small>${u.phone ? `${esc(u.phone)} (${u.phone_verified ? 'verified' : 'not verified'})` : 'No WhatsApp number'}</small></td>
    <td><select name="role"><option${u.role === 'user' ? ' selected' : ''}>user</option><option${u.role === 'admin' ? ' selected' : ''}>admin</option></select></td>
    <td><input type="checkbox" name="active"${u.active ? ' checked' : ''} aria-label="Active"></td>
    <td>${tanks.map(t => `<label class="check"><input type="checkbox" value="${t.id}"${u.tanks.includes(t.id) ? ' checked' : ''}>${esc(t.name)}</label>`).join('')}</td>
    <td><button class="ghost" data-save-user>Save</button></td>
  </tr>`;

export async function mount() { await render(); }

async function render(notice = '') {
  let users, tanks, notifications;
  try {
    [users, tanks, notifications] = await Promise.all([svc.admin.users(), svc.admin.tanks(), svc.admin.notifications()]);
  } catch (error) {
    $('#view').innerHTML = `<h1>Admin</h1><p class="error">${esc(error.message)}</p>`;
    return;
  }
  $('#view').innerHTML = `
    <h1>Admin</h1>${notice}
    <section class="panel">
      <h2>Users</h2>
      <table>
        <thead><tr><th>Email</th><th>Role</th><th>Active</th><th>Tanks they can see</th><th></th></tr></thead>
        <tbody>${users.map(u => userRow(u, tanks)).join('')}</tbody>
      </table>
      <p class="small">Admins see every tank.</p>
    </section>
    <section class="panel">
      <h2>Tanks</h2>${tanks.map(tankForm).join('')}
      <h2 style="margin-top:1.2rem">Add a tank</h2>${tankForm(NEW_TANK)}
    </section>
    <section class="panel">
      <h2>Recent WhatsApp messages</h2>
      ${notifications.length ? `<table>
        <thead><tr><th>Time</th><th>Sent to</th><th>Tank</th><th>Event</th><th>Status</th></tr></thead>
        <tbody>${notifications.map(n => `<tr><td>${new Date(n.ts).toLocaleString()}</td><td>${esc(n.email)}</td><td>${esc(n.tank_name || '')}</td>
          <td>${EVENT_LABEL[n.type] || n.type}${n.kind === 'reminder' ? ' (reminder)' : ''}</td><td>${esc(n.state)}</td></tr>`).join('')}</tbody>
      </table>` : '<p class="muted">No messages sent yet.</p>'}
    </section>`;
  wire();
}

function wire() {
  $('#view').onclick = async event => {
    const button = event.target.closest('button');
    if (!button) return;
    try {
      if ('saveUser' in button.dataset) {
        const row = button.closest('tr');
        await svc.admin.saveUser(row.dataset.user, {
          role: row.querySelector('[name=role]').value,
          active: row.querySelector('[name=active]').checked,
          tanks: [...row.querySelectorAll('input[type=checkbox][value]:checked')].map(box => +box.value),
        });
        toast('User saved', 'safe');
      } else if (button.dataset.rotate && confirm('Make a new key? The current device stops working until you flash the new one.')) {
        render(keyBox((await svc.admin.rotateKey(button.dataset.rotate)).device_key));
      } else if (button.dataset.delete && confirm('Delete this tank and all its readings and alerts?')) {
        await svc.admin.deleteTank(button.dataset.delete);
        render();
      }
    } catch (error) { toast(error.message, 'danger'); }
  };

  document.querySelectorAll('.tank-form').forEach(form => {
    form.onsubmit = async event => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(form));
      NUMBER_FIELDS.forEach(([key]) => { data[key] = +data[key]; });
      try {
        if (form.dataset.tank === 'new') render(keyBox((await svc.admin.createTank(data)).device_key));
        else { await svc.admin.saveTank(form.dataset.tank, data); toast('Tank saved', 'safe'); }
      } catch (error) { toast(error.message, 'danger'); }
    };
  });
}

// Talks to the FastAPI backend: REST for requests, a WebSocket for live updates (polling is the fallback).
import { CONFIG } from './config.js';
import { store } from './store.js';
import { toast } from './ui.js';

let token = sessionStorage.getItem('ssmeas_token');
let socket, pollTimer;

async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(CONFIG.api + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }) },
    body: body && JSON.stringify(body),
  });
  if (response.status === 401 && token) {
    signOut();
    location.reload();
    throw new Error('Session expired. Sign in again.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : data.detail?.[0]?.msg;
    throw new Error((detail || 'Request failed').replace(/^Value error, /, ''));
  }
  return data;
}

// ---------- session ----------
export const hasSession = () => Boolean(token);
function setToken(t) { token = t; sessionStorage.setItem('ssmeas_token', t); }
export async function signIn(email, password) { setToken((await request('/auth/login', { method: 'POST', body: { email, password } })).token); }
export async function register(email, password) { setToken((await request('/auth/register', { method: 'POST', body: { email, password } })).token); }
export const forgotPassword = email => request('/auth/forgot', { method: 'POST', body: { email } });
export const resetPassword = (resetToken, password) => request('/auth/reset', { method: 'POST', body: { token: resetToken, password } });
export function signOut() {
  token = null;
  sessionStorage.removeItem('ssmeas_token');
  clearInterval(pollTimer);
  socket?.close();
}

// ---------- data + live updates ----------
async function refresh() {
  store.tanks = await request('/tanks');
  store.alerts = await request('/alerts');
  store.emit({ type: 'refresh' });
}

function connect() {
  if (!token) return;
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${CONFIG.api}/ws`);
  socket.onopen = () => socket.send(token);
  socket.onmessage = async event => {
    const message = JSON.parse(event.data);
    if (message.type === 'tank') {
      const tank = store.tank(message.tank.id);
      if (!tank) return refresh();
      Object.assign(tank, message.tank);
      store.emit({ type: 'tank', tankId: tank.id, point: message.point });
    } else if (message.type === 'alert') {
      toast(message.message, message.severity);
      store.alerts = await request('/alerts');
      store.emit({ type: 'alerts' });
    }
  };
  socket.onclose = () => { if (token) setTimeout(connect, 3000); };   // reconnect
}

export async function start() {
  store.me = await request('/me');
  await refresh();
  connect();
  pollTimer = setInterval(() => refresh().catch(() => {}), 15000);
}

export const history = (tankId, minutes) => request(`/tanks/${tankId}/readings?minutes=${minutes}`);
export const stats = (tankId, minutes) => request(`/tanks/${tankId}/stats?minutes=${minutes}`);
export const acknowledge = alertId => request(`/alerts/${alertId}/ack`, { method: 'POST' });

export async function exportCsv(tankId, minutes) {
  const response = await fetch(`${CONFIG.api}/tanks/${tankId}/export.csv?minutes=${minutes}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error('Export failed');
  return response.blob();
}

// ---------- profile ----------
export async function savePhone(number) { Object.assign(store.me, await request('/me/phone', { method: 'PUT', body: { number } })); }
export async function verifyPhone(code) { await request('/me/phone/verify', { method: 'POST', body: { code } }); store.me.phone_verified = true; }
export async function removePhone() { await request('/me/phone', { method: 'DELETE' }); Object.assign(store.me, { phone: '', phone_verified: false }); }
export const savePrefs = prefs => request('/me/prefs', { method: 'PUT', body: prefs });
export const sendTestMessage = () => request('/me/phone/test', { method: 'POST' });

// ---------- admin ----------
export const admin = {
  users: () => request('/admin/users'),
  tanks: () => request('/admin/tanks'),
  notifications: () => request('/admin/notifications'),
  saveUser: (email, patch) => request(`/admin/users/${encodeURIComponent(email)}`, { method: 'PATCH', body: patch }),
  createTank: tank => request('/admin/tanks', { method: 'POST', body: tank }),
  saveTank: (id, tank) => request(`/admin/tanks/${id}`, { method: 'PUT', body: tank }),
  rotateKey: id => request(`/admin/tanks/${id}/rotate-key`, { method: 'POST' }),
  deleteTank: id => request(`/admin/tanks/${id}`, { method: 'DELETE' }),
};

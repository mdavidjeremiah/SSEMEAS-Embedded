// Demo mode: the same functions as remote.js, but backed by a simulator running in the browser.
import { store } from './store.js';
import { toast, EVENT_LABEL } from './ui.js';

let timer;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// Same rule as the backend (backend/app/services/status.py).
function classify(level, previous, tank) {
  const h = 3;
  if (level >= tank.danger_pct || (previous === 'danger' && level >= tank.danger_pct - h)) return 'danger';
  if (level >= tank.warn_pct || (['warning', 'danger'].includes(previous) && level >= tank.warn_pct - h)) return 'warning';
  return 'safe';
}

function makeTank(id, name, location, level, extra = {}) {
  const now = Date.now();
  const tank = { id, name, location, depth_cm: 180, warn_pct: 70, danger_pct: 85, level_pct: level, last_seen: now,
                 rssi: -60, direction: 1, history: [], ...extra };
  let v = level;
  for (let i = 1; i <= 288; i++) {                      // 24 hours of history, one point every 5 minutes
    v = clamp(v + Math.random() * 2 - 1.1, 5, 95);
    tank.history.unshift({ ts: now - i * 300000, level: v });
  }
  tank.history.push({ ts: now, level });
  tank.status = tank.offline ? 'offline' : classify(level, 'safe', tank);
  return tank;
}

function tick() {
  const now = Date.now();
  for (const tank of store.tanks) {
    if (tank.offline) continue;
    tank.level_pct = clamp(tank.level_pct + tank.direction * (tank.id === 2 ? 0.9 : 0.4) + Math.random() * 0.4 - 0.2, 3, 99);
    if (tank.level_pct >= 95) tank.direction = -1;       // pretend the tank gets emptied
    if (tank.level_pct <= 20) tank.direction = 1;
    tank.last_seen = now;
    tank.distance_cm = Math.round(tank.depth_cm * (1 - tank.level_pct / 100));
    const point = { ts: now, level: tank.level_pct };
    tank.history.push(point);
    const next = classify(tank.level_pct, tank.status, tank);
    if (next !== tank.status) raiseAlert(tank, next);
    tank.status = next;
    store.emit({ type: 'tank', tankId: tank.id, point });
  }
}

function raiseAlert(tank, status) {
  const type = status === 'safe' ? 'recovery' : status;
  const prefs = store.me.prefs;
  store.alerts.unshift({ id: String(Math.random()), tank_id: tank.id, tank_name: tank.name, ts: Date.now(), type,
                         level_pct: tank.level_pct, acknowledged: false,
                         delivery: store.me.phone_verified && prefs[type] ? '1 sent' : 'Not sent' });
  toast(`${tank.name}: ${EVENT_LABEL[type].toLowerCase()} (${Math.round(tank.level_pct)}%)`, status);
  store.emit({ type: 'alerts' });
}

// ---------- session ----------
export const hasSession = () => false;
export async function signIn(email) { store.me.email = email; }
export const register = signIn;
export const forgotPassword = async () => {};
export const resetPassword = async () => {};
export function signOut() { clearInterval(timer); }

export async function start() {
  store.tanks = [
    makeTank(1, 'Home septic tank', 'Muyenga, Kampala', 42),
    makeTank(2, 'Workshop tank', 'Kampala Road', 76),
    makeTank(3, 'Block B tank', 'Ntinda', 58, { offline: true, last_seen: Date.now() - 3600000 }),
  ];
  store.alerts = [];
  store.emit();
  timer = setInterval(tick, 2000);
}

// ---------- data ----------
export async function history(tankId, minutes) {
  const since = Date.now() - minutes * 60000;
  return store.tank(tankId).history.filter(p => p.ts >= since);
}

export async function stats(tankId, minutes) {
  const tank = store.tank(tankId);
  const since = Date.now() - minutes * 60000;
  const points = tank.history.filter(p => p.ts >= since);
  const recent = tank.history.filter(p => p.ts >= Date.now() - 30 * 60000);
  let eta = null;
  if (recent.length >= 6) {
    const mean = list => list.reduce((s, p) => s + p.level, 0) / list.length;
    const rate = (mean(recent.slice(-3)) - mean(recent.slice(0, 3))) / ((recent.at(-1).ts - recent[0].ts) / 60000 || 1);
    if (rate > 0.02) eta = Math.round((100 - recent.at(-1).level) / rate);
  }
  return {
    peak: Math.max(...points.map(p => p.level)),
    avg: points.reduce((s, p) => s + p.level, 0) / (points.length || 1),
    danger_events: store.alerts.filter(a => a.tank_id == tankId && a.type === 'danger' && a.ts >= since).length,
    eta_minutes: eta,
  };
}

export async function acknowledge(alertId) { store.alerts.find(a => a.id === alertId).acknowledged = true; }

export async function exportCsv(tankId, minutes) {
  const rows = (await history(tankId, minutes)).map(p => `${new Date(p.ts).toISOString()},${p.level.toFixed(1)}`);
  return new Blob([`time_utc,level_pct\n${rows.join('\n')}`], { type: 'text/csv' });
}

// ---------- profile (kept in memory; the demo code is 123456) ----------
export async function savePhone(number) { Object.assign(store.me, { phone: number, phone_verified: false }); }
export async function verifyPhone(code) {
  if (code !== '123456') throw new Error('That code is not right. Try again.');
  store.me.phone_verified = true;
}
export async function removePhone() { Object.assign(store.me, { phone: '', phone_verified: false }); }
export async function savePrefs() {}
export async function sendTestMessage() {}

export const admin = null;   // the admin page needs the real backend

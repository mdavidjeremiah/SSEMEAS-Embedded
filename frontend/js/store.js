// The one place the current data lives. Services update it and call emit(); main.js passes events to the open view.
export const store = {
  me: { email: '', role: 'user', phone: '', phone_verified: false,
        prefs: { warning: true, danger: true, recovery: true, offline: false, quiet_on: false, quiet_from: 22, quiet_to: 6 } },
  tanks: [],
  alerts: [],
  listeners: new Set(),

  subscribe(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); },
  emit(event = { type: 'refresh' }) { this.listeners.forEach(fn => fn(event)); },
  tank(id) { return this.tanks.find(t => t.id == id); },
};

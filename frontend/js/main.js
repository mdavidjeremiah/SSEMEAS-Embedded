import { initAuth, showLogin } from './auth.js';
import { CONFIG } from './config.js';
import { svc } from './service.js';
import { store } from './store.js';
import { $ } from './ui.js';
import * as admin from './views/admin.js';
import * as alerts from './views/alerts.js';
import * as overview from './views/overview.js';
import * as settings from './views/settings.js';
import * as tank from './views/tank.js';

// Each view exports mount(params), and optionally update(event) for live data and unmount() for cleanup.
const views = { '': overview, tank, alerts, settings, admin };
let current = null;
let signedIn = false;

function route() {
  const [name = '', ...params] = (location.hash || '#/').slice(2).split('/');
  current?.unmount?.();
  current = views[name] ?? overview;
  document.querySelectorAll('nav a').forEach(a =>
    a.classList.toggle('on', a.getAttribute('href') === '#/' + (name === 'tank' ? '' : name)));
  current.mount(params);
}

async function enterApp() {
  await svc.start();
  signedIn = true;
  $('#login').hidden = true;
  $('#app').hidden = false;
  $('#admin-link').hidden = !(svc.admin && store.me.role === 'admin');
  route();
}

store.subscribe(event => signedIn && current?.update?.(event));
addEventListener('hashchange', () => signedIn && route());
$('#sign-out').onclick = () => { svc.signOut(); location.hash = ''; location.reload(); };

initAuth(enterApp);
if (!CONFIG.mock && svc.hasSession() && !location.hash.startsWith('#reset/')) {
  enterApp().catch(() => { svc.signOut(); showLogin(); });
} else {
  showLogin();
  if (location.hash.startsWith('#reset/')) { $('#login-form').hidden = true; $('#reset-form').hidden = false; }
}

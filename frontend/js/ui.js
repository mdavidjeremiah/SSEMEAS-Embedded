export const $ = selector => document.querySelector(selector);

export const esc = text => String(text ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export const STATUS_LABEL = { safe: 'Safe', warning: 'Warning', danger: 'Danger', offline: 'Offline' };
// A shape as well as a colour, so status never relies on colour alone.
export const STATUS_ICON = { safe: '●', warning: '▲', danger: '■', offline: '○' };
export const EVENT_LABEL = { warning: 'Reached Warning', danger: 'Reached Danger', recovery: 'Back to Safe', offline: 'Device offline' };

export const pill = (cls, text) => `<span class="pill ${cls}">${text}</span>`;
export const statusPill = status => pill(status, `${STATUS_ICON[status]} ${STATUS_LABEL[status]}`);

export function ago(ts) {
  const seconds = Math.max(0, (Date.now() - ts) / 1000 | 0);
  if (seconds < 10) return 'just now';
  if (seconds < 60) return `${seconds} s ago`;
  if (seconds < 3600) return `${seconds / 60 | 0} min ago`;
  return `${seconds / 3600 | 0} h ago`;
}

export function toast(message, kind = '') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = message;
  $('#toasts').append(el);
  setTimeout(() => el.remove(), 7000);
}

export function download(blob, filename) {
  const link = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: filename });
  link.click();
  URL.revokeObjectURL(link.href);
}

export const hourOptions = selected =>
  [...Array(24).keys()].map(h => `<option value="${h}"${h === selected ? ' selected' : ''}>${String(h).padStart(2, '0')}:00</option>`).join('');

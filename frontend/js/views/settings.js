import { svc } from '../service.js';
import { store } from '../store.js';
import { $, esc, hourOptions, pill, toast } from '../ui.js';

const COUNTRIES = [['+256', 'UG'], ['+254', 'KE'], ['+255', 'TZ'], ['+250', 'RW'], ['+44', 'UK'], ['+1', 'US']];
const EVENTS = [['warning', 'A tank reaches Warning'], ['danger', 'A tank reaches Danger'],
                ['recovery', 'A tank is back to Safe'], ['offline', 'A device goes offline']];
let waitingForCode = false;

export function mount() { render(); }

function render() {
  const { phone, phone_verified: verified, prefs } = store.me;
  $('#view').innerHTML = `
    <h1>Settings</h1>
    <section class="panel">
      <h2>WhatsApp alerts</h2>
      <p class="muted">Get tank alerts on WhatsApp. We send a code to confirm the number is yours. You can remove it any time.</p>
      <p><b>${phone ? esc(phone) : 'No number added'}</b> ${phone ? pill(verified ? 'safe' : 'warning', verified ? 'Verified' : 'Not verified') : ''}</p>
      <form id="phone-form">
        <label>Phone number
          <div class="phone">
            <select id="country" aria-label="Country code">${COUNTRIES.map(([c, n]) => `<option value="${c}">${n} ${c}</option>`).join('')}</select>
            <input id="national" inputmode="tel" autocomplete="tel-national" placeholder="772 123456" required>
          </div>
        </label>
        <p id="phone-error" class="error" role="alert"></p>
        <button>Send code</button>
        ${phone ? '<button type="button" id="remove" class="ghost">Remove number</button>' : ''}
      </form>
      <form id="code-form" ${waitingForCode && !verified ? '' : 'hidden'}>
        <label>6-digit code<input id="code" inputmode="numeric" maxlength="6" pattern="\\d{6}" required></label>
        <button>Verify number</button>
      </form>
    </section>
    <section class="panel">
      <h2>Send me a message when</h2>
      <form id="prefs-form">
        ${EVENTS.map(([key, text]) => `<label class="check"><input type="checkbox" name="${key}"${prefs[key] ? ' checked' : ''}>${text}</label>`).join('')}
        <label class="check"><input type="checkbox" name="quiet_on"${prefs.quiet_on ? ' checked' : ''}>Mute Warning messages overnight (Danger always sends)</label>
        <div class="phone">
          <label>From<select name="quiet_from">${hourOptions(prefs.quiet_from)}</select></label>
          <label>To<select name="quiet_to">${hourOptions(prefs.quiet_to)}</select></label>
        </div>
        <div class="row start" style="margin-top:1rem">
          <button>Save preferences</button>
          <button type="button" id="test" class="ghost"${verified ? '' : ' disabled'}>Send test message</button>
        </div>
      </form>
    </section>`;
  wire();
}

// Runs an action; shows any error under the phone form and as a toast.
const guarded = action => async event => {
  event?.preventDefault();
  $('#phone-error').textContent = '';
  try { await action(); } catch (error) { $('#phone-error').textContent = error.message; toast(error.message, 'danger'); }
};

function wire() {
  $('#phone-form').onsubmit = guarded(async () => {
    const number = $('#country').value + $('#national').value.replace(/[\s-]/g, '').replace(/^0/, '');
    if (!/^\+[1-9]\d{7,14}$/.test(number)) throw new Error('Enter a valid number, for example 772 123456.');
    await svc.savePhone(number);
    waitingForCode = true;
    render();
    toast('Code sent on WhatsApp (demo mode: use 123456)', 'safe');
  });

  $('#code-form').onsubmit = guarded(async () => {
    await svc.verifyPhone($('#code').value);
    waitingForCode = false;
    render();
    toast('Number verified', 'safe');
  });

  $('#prefs-form').onsubmit = guarded(async () => {
    const form = new FormData($('#prefs-form'));
    const prefs = store.me.prefs;
    [...EVENTS.map(([key]) => key), 'quiet_on'].forEach(key => { prefs[key] = form.has(key); });
    prefs.quiet_from = +form.get('quiet_from');
    prefs.quiet_to = +form.get('quiet_to');
    await svc.savePrefs(prefs);
    toast('Preferences saved', 'safe');
  });

  $('#test').onclick = guarded(async () => { await svc.sendTestMessage(); toast('Test message sent', 'safe'); });
  $('#remove')?.addEventListener('click', guarded(async () => { await svc.removePhone(); waitingForCode = false; render(); }));
}

import { CONFIG } from './config.js';
import { svc } from './service.js';
import { $, toast } from './ui.js';

export function showLogin() {
  $('#app').hidden = true;
  $('#login').hidden = false;
}

export function initAuth(enterApp) {
  $('#forgot').hidden = CONFIG.mock;
  $('#demo-hint').textContent = CONFIG.mock ? 'Demo mode: any email and password works.' : '';

  async function attempt(action) {
    $('#login-error').textContent = '';
    try {
      await action($('#email').value, $('#password').value);
      await enterApp();
    } catch (error) {
      $('#login-error').textContent = error.message;
    }
  }

  $('#login-form').onsubmit = event => { event.preventDefault(); attempt(svc.signIn); };
  $('#register').onclick = () => $('#login-form').reportValidity() && attempt(svc.register);

  $('#forgot').onclick = async event => {
    event.preventDefault();
    const email = $('#email').value;
    if (!email) { $('#login-error').textContent = 'Enter your email above, then choose Forgot password.'; return; }
    try {
      await svc.forgotPassword(email);
      $('#login-error').textContent = '';
      toast('If that email has an account, a reset link is on its way.', 'safe');
    } catch (error) {
      $('#login-error').textContent = error.message;
    }
  };

  // The emailed link looks like  /#reset/<token>
  if (location.hash.startsWith('#reset/')) {
    $('#login-form').hidden = true;
    $('#reset-form').hidden = false;
    showLogin();
  }
  $('#reset-form').onsubmit = async event => {
    event.preventDefault();
    try {
      await svc.resetPassword(location.hash.slice('#reset/'.length), $('#new-password').value);
      location.hash = '';
      $('#reset-form').hidden = true;
      $('#login-form').hidden = false;
      toast('Password changed. Sign in with the new one.', 'safe');
    } catch (error) {
      $('#reset-error').textContent = error.message;
    }
  };
}

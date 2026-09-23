/**
 * Auth accessors — the ONLY data access point for authentication
 * (data-layer rule: components never fetch directly).
 *
 * Talks to the real Django API (/api/v1/auth/...) with session cookies.
 * Error convention (§8): throws Error with .status and .data
 * ({error, detail?, field_errors?}) so pages render server messages.
 */

const BASE = '/api/v1/auth';

async function request(path, { method = 'GET', body, csrf } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (csrf) headers['X-CSRFToken'] = csrf;

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data;
  try {
    data = await response.json();
  } catch {
    data = null; // empty body (e.g. some 204s)
  }

  if (!response.ok) {
    const error = new Error(data?.detail || data?.error || 'Request failed');
    error.status = response.status;
    error.data = data || {};
    throw error;
  }
  return data;
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/** Fetches a fresh CSRF cookie and returns its token (needed for unsafe methods). */
export async function ensureCsrfToken() {
  await request('/csrf');
  return readCookie('csrftoken');
}

export async function register(payload) {
  const csrf = await ensureCsrfToken();
  return request('/register', { method: 'POST', body: payload, csrf });
}

export async function login(email, password) {
  const csrf = await ensureCsrfToken();
  return request('/login', { method: 'POST', body: { email, password }, csrf });
}

export async function logout() {
  const csrf = await ensureCsrfToken();
  return request('/logout', { method: 'POST', csrf });
}

export function fetchMe() {
  return request('/me');
}

export async function updateMe(payload) {
  const csrf = await ensureCsrfToken();
  return request('/me', { method: 'PATCH', body: payload, csrf });
}

export async function changePassword(currentPassword, newPassword) {
  const csrf = await ensureCsrfToken();
  return request('/change-password', {
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword },
    csrf,
  });
}

export function requestPasswordReset(email) {
  return request('/password-reset', { method: 'POST', body: { email } });
}

export function confirmPasswordReset(uid, token, new_password) {
  return request('/password-reset-confirm', {
    method: 'POST',
    body: { uid, token, new_password },
  });
}

export function verifyEmail(uid, token) {
  return request(`/verify-email?uid=${encodeURIComponent(uid)}&token=${encodeURIComponent(token)}`);
}

export function fetchAddresses() {
  return request('/addresses/');
}

export async function createAddress(payload) {
  const csrf = await ensureCsrfToken();
  return request('/addresses/', { method: 'POST', body: payload, csrf });
}

export async function deleteAddress(id) {
  const csrf = await ensureCsrfToken();
  return request(`/addresses/${id}/`, { method: 'DELETE', csrf });
}

export function fetchNotificationPreferences() {
  return request('/notification-preferences');
}

export async function updateNotificationPreferences(payload) {
  const csrf = await ensureCsrfToken();
  return request('/notification-preferences', { method: 'PUT', body: payload, csrf });
}

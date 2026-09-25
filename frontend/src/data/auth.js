/**
 * Auth accessors — the ONLY data access point for authentication
 * (data-layer rule: components never fetch directly).
 *
 * Talks to the real Django API (/api/v1/auth/...) with session cookies.
 * Fetch plumbing + error convention (§8) live in lib/api.js.
 */

import { ensureCsrfToken, request } from "../lib/api";

const BASE = "/api/v1/auth";

export { ensureCsrfToken };

export async function register(payload) {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/register", { method: "POST", body: payload, csrf });
}

export async function login(email, password) {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/login", { method: "POST", body: { email, password }, csrf });
}

export async function logout() {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/logout", { method: "POST", csrf });
}

export function fetchMe() {
  return request(BASE, "/me");
}

export async function updateMe(payload) {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/me", { method: "PATCH", body: payload, csrf });
}

export async function changePassword(currentPassword, newPassword) {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/change-password", {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
    csrf,
  });
}

export function requestPasswordReset(email) {
  return request(BASE, "/password-reset", { method: "POST", body: { email } });
}

export function confirmPasswordReset(uid, token, new_password) {
  return request(BASE, "/password-reset-confirm", {
    method: "POST",
    body: { uid, token, new_password },
  });
}

export function verifyEmail(uid, token) {
  return request(BASE, `/verify-email?uid=${encodeURIComponent(uid)}&token=${encodeURIComponent(token)}`);
}

export function fetchAddresses() {
  return request(BASE, "/addresses/");
}

export async function createAddress(payload) {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/addresses/", { method: "POST", body: payload, csrf });
}

export async function deleteAddress(id) {
  const csrf = await ensureCsrfToken();
  return request(BASE, `/addresses/${id}/`, { method: "DELETE", csrf });
}

export async function updateAddress(id, payload) {
  const csrf = await ensureCsrfToken();
  return request(BASE, `/addresses/${id}/`, { method: "PATCH", body: payload, csrf });
}

export function fetchNotificationPreferences() {
  return request(BASE, "/notification-preferences");
}

export async function updateNotificationPreferences(payload) {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/notification-preferences", { method: "PUT", body: payload, csrf });
}

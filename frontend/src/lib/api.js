/**
 * Shared fetch plumbing for data/ accessors (data-layer rule).
 * Handles session cookies, CSRF, and the §8 error convention:
 * throws Error with .status and .data ({error, detail?, field_errors?})
 * so pages render server messages.
 */

export async function request(base, path, { method = "GET", body, csrf } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (csrf) headers["X-CSRFToken"] = csrf;

  const response = await fetch(`${base}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data;
  try {
    data = await response.json();
  } catch {
    data = null; // empty body (e.g. some 204s)
  }

  if (!response.ok) {
    const error = new Error(data?.detail || data?.error || "Request failed");
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

/** Fetches a fresh CSRF cookie and returns its token (unsafe methods). */
export async function ensureCsrfToken() {
  await request("/api/v1/auth", "/csrf");
  return readCookie("csrftoken");
}
/**
 * Store accessors — the ONLY data access point for stores (Phase 4).
 * Same conventions as auth.js: session cookies, CSRF on unsafe methods,
 * §8 error envelope. Public storefront works logged-out (AllowAny).
 */

import { ensureCsrfToken, request } from "../lib/api";

const BASE = "/api/v1/stores";

export async function applyAsSeller(payload) {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/apply", { method: "POST", body: payload, csrf });
}

export function fetchMyStore() {
  return request(BASE, "/my/store");
}

export async function updateMyStore(payload) {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/my/store", { method: "PATCH", body: payload, csrf });
}

export function fetchPublicStore(slug) {
  return request(BASE, `/public/${encodeURIComponent(slug)}/`);
}

/**
 * Public store directory (Phase 6 discovery) — active stores only,
 * {count, items} envelope like every list endpoint.
 */
export async function fetchPublicStores({ page = "", pageSize = "" } = {}) {
  const params = new URLSearchParams();
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(BASE, `/public/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: data.items ?? [],
  };
}
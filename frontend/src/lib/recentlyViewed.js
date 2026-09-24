/**
 * Recently viewed foundation (Phase 6.1) — client-side only for now.
 *
 * Stores a light snapshot of the product contract so Home can render
 * cards without refetching; a server-side history is a later concern.
 * Storage failures are swallowed — the feature simply stays empty.
 */

const KEY = "jeyvro.recentlyViewed";
const LIMIT = 8;

export function getRecentlyViewed() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY));
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

export function recordRecentlyViewed(product) {
  if (!product?.id) return;
  const snapshot = { ...product };
  delete snapshot.description;
  delete snapshot.images;
  delete snapshot.variants;
  try {
    const next = [
      snapshot,
      ...getRecentlyViewed().filter((item) => item.id !== product.id),
    ].slice(0, LIMIT);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Storage unavailable (private mode, quota) — skip quietly.
  }
}
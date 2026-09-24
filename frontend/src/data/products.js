/**
 * Catalog accessors — the ONLY data access point for products.
 *
 * Swapped to the real Django API (Phase 5): same shapes as the old mock
 * contract, so components did not change (data-layer rule). Search /
 * filter / sort run server-side (marketplace-catalog rule 3) — the old
 * client-side filtering is gone.
 *
 * Shape mapping (API → component contract): id=slug, price/originalPrice
 * are server-resolved numbers, rating=null renders as "no ratings yet",
 * seed is a presentation-only placeholder derived from the id.
 */

import { request } from "../lib/api";

const BASE = "/api/v1/catalog/products/";

function hashSeed(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) % 100000;
  }
  return hash % 6;
}

function toContract(item) {
  return {
    id: item.slug,
    seed: hashSeed(item.slug),
    title: item.title,
    price: item.price,
    originalPrice: item.originalPrice ?? undefined,
    discount: item.discount ?? 0,
    rating: item.rating ?? 0,
    sold: item.sold ?? 0,
    stock: item.stock,
    store: item.store_name,
    storeSlug: item.store_slug,
    verified: Boolean(item.store_verified),
    isNew: Boolean(item.isNew),
    category: item.category ?? "",
    image: item.primary_image ?? null,
  };
}

export async function getProducts({ q = "", store = "", category = "", sort = "" } = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (store) params.set("store", store);
  if (category) params.set("category", category);
  if (sort) params.set("sort", sort);
  const query = params.toString();
  const data = await request(BASE, query ? `?${query}` : "");
  return data.items.map(toContract);
}

export async function getProductById(slug) {
  try {
    const item = await request(BASE, `${encodeURIComponent(slug)}/`);
    return toContract(item);
  } catch (err) {
    if (err.status === 404) return null;
    throw err;
  }
}

/** Public categories (server truth — never hardcoded in components). */
export function getCategories() {
  return request("/api/v1/catalog/categories/");
}

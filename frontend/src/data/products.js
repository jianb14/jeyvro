/**
 * Catalog accessors — the ONLY data access point for products.
 *
 * Real Django API only (Phase 5 swap). Search / filter / sort / pagination
 * all run server-side (marketplace-catalog rule 3) — list responses keep
 * the {count, items} envelope so pages can paginate against `count`.
 *
 * Shape mapping (API → component contract): id=slug, price/originalPrice
 * are server-resolved numbers, rating=null renders as "no ratings yet",
 * seed is a presentation-only placeholder derived from the id. Variant
 * prices arrive as Decimal strings — converted here, never in components
 * (data-layer rule). `mapProduct` and `hashSeed` are exported so the
 * cart/wishlist accessors map the same product shape the same way.
 */

import { request } from "../lib/api";

const BASE = "/api/v1/catalog/products/";

export function hashSeed(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) % 100000;
  }
  return hash % 6;
}

export function mapProduct(item) {
  return {
    id: item.slug,
    seed: hashSeed(item.slug),
    title: item.title,
    description: item.description ?? "",
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
    categorySlug: item.category_slug ?? "",
    image: item.primary_image ?? null,
    images: (item.images ?? []).map((image) => image.image),
    variants: (item.variants ?? []).map((variant) => ({
      id: variant.id,
      sku: variant.sku,
      name: variant.name || variant.sku,
      price: Number(variant.price),
      isDefault: Boolean(variant.is_default),
      active: Boolean(variant.is_active),
      stock: variant.inventory?.available ?? 0,
      lowStockThreshold: variant.inventory?.low_stock_threshold ?? 5,
    })),
  };
}

/**
 * Server-side product discovery — returns the {count, items} envelope
 * with contract-shaped items. `sort` accepts the server's map:
 * newest | price | -price | title | discount.
 */
export async function getProducts({
  q = "",
  store = "",
  category = "",
  sort = "",
  minPrice = "",
  maxPrice = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (store) params.set("store", store);
  if (category) params.set("category", category);
  if (sort) params.set("sort", sort);
  if (minPrice !== "" && minPrice != null) params.set("min_price", minPrice);
  if (maxPrice !== "" && maxPrice != null) params.set("max_price", maxPrice);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(BASE, query ? `?${query}` : "");
  return {
    count: data.count ?? data.items.length,
    items: data.items.map(mapProduct),
  };
}

export async function getProductById(slug) {
  try {
    const item = await request(BASE, `${encodeURIComponent(slug)}/`);
    return mapProduct(item);
  } catch (err) {
    if (err.status === 404) return null;
    throw err;
  }
}

/**
 * Public categories (server truth — never hardcoded in components).
 * Parent id is kept so callers can build the tree.
 */
export async function getCategories() {
  const data = await request("/api/v1/catalog/categories/");
  const items = data.items ?? data;
  return items.map((category) => ({
    id: category.id,
    parent: category.parent,
    name: category.name,
    slug: category.slug,
  }));
}

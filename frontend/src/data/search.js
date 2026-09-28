/**
 * Search accessors — the ONLY data access point for Phase 18 discovery.
 *
 * Covers the two `apps.search` surfaces (§18.1): ranked, faceted product
 * search (`GET /api/v1/search/`) and autocomplete (`GET /api/v1/search/suggest/`).
 * The catalog list in `products.js` stays exactly where it was — that one
 * answers "show me this category", this one answers "find me this" — so a
 * category page and a keyword page can evolve independently instead of one
 * endpoint slowly growing every optional filter the other one needs.
 *
 * Parsing happens here, never in components (data-layer rule): products run
 * through the catalog's own `mapProduct` so a search card and a browse card
 * are literally the same shape, and facet rows become a plain camelCase
 * contract instead of leaking the API's snake_case into render code.
 */

import { request } from "../lib/api";
import { mapProduct } from "./products";

const BASE = "/api/v1/search/";
const SUGGEST = "/api/v1/search/suggest/";

// Mirrored for efficiency, never trusted: the server re-validates both limits
// and answers 400 with the §8 envelope. Holding them here just saves a round
// trip on a keystroke the server was going to refuse anyway.
export const MAX_QUERY_LENGTH = 120;
export const MIN_SUGGEST_LENGTH = 2;

/**
 * Sort keys `apps.search` accepts — deliberately *not* the catalog's list.
 * The catalog orders by column, search orders by relevance/price/rating, so a
 * value valid on one endpoint is a 400 on the other.
 */
export const SEARCH_SORTS = [
  "relevance",
  "newest",
  "price_asc",
  "price_desc",
  "rating",
];

function mapStore(store) {
  return {
    slug: store.slug,
    name: store.name,
    logo: store.logo_url ?? null,
    rating: store.rating ?? null,
    productCount: store.product_count ?? 0,
  };
}

function mapCategory(category) {
  return {
    slug: category.slug,
    name: category.name,
    productCount: category.product_count ?? 0,
  };
}

function mapFacets(facets) {
  const source = facets ?? {};
  return {
    categories: (source.categories ?? []).map((row) => ({
      slug: row.slug,
      name: row.name,
      count: row.count ?? 0,
    })),
    brands: (source.brands ?? []).map((row) => ({
      slug: row.slug,
      name: row.name,
      count: row.count ?? 0,
    })),
    prices: (source.prices ?? []).map((row) => ({
      label: row.label,
      min: row.min,
      max: row.max,
      count: row.count ?? 0,
    })),
    ratings: (source.ratings ?? []).map((row) => ({
      label: row.label,
      min: row.min,
      count: row.count ?? 0,
    })),
    stock: {
      total: source.in_stock?.total ?? 0,
      inStock: source.in_stock?.in_stock ?? 0,
      outOfStock: source.in_stock?.out_of_stock ?? 0,
    },
  };
}

/**
 * Ranked, filtered, faceted search. Returns the §8 `{count, items}` envelope
 * plus everything the facet sidebar and the companion strips need, so a page
 * makes exactly one request for the whole screen.
 *
 * `fuzzy` comes back true when the strict pass found nothing and the typo
 * fallback rescued the query — the UI must say so, or a shopper has no way to
 * tell "no results" from "close results".
 */
export async function searchResults({
  q = "",
  store = "",
  category = "",
  brand = "",
  minPrice = "",
  maxPrice = "",
  minRating = "",
  inStock = "",
  sort = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (store) params.set("store", store);
  if (category) params.set("category", category);
  if (brand) params.set("brand", brand);
  if (minPrice !== "" && minPrice != null) params.set("min_price", minPrice);
  if (maxPrice !== "" && maxPrice != null) params.set("max_price", maxPrice);
  if (minRating !== "" && minRating != null) params.set("min_rating", minRating);
  if (inStock) params.set("in_stock", String(inStock));
  if (sort) params.set("sort", sort);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);

  const query = params.toString();
  const data = await request(BASE, query ? `?${query}` : "");

  return {
    query: data.query ?? "",
    count: data.count ?? (data.items ?? []).length,
    fuzzy: Boolean(data.fuzzy),
    items: (data.items ?? []).map(mapProduct),
    stores: (data.stores ?? []).map(mapStore),
    categories: (data.categories ?? []).map(mapCategory),
    facets: mapFacets(data.facets),
  };
}

/**
 * Autocomplete for the search box — prefix matches, grouped by entity, and
 * deliberately lean (a title and a link, never a product card).
 *
 * Below `MIN_SUGGEST_LENGTH` this returns empty groups rather than calling the
 * API: one character is a shopper mid-word, not a request, and a single
 * keystroke must never reach the server.
 */
export async function getSuggestions(needle) {
  const q = (needle ?? "").trim();
  const empty = { query: q, products: [], stores: [], categories: [] };
  if (q.length < MIN_SUGGEST_LENGTH || q.length > MAX_QUERY_LENGTH) return empty;

  const data = await request(SUGGEST, `?${new URLSearchParams({ q })}`);
  return {
    query: data.query ?? q,
    products: (data.products ?? []).map((product) => ({
      slug: product.slug,
      title: product.title,
      storeName: product.store_name ?? "",
    })),
    stores: (data.stores ?? []).map(mapStore),
    categories: (data.categories ?? []).map(mapCategory),
  };
}

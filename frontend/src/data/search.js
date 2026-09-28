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
 *
 * §18.3 Discovery adds the third surface, `recommendations/`, and it lives in
 * this same file for the reason §18.1 put search here: a "you may also like"
 * shelf that goes through a different mapper than the grid beside it is a
 * shelf that eventually renders differently from the grid beside it.
 */

import { request } from "../lib/api";
import { mapProduct } from "./products";

const BASE = "/api/v1/search/";
const SUGGEST = "/api/v1/search/suggest/";
const RECOMMEND = "/api/v1/search/recommendations/";

// Mirrored for efficiency, never trusted: the server re-validates both limits
// and answers 400 with the §8 envelope. Holding them here just saves a round
// trip on a keystroke the server was going to refuse anyway.
export const MAX_QUERY_LENGTH = 120;
export const MIN_SUGGEST_LENGTH = 2;

// §18.3 shelf kinds, in the order they appear in the roadmap. Mirrored for the
// same reason: the server owns the real list and answers 400 on anything else.
export const RECOMMENDATION_KINDS = [
  "trending",
  "popular",
  "related",
  "similar",
  "personalized",
];

/** A kind that needs a `seed`, or `seen` for personalized, before it can run. */
export const SEEDED_KINDS = ["related", "similar"];

// Mirrors `apps.search.services`. `seen` is trimmed client-side because the
// history is a growing local list: sending 30 slugs to a 20-slug cap would be
// a guaranteed 400, and the tail is the *oldest* view anyway.
export const MAX_SEEN_SLUGS = 20;
export const MAX_RECOMMENDATION_LIMIT = 48;

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

/**
 * A §18.3 discovery shelf — trending, popular, related, similar or personalized
 * — as `{kind, items}` with items already through the catalog's `mapProduct`.
 *
 * `kind` is echoed back from the response rather than the argument, so a shelf
 * can never render under a heading it was not actually served (the server
 * answers with the kind it ranked for, and is the only authority on it).
 *
 * The seeded kinds are refused *here* when the caller has no seed, and
 * `personalized` is refused when the browser has no history. The server rejects
 * both with a 400, and in each case the right answer is an empty shelf rather
 * than an error — "related" with nothing to be related to is not a failure the
 * shopper should be shown, and their own history being empty is the normal
 * state of a first visit, not a fault.
 */
export async function recommendations({
  kind = "trending",
  seed = "",
  seen = [],
  limit = "",
} = {}) {
  const history = (Array.isArray(seen) ? seen : [])
    .map((slug) => (slug ?? "").trim())
    .filter(Boolean)
    .slice(0, MAX_SEEN_SLUGS);

  if (SEEDED_KINDS.includes(kind) && !seed) return { kind, items: [] };
  if (kind === "personalized" && history.length === 0) return { kind, items: [] };

  const params = new URLSearchParams();
  params.set("kind", kind);
  if (seed) params.set("seed", seed);
  if (history.length > 0) params.set("seen", history.join(","));
  if (limit) params.set("limit", String(limit));

  const data = await request(RECOMMEND, `?${params}`);
  return {
    kind: data.kind ?? kind,
    items: (data.items ?? []).map(mapProduct),
  };
}

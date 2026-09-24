/**
 * Wishlist accessors — the ONLY data access point for saved products.
 *
 * Wishlist is private per customer (marketplace-community rule 5): every
 * call rides the session and the API scopes rows to the requesting user.
 * Products map through the shared product mapper so wishlist cards render
 * the exact same contract as the catalog.
 */

import { ensureCsrfToken, request } from "../lib/api";
import { mapProduct } from "./products";

const BASE = "/api/v1/wishlist";

function mapEntry(entry) {
  return {
    id: entry.id,
    productId: entry.product?.slug ?? null,
    addedAt: entry.created_at,
    available: Boolean(entry.available),
    product: entry.product ? mapProduct(entry.product) : null,
  };
}

export async function fetchWishlist({ page = "", pageSize = "" } = {}) {
  const params = new URLSearchParams();
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(BASE, `/${query ? `?${query}` : ""}`);
  const items = (data.items ?? []).map(mapEntry);
  return { count: data.count ?? items.length, items };
}

export async function addToWishlist(productId) {
  const csrf = await ensureCsrfToken();
  return mapEntry(
    await request(BASE, "/", {
      method: "POST",
      body: { product_id: productId },
      csrf,
    })
  );
}

export async function removeFromWishlist(productId) {
  const csrf = await ensureCsrfToken();
  return request(BASE, `/items/${encodeURIComponent(productId)}`, {
    method: "DELETE",
    csrf,
  });
}

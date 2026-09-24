/**
 * Cart accessors — the ONLY data access point for the cart (data-layer).
 *
 * The API recomputes everything server-side on every call (§6): live
 * prices, live stock, line totals, store groups, and totals. This module
 * only maps that payload into the component contract — components render
 * these numbers and never recompute them (marketplace-orders rule 1).
 * Guest carts ride the session cookie; login merges them server-side.
 */

import { ensureCsrfToken, request } from "../lib/api";
import { hashSeed } from "./products";

const BASE = "/api/v1/cart";

function mapItem(item) {
  return {
    id: item.id,
    variantId: item.variant_id,
    productSlug: item.product_slug,
    title: item.title,
    variant: item.variant_name,
    sku: item.sku,
    price: item.price,
    originalPrice: item.compare_at_price ?? undefined,
    discount: item.discount ?? 0,
    qty: item.quantity,
    lineTotal: item.line_total,
    stock: item.available,
    purchasable: Boolean(item.purchasable),
    unavailableReason: item.unavailable_reason || "",
    stockLimited: Boolean(item.stock_limited),
    image: item.primary_image,
    seed: hashSeed(item.product_slug || item.sku || ""),
    storeSlug: item.store_slug,
    storeName: item.store_name,
  };
}

function mapCart(data) {
  const items = (data.items ?? []).map(mapItem);
  return {
    id: data.id,
    owner: data.owner, // "guest" | "user"
    items,
    groups: (data.groups ?? []).map((group) => ({
      storeSlug: group.store_slug,
      storeName: group.store_name,
      itemCount: group.item_count,
      subtotal: group.subtotal,
      items: (group.items ?? []).map(mapItem),
    })),
    totals: {
      lineCount: data.totals?.line_count ?? items.length,
      itemCount: data.totals?.item_count ?? 0,
      subtotal: data.totals?.subtotal ?? 0,
      savings: data.totals?.savings ?? 0,
    },
  };
}

export async function fetchCart() {
  return mapCart(await request(BASE, "/"));
}

export async function addCartItem(variantId, quantity = 1) {
  const csrf = await ensureCsrfToken();
  return mapCart(
    await request(BASE, "/items", {
      method: "POST",
      body: { variant_id: variantId, quantity },
      csrf,
    })
  );
}

export async function updateCartItem(itemId, quantity) {
  const csrf = await ensureCsrfToken();
  return mapCart(
    await request(BASE, `/items/${itemId}`, {
      method: "PATCH",
      body: { quantity },
      csrf,
    })
  );
}

export async function removeCartItem(itemId) {
  const csrf = await ensureCsrfToken();
  return mapCart(
    await request(BASE, `/items/${itemId}`, { method: "DELETE", csrf })
  );
}

export async function clearCart() {
  const csrf = await ensureCsrfToken();
  return mapCart(await request(BASE, "/", { method: "DELETE", csrf }));
}

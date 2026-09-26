/**
 * Seller operations accessors (Phase 12) — the ONLY data access point for
 * the seller dashboard, product/variant management, inventory, and seller
 * orders. Same conventions as the other data modules: session cookies,
 * CSRF on unsafe methods, the §8 error envelope, and every shape mapped
 * here so components render API truth and never recompute numbers
 * (marketplace-sellers rule 5).
 */

import { ensureCsrfToken, request } from "../lib/api";
import { mapSellerOrder } from "./orders";

const STORES = "/api/v1/stores";
const CATALOG = "/api/v1/catalog";
const BASE = "/api/v1";

// --- Shape mapping ---------------------------------------------------------

export function mapInventory(inventory) {
  if (!inventory) return null;
  return {
    onHand: inventory.on_hand,
    reserved: inventory.reserved,
    available: inventory.available,
    lowStockThreshold: inventory.low_stock_threshold,
    lowStock: Boolean(inventory.low_stock),
  };
}

export function mapSellerVariant(variant) {
  return {
    id: variant.id,
    sku: variant.sku,
    name: variant.name ?? "",
    price: Number(variant.price),
    isDefault: Boolean(variant.is_default),
    isActive: Boolean(variant.is_active),
    inventory: mapInventory(variant.inventory),
  };
}

export function mapSellerProduct(item) {
  const variants = (item.variants ?? []).map(mapSellerVariant);
  return {
    id: item.id,
    title: item.title,
    slug: item.slug,
    description: item.description ?? "",
    status: item.status,
    rejectionReason: item.rejection_reason ?? "",
    basePrice: item.base_price,
    compareAtPrice: item.compare_at_price ?? null,
    displayPrice: item.display_price,
    discountPercent: item.discount_percent ?? 0,
    category: item.category ?? null,
    brand: item.brand ?? null,
    variants,
    stockTotal: variants.reduce(
      (total, variant) =>
        variant.isActive ? total + (variant.inventory?.available ?? 0) : total,
      0
    ),
    images: (item.images ?? []).map((image) => ({
      id: image.id,
      url: image.image,
      altText: image.alt_text ?? "",
      position: image.position ?? 0,
    })),
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

export function mapInventoryRow(row) {
  return {
    variantId: row.variant_id,
    productId: row.product_id,
    productTitle: row.product_title,
    productSlug: row.product_slug,
    productStatus: row.product_status,
    sku: row.sku,
    name: row.name ?? "",
    price: Number(row.price),
    isActive: Boolean(row.is_active),
    inventory: mapInventory(row.inventory),
  };
}

// --- 12.1 Dashboard --------------------------------------------------------

export async function fetchDashboard() {
  const data = await request(STORES, "/my/dashboard");
  return {
    store: {
      name: data.store?.name ?? "",
      slug: data.store?.slug ?? "",
      status: data.store?.status ?? "",
    },
    products: {
      total: data.products?.total ?? 0,
      byStatus: data.products?.by_status ?? {},
    },
    sales: {
      orders: data.sales?.orders ?? 0,
      unitsSold: data.sales?.units_sold ?? 0,
      gross: data.sales?.gross ?? 0,
      averageOrderValue: data.sales?.average_order_value ?? 0,
      last30Days: {
        orders: data.sales?.last_30_days?.orders ?? 0,
        unitsSold: data.sales?.last_30_days?.units_sold ?? 0,
        gross: data.sales?.last_30_days?.gross ?? 0,
      },
    },
    orders: {
      total: data.orders?.total ?? 0,
      open: data.orders?.open ?? 0,
      byStatus: data.orders?.by_status ?? {},
    },
    inventory: {
      lowStockCount: data.inventory?.low_stock_count ?? 0,
      lowStockItems: (data.inventory?.low_stock_items ?? []).map((item) => ({
        variantId: item.variant_id,
        productId: item.product_id,
        productTitle: item.product_title,
        sku: item.sku,
        available: item.available,
        lowStockThreshold: item.low_stock_threshold,
      })),
    },
    recentOrders: (data.recent_orders ?? []).map((order) => ({
      id: order.id,
      orderNumber: order.order_number,
      status: order.status,
      itemCount: order.item_count ?? 0,
      total: order.total ?? 0,
      customer: order.customer ?? "",
      placedAt: order.placed_at,
    })),
    // Reviews land with Phase 14 — the slot renders its empty state today.
    recentReviews: data.recent_reviews ?? [],
  };
}

// --- 12.2 Products, variants, images ---------------------------------------

export async function fetchMyProducts({
  q = "",
  status = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(
    CATALOG,
    `/my/products/${query ? `?${query}` : ""}`
  );
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapSellerProduct),
  };
}

export async function fetchMyProduct(id) {
  return mapSellerProduct(await request(CATALOG, `/my/products/${id}/`));
}

export async function createProduct(payload) {
  const csrf = await ensureCsrfToken();
  return mapSellerProduct(
    await request(CATALOG, "/my/products/", {
      method: "POST",
      body: payload,
      csrf,
    })
  );
}

export async function updateProduct(id, payload) {
  const csrf = await ensureCsrfToken();
  return mapSellerProduct(
    await request(CATALOG, `/my/products/${id}/`, {
      method: "PATCH",
      body: payload,
      csrf,
    })
  );
}

/** Delete — the server hard-deletes, or archives when order history exists. */
export async function deleteProduct(id) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, `/my/products/${id}/`, {
    method: "DELETE",
    csrf,
  });
  return {
    action: data.action,
    detail: data.detail,
    product: data.product ? mapSellerProduct(data.product) : null,
  };
}

/** Lifecycle transitions (12.2) — status is service-owned, never a PATCH. */
async function transitionProduct(id, action) {
  const csrf = await ensureCsrfToken();
  return mapSellerProduct(
    await request(CATALOG, `/my/products/${id}/${action}/`, {
      method: "POST",
      csrf,
    })
  );
}

export function submitProduct(id) {
  return transitionProduct(id, "submit");
}

export function unpublishProduct(id) {
  return transitionProduct(id, "unpublish");
}

export function archiveProduct(id) {
  return transitionProduct(id, "archive");
}

/** Bulk lifecycle (§12.2) — per-id results; one bad row never blocks the batch. */
export function bulkProducts(action, ids) {
  return ensureCsrfToken().then((csrf) =>
    request(CATALOG, "/my/products/bulk/", {
      method: "POST",
      body: { action, ids },
      csrf,
    })
  );
}

export async function addVariant(productId, payload) {
  const csrf = await ensureCsrfToken();
  return mapSellerVariant(
    await request(CATALOG, `/my/products/${productId}/variants/`, {
      method: "POST",
      body: payload,
      csrf,
    })
  );
}

export async function updateVariant(productId, variantId, payload) {
  const csrf = await ensureCsrfToken();
  return mapSellerVariant(
    await request(
      CATALOG,
      `/my/products/${productId}/variants/${variantId}/`,
      { method: "PATCH", body: payload, csrf }
    )
  );
}

export async function removeVariant(productId, variantId) {
  const csrf = await ensureCsrfToken();
  const data = await request(
    CATALOG,
    `/my/products/${productId}/variants/${variantId}/`,
    { method: "DELETE", csrf }
  );
  return {
    action: data.action,
    detail: data.detail,
    variant: data.variant ? mapSellerVariant(data.variant) : null,
  };
}

export async function uploadProductImage(
  productId,
  file,
  { altText = "", position = 0 } = {}
) {
  const csrf = await ensureCsrfToken();
  const form = new FormData();
  form.append("image", file);
  form.append("alt_text", altText);
  form.append("position", String(position));
  const data = await request(CATALOG, `/my/products/${productId}/images/`, {
    method: "POST",
    body: form,
    csrf,
  });
  return {
    id: data.id,
    url: data.image,
    altText: data.alt_text ?? "",
    position: data.position ?? 0,
  };
}

export async function removeProductImage(productId, imageId) {
  const csrf = await ensureCsrfToken();
  return request(
    CATALOG,
    `/my/products/${productId}/remove_image/?image_id=${imageId}`,
    { method: "DELETE", csrf }
  );
}

// --- 12.3 Inventory --------------------------------------------------------

export async function fetchInventory({
  q = "",
  lowStock = false,
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (lowStock) params.set("low_stock", "1");
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(CATALOG, `/my/stock${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapInventoryRow),
  };
}

export async function adjustStock({ variantId, delta, note = "" }) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, "/my/stock", {
    method: "POST",
    body: { variant_id: variantId, delta, note },
    csrf,
  });
  return mapSellerVariant(data);
}

export async function setLowStockThreshold(variantId, threshold) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, "/my/stock", {
    method: "POST",
    body: { variant_id: variantId, threshold },
    csrf,
  });
  return mapSellerVariant(data);
}

export async function fetchStockHistory(variantId) {
  const data = await request(
    CATALOG,
    `/my/stock?variant_id=${encodeURIComponent(variantId)}`
  );
  return {
    count: data.count ?? 0,
    items: (data.items ?? []).map((movement) => ({
      id: movement.id,
      reason: movement.reason,
      delta: movement.quantity_delta,
      resultingOnHand: movement.resulting_on_hand,
      note: movement.note,
      createdAt: movement.created_at,
    })),
  };
}

// --- 12.4 / 12.5 Seller orders ---------------------------------------------

export async function fetchSellerOrders({
  status = "",
  q = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (q) params.set("q", q);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(
    BASE,
    `/seller/orders/${query ? `?${query}` : ""}`
  );
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapSellerOrder),
  };
}

export async function fetchSellerOrder(id) {
  return mapSellerOrder(await request(BASE, `/seller/orders/${id}/`));
}

async function transitionSellerOrder(id, action, body = undefined) {
  const csrf = await ensureCsrfToken();
  return mapSellerOrder(
    await request(BASE, `/seller/orders/${id}/${action}`, {
      method: "POST",
      body,
      csrf,
    })
  );
}

export function processSellerOrder(id) {
  return transitionSellerOrder(id, "process");
}

export function packSellerOrder(id) {
  return transitionSellerOrder(id, "pack");
}

/**
 * Ship (§10.2/12.4) — items omitted means "everything still unfulfilled";
 * carrier/notes/weight are the seller's parcel details, not pricing input.
 */
export function shipSellerOrder(
  id,
  { carrier = "manual", notes = "", weightGrams = null, items = null } = {}
) {
  return transitionSellerOrder(id, "ship", {
    carrier,
    package_notes: notes,
    ...(weightGrams ? { package_weight_grams: Number(weightGrams) } : {}),
    ...(items ? { items } : {}),
  });
}



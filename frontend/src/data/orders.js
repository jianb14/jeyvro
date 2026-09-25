/**
 * Order accessors — the ONLY data access point for checkout and orders
 * (data-layer). The API recomputes every number server-side (§6): the
 * checkout preview returns live lines + per-store shipping, and order
 * payloads are immutable snapshots — components render these values and
 * never recompute them (marketplace-orders rule 1).
 */

import { ensureCsrfToken, request } from "../lib/api";

const BASE = "/api/v1";

/**
 * Payment labels (Phase 9) — display only; status and amounts always come
 * from the API (server-authoritative money, §6 v1.8).
 */
const PAYMENT_LABELS = {
  cod: "Cash on Delivery",
  card: "Card",
  gcash: "GCash",
  maya: "Maya",
};

function mapItem(item) {
  return {
    id: item.id,
    productSlug: item.product_slug,
    title: item.title,
    variant: item.variant_name,
    sku: item.sku,
    price: item.price ?? item.unit_price,
    originalPrice: item.compare_at_price ?? undefined,
    qty: item.quantity,
    lineTotal: item.line_total,
  };
}

function mapSellerOrder(sellerOrder) {
  return {
    id: sellerOrder.id,
    storeSlug: sellerOrder.store_slug,
    storeName: sellerOrder.store_name,
    status: sellerOrder.status,
    subtotal: sellerOrder.subtotal,
    shippingFee: sellerOrder.shipping_fee,
    total: sellerOrder.total,
    items: (sellerOrder.items ?? []).map(mapItem),
  };
}

function mapPayment(payment) {
  return {
    reference: payment.reference,
    method: payment.method,
    methodLabel: PAYMENT_LABELS[payment.method] ?? payment.method,
    status: payment.status,
    amount: payment.amount,
    currency: payment.currency,
    checkoutUrl: payment.checkout_url ?? null,
    paidAt: payment.paid_at ?? null,
    expiresAt: payment.expires_at ?? null,
    refundedTotal: payment.refunded_total ?? 0,
  };
}

function mapOrder(order) {
  return {
    number: order.number,
    status: order.status,
    placedAt: order.created_at,
    itemCount: order.item_count ?? 0,
    payment: order.payment ? mapPayment(order.payment) : null,
    address: {
      fullName: order.shipping_address?.full_name ?? "",
      phone: order.shipping_address?.phone ?? "",
      line1: order.shipping_address?.line1 ?? "",
      line2: order.shipping_address?.line2 ?? "",
      city: order.shipping_address?.city ?? "",
      province: order.shipping_address?.province ?? "",
      postalCode: order.shipping_address?.postal_code ?? "",
    },
    totals: {
      subtotal: order.totals?.subtotal ?? 0,
      shipping: order.totals?.shipping_total ?? 0,
      savings: order.totals?.savings_total ?? 0,
      tax: order.totals?.tax_total ?? 0,
      grandTotal: order.totals?.grand_total ?? 0,
    },
    sellerOrders: (order.seller_orders ?? []).map(mapSellerOrder),
  };
}

function mapCheckout(data) {
  const items = (data.items ?? []).map(mapItem);
  return {
    items,
    groups: (data.groups ?? []).map((group) => ({
      storeSlug: group.store_slug,
      storeName: group.store_name,
      itemCount: group.item_count,
      subtotal: group.subtotal,
      shippingFee: group.shipping_fee ?? 0,
      freeShipping: Boolean(group.free_shipping),
      items: (group.items ?? []).map(mapItem),
    })),
    totals: {
      lineCount: data.totals?.line_count ?? items.length,
      itemCount: data.totals?.item_count ?? 0,
      subtotal: data.totals?.subtotal ?? 0,
      savings: data.totals?.savings ?? 0,
      shipping: data.totals?.shipping_total ?? 0,
      tax: data.totals?.tax_total ?? 0,
      grandTotal: data.totals?.grand_total ?? 0,
    },
    issues: (data.issues ?? []).map((issue) => ({
      itemId: issue.item_id,
      title: issue.title,
      reason: issue.reason,
    })),
    paymentMethods: (data.payment_methods ?? []).map((method) => ({
      id: method.id,
      label: method.label,
      description: method.description,
      available: Boolean(method.available),
    })),
    ready: Boolean(data.checkout_ready),
  };
}

export async function fetchCheckout() {
  return mapCheckout(await request(BASE, "/checkout/"));
}

export async function placeOrder(addressId, paymentMethod = "cod") {
  const csrf = await ensureCsrfToken();
  return mapOrder(
    await request(BASE, "/checkout/orders", {
      method: "POST",
      body: { address_id: addressId, payment_method: paymentMethod },
      csrf,
    })
  );
}

export async function fetchOrder(number) {
  return mapOrder(
    await request(BASE, `/orders/${encodeURIComponent(number)}/`)
  );
}

export async function cancelOrder(number) {
  const csrf = await ensureCsrfToken();
  return mapOrder(
    await request(BASE, `/orders/${encodeURIComponent(number)}/cancel`, {
      method: "POST",
      csrf,
    })
  );
}

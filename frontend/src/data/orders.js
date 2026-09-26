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

function mapTrackingEvent(event) {
  return {
    id: event.id,
    status: event.status,
    location: event.location,
    description: event.description,
    occurredAt: event.occurred_at,
  };
}

function mapShipment(shipment) {
  return {
    id: shipment.id,
    trackingNumber: shipment.tracking_number,
    carrier: shipment.carrier,
    carrierName: shipment.carrier_name,
    shippingMethod: shipment.shipping_method,
    shippingFee: shipment.shipping_fee ?? 0,
    status: shipment.status,
    shippedAt: shipment.shipped_at ?? null,
    estimatedDelivery: shipment.estimated_delivery ?? null,
    deliveredAt: shipment.delivered_at ?? null,
    items: (shipment.items ?? []).map((entry) => ({
      id: entry.id,
      orderItemId: entry.order_item_id,
      title: entry.product_title,
      variant: entry.variant_name,
      sku: entry.sku,
      quantity: entry.quantity,
    })),
    events: (shipment.tracking_events ?? []).map(mapTrackingEvent),
  };
}

function mapOrderRequest(request) {
  return {
    id: request.id,
    kind: request.kind,
    kindLabel: request.kind_label,
    status: request.status,
    reason: request.reason,
    description: request.description,
    sellerOrderId: request.seller_order_id,
    storeName: request.store_name,
    createdAt: request.created_at,
  };
}

/**
 * Seller-side slice mapping (Phase 12 reuses it from the seller accessors):
 * server truth only — item snapshots, shipment timeline, privacy-laddered
 * customer context, and the action flags that mirror the fulfillment
 * services. `customer.address` is null until the seller accepts the order.
 */
export function mapSellerOrder(sellerOrder) {
  return {
    id: sellerOrder.id,
    orderNumber: sellerOrder.order_number ?? "",
    placedAt: sellerOrder.placed_at ?? null,
    storeSlug: sellerOrder.store_slug,
    storeName: sellerOrder.store_name,
    status: sellerOrder.status,
    itemCount: sellerOrder.item_count ?? 0,
    subtotal: sellerOrder.subtotal,
    shippingFee: sellerOrder.shipping_fee,
    total: sellerOrder.total,
    items: (sellerOrder.items ?? []).map(mapItem),
    shipments: (sellerOrder.shipments ?? []).map(mapShipment),
    payment: sellerOrder.payment
      ? {
          method: sellerOrder.payment.method,
          methodLabel: sellerOrder.payment.method_label,
          status: sellerOrder.payment.status,
          paid: Boolean(sellerOrder.payment.paid),
        }
      : null,
    customer: {
      name: sellerOrder.customer?.name ?? "",
      phone: sellerOrder.customer?.phone ?? "",
      city: sellerOrder.customer?.city ?? "",
      province: sellerOrder.customer?.province ?? "",
      postalCode: sellerOrder.customer?.postal_code ?? "",
      address: sellerOrder.customer?.address ?? null,
      revealed: Boolean(sellerOrder.customer?.revealed),
    },
    canProcess: Boolean(sellerOrder.can_process),
    canPack: Boolean(sellerOrder.can_pack),
    canShip: Boolean(sellerOrder.can_ship),
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
    canCancel: Boolean(order.can_cancel),
    // Timeline steps come pre-mapped from the server's audit trail — the
    // client renders copy + tone, never interprets raw events (§11.2).
    timeline: (order.timeline ?? []).map((step) => ({
      title: step.title,
      description: step.description,
      tone: step.tone,
      time: step.occurred_at,
    })),
    requests: (order.requests ?? []).map(mapOrderRequest),
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

/**
 * Order history (Phase 11.2) — the {count, items} envelope; rows carry only
 * the server's snapshot values.
 */
function mapOrderSummary(order) {
  return {
    number: order.number,
    status: order.status,
    placedAt: order.created_at,
    itemCount: order.item_count ?? 0,
    grandTotal: order.grand_total ?? 0,
    storeNames: order.store_names ?? [],
    canCancel: Boolean(order.can_cancel),
  };
}

export async function fetchOrders({ page, pageSize } = {}) {
  const params = new URLSearchParams();
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(BASE, `/orders/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? 0,
    items: (data.items ?? []).map(mapOrderSummary),
  };
}

/**
 * Reorder (Phase 11.2) — re-adds still-buyable lines through the cart
 * service; `skipped` explains every line the live catalog refused.
 */
export async function reorderOrder(number) {
  const csrf = await ensureCsrfToken();
  const data = await request(
    BASE,
    `/orders/${encodeURIComponent(number)}/reorder`,
    { method: "POST", csrf }
  );
  return {
    added: data.added ?? [],
    skipped: data.skipped ?? [],
    cartItemCount: data.cart_item_count ?? 0,
  };
}

/**
 * Post-purchase request intake (Phase 11.3) — the server decides whether
 * the order is eligible; the UI only submits what the customer chose.
 */
export async function createOrderRequest(
  number,
  { kind, reason, description = "", sellerOrderId = null }
) {
  const csrf = await ensureCsrfToken();
  return mapOrderRequest(
    await request(BASE, `/orders/${encodeURIComponent(number)}/requests`, {
      method: "POST",
      body: {
        kind,
        reason,
        description,
        ...(sellerOrderId ? { seller_order_id: sellerOrderId } : {}),
      },
      csrf,
    })
  );
}

export async function withdrawOrderRequest(number, requestId) {
  const csrf = await ensureCsrfToken();
  return mapOrderRequest(
    await request(
      BASE,
      `/orders/${encodeURIComponent(number)}/requests/${requestId}/withdraw`,
      { method: "POST", csrf }
    )
  );
}

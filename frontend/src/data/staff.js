/**
 * Staff operations accessors (Phase 13) — the ONLY data access point for
 * the staff portal: seller-application review, store oversight, the audit
 * log viewer, the staff directory with role assignment, and user management
 * (13.1/13.2). Same conventions as the other data modules: session cookies,
 * CSRF on unsafe methods, the §8 error envelope, and every shape mapped
 * here so components render API truth and never recompute numbers
 * (marketplace-admin rule 5).
 */

import { ensureCsrfToken, request } from "../lib/api";

const STORES = "/api/v1/stores";
const AUDIT = "/api/v1/audit";
const AUTH = "/api/v1/auth";
const CATALOG = "/api/v1/catalog";

// --- Shape mapping ---------------------------------------------------------

export function mapApplication(application) {
  return {
    id: application.id,
    applicantEmail: application.applicant_email ?? "",
    storeSlug: application.store_slug ?? "",
    storeStatus: application.store_status ?? "",
    storeName: application.store_name ?? "",
    storeDescription: application.store_description ?? "",
    contactPhone: application.contact_phone ?? "",
    status: application.status,
    rejectionReason: application.rejection_reason ?? "",
    reviewedBy: application.reviewed_by ?? null,
    reviewedAt: application.reviewed_at ?? null,
    createdAt: application.created_at,
  };
}

export function mapStaffStore(store) {
  return {
    id: store.id,
    name: store.name,
    slug: store.slug,
    description: store.description ?? "",
    ownerEmail: store.owner_email ?? "",
    ownerName: store.owner_name ?? "",
    status: store.status,
    contactEmail: store.contact_email ?? "",
    contactPhone: store.contact_phone ?? "",
    productCount: store.product_count ?? 0,
    suspendedAt: store.suspended_at ?? null,
    createdAt: store.created_at,
    updatedAt: store.updated_at,
  };
}

export function mapAuditEvent(event) {
  return {
    id: event.id,
    actorEmail: event.actor_email ?? "system",
    action: event.action,
    objectType: event.object_type,
    objectId: event.object_id,
    detail: event.detail ?? {},
    createdAt: event.created_at,
  };
}

export function mapAdminUser(user) {
  return {
    id: user.id,
    email: user.email,
    firstName: user.first_name ?? "",
    lastName: user.last_name ?? "",
    fullName:
      user.full_name ??
      `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim(),
    phone: user.phone ?? "",
    isSeller: Boolean(user.is_seller),
    isStaff: Boolean(user.is_staff),
    staffRoles: user.staff_roles ?? [],
    accountStatus: user.account_status ?? "active",
    suspendedAt: user.suspended_at ?? null,
    emailVerified: Boolean(user.email_verified),
    joinedAt: user.date_joined,
  };
}

export function mapStaffMember(user) {
  return {
    id: user.id,
    email: user.email,
    fullName:
      user.full_name ??
      `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim(),
    staffRoles: user.staff_roles ?? [],
    isStaff: Boolean(user.is_staff),
    isSuperuser: Boolean(user.is_superuser),
    accountStatus: user.account_status ?? "active",
    joinedAt: user.date_joined,
  };
}

// --- 13.3 Seller application review ----------------------------------------

export async function fetchApplicationQueue({
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
    STORES,
    `/admin/applications/${query ? `?${query}` : ""}`
  );
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapApplication),
  };
}

/**
 * Approve or reject a pending application (§13.3). A rejection reason is
 * mandatory server-side — the UI collects it, the API enforces it.
 */
export async function reviewApplication(id, { decision, reason = "" }) {
  const csrf = await ensureCsrfToken();
  const data = await request(STORES, `/admin/applications/${id}/review`, {
    method: "POST",
    body: { decision, reason },
    csrf,
  });
  return mapApplication(data);
}

// --- 13.3 Store oversight --------------------------------------------------

export async function fetchStaffStores({
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
  const data = await request(STORES, `/admin/stores/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffStore),
  };
}

/** `action` is "suspend" or "activate" — both audit-logged server-side. */
export async function setStoreStatus(id, action, reason = "") {
  const csrf = await ensureCsrfToken();
  const data = await request(STORES, `/admin/stores/${id}/${action}`, {
    method: "POST",
    body: { reason },
    csrf,
  });
  return mapStaffStore(data);
}

// --- 13.7 Audit log viewer -------------------------------------------------

export async function fetchAuditEvents({
  actor = "",
  action = "",
  objectType = "",
  objectId = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (actor) params.set("actor", actor);
  if (action) params.set("action", action);
  if (objectType) params.set("object_type", objectType);
  if (objectId) params.set("object_id", objectId);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(AUDIT, `/events/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapAuditEvent),
  };
}

// --- 13.2 User management --------------------------------------------------

export async function fetchAdminUsers({
  q = "",
  status = "",
  role = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (role) params.set("role", role);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(AUTH, `/admin/users/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapAdminUser),
  };
}

export async function fetchAdminUser(id) {
  const data = await request(AUTH, `/admin/users/${id}/`);
  return mapAdminUser(data);
}

/** `action` is "suspend" or "reactivate" — both audit-logged server-side. */
export async function setUserStatus(id, action, reason = "") {
  const csrf = await ensureCsrfToken();
  const data = await request(AUTH, `/admin/users/${id}/${action}`, {
    method: "POST",
    body: { reason },
    csrf,
  });
  return mapAdminUser(data);
}

// --- 13.1 Staff directory & role assignment --------------------------------

export async function fetchStaffMembers({
  q = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(AUTH, `/admin/staff/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffMember),
  };
}

/** `action` is "assign" or "remove" — both audit-logged server-side. */
export async function changeStaffRole(id, action, group) {
  const csrf = await ensureCsrfToken();
  const data = await request(AUTH, `/admin/staff/${id}/roles/${action}`, {
    method: "POST",
    body: { group },
    csrf,
  });
  return mapStaffMember(data);
}

// --- 13.4 Catalog management ----------------------------------------------

export function mapStaffProduct(product) {
  return {
    id: product.id,
    title: product.title,
    slug: product.slug,
    status: product.status,
    rejectionReason: product.rejection_reason ?? "",
    basePrice: Number(product.base_price ?? 0),
    compareAtPrice:
      product.compare_at_price != null ? Number(product.compare_at_price) : null,
    displayPrice: Number(product.display_price ?? product.base_price ?? 0),
    storeName: product.store_name ?? "",
    storeSlug: product.store_slug ?? "",
    storeOwnerEmail: product.store_owner_email ?? "",
    categoryName: product.category_name ?? null,
    categorySlug: product.category_slug ?? null,
    brandName: product.brand_name ?? null,
    variantCount: product.variant_count ?? 0,
    imageCount: product.image_count ?? 0,
    primaryImage: product.primary_image ?? null,
    createdAt: product.created_at,
    updatedAt: product.updated_at,
  };
}

export async function fetchAdminProducts({
  q = "",
  status = "",
  store = "",
  category = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (store) params.set("store", store);
  if (category) params.set("category", category);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(CATALOG, `/admin/products/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffProduct),
  };
}

/** `decision` is "published" or "rejected" — both audit-logged server-side. */
export async function reviewProduct(id, decision, reason = "") {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, `/admin/products/${id}/review`, {
    method: "POST",
    body: { decision, reason },
    csrf,
  });
  return mapStaffProduct(data);
}

/** Staff takedown of a published product (reason required, audit-logged). */
export async function unpublishProduct(id, reason) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, `/admin/products/${id}/unpublish`, {
    method: "POST",
    body: { reason },
    csrf,
  });
  return mapStaffProduct(data);
}

export function mapStaffCategory(category) {
  return {
    id: category.id,
    parentId: category.parent ?? null,
    name: category.name,
    slug: category.slug,
    description: category.description ?? "",
    position: category.position ?? 0,
    isActive: Boolean(category.is_active),
    productCount: category.product_count ?? 0,
  };
}

export function mapStaffBrand(brand) {
  return {
    id: brand.id,
    name: brand.name,
    slug: brand.slug,
    productCount: brand.product_count ?? 0,
  };
}

export async function fetchAdminCategories({
  q = "",
  page = "",
  pageSize = "",
} = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(CATALOG, `/admin/categories/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffCategory),
  };
}

export async function createCategory(payload) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, "/admin/categories/", {
    method: "POST",
    body: payload,
    csrf,
  });
  return mapStaffCategory(data);
}

export async function updateCategory(id, payload) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, `/admin/categories/${id}/`, {
    method: "PATCH",
    body: payload,
    csrf,
  });
  return mapStaffCategory(data);
}

export async function deleteCategory(id) {
  const csrf = await ensureCsrfToken();
  await request(CATALOG, `/admin/categories/${id}/`, { method: "DELETE", csrf });
}

export async function fetchAdminBrands({ q = "", page = "", pageSize = "" } = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (page) params.set("page", page);
  if (pageSize) params.set("page_size", pageSize);
  const query = params.toString();
  const data = await request(CATALOG, `/admin/brands/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffBrand),
  };
}

export async function createBrand(payload) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, "/admin/brands/", {
    method: "POST",
    body: payload,
    csrf,
  });
  return mapStaffBrand(data);
}

export async function updateBrand(id, payload) {
  const csrf = await ensureCsrfToken();
  const data = await request(CATALOG, `/admin/brands/${id}/`, {
    method: "PATCH",
    body: payload,
    csrf,
  });
  return mapStaffBrand(data);
}

export async function deleteBrand(id) {
  const csrf = await ensureCsrfToken();
  await request(CATALOG, `/admin/brands/${id}/`, { method: "DELETE", csrf });
}

// --- 13.5 Order & payment operations (read-only oversight, §4 groups) ------

const OPERATIONS = "/api/v1";
const PAYMENTS = "/api/v1/payments";

export function mapStaffOrderRow(row) {
  return {
    number: row.number,
    status: row.status,
    placedAt: row.created_at,
    customerEmail: row.customer_email ?? "",
    shipToCity: row.ship_to_city ?? "",
    shipToProvince: row.ship_to_province ?? "",
    grandTotal: row.grand_total ?? 0,
    itemCount: row.item_count ?? 0,
    storeNames: row.store_names ?? [],
    paymentMethod: row.payment_method ?? null,
    paymentStatus: row.payment_status ?? null,
  };
}

export function mapStaffShipmentRow(row) {
  return {
    trackingNumber: row.tracking_number,
    orderNumber: row.order_number,
    storeName: row.store_name ?? "",
    carrier: row.carrier,
    carrierName: row.carrier_name ?? "",
    status: row.status,
    shippedAt: row.shipped_at ?? null,
    deliveredAt: row.delivered_at ?? null,
    eventCount: row.event_count ?? 0,
    createdAt: row.created_at,
  };
}

export function mapStaffRequestRow(row) {
  return {
    id: row.id,
    kind: row.kind,
    kindLabel: row.kind_label ?? "",
    status: row.status,
    reason: row.reason ?? "",
    description: row.description ?? "",
    storeName: row.store_name ?? "",
    orderNumber: row.order_number,
    customerEmail: row.customer_email ?? "",
    createdAt: row.created_at,
  };
}

export function mapStaffPaymentRow(row) {
  return {
    reference: row.reference,
    orderNumber: row.order_number,
    customerEmail: row.customer_email ?? "",
    method: row.method,
    status: row.status,
    amount: row.amount ?? 0,
    currency: row.currency ?? "PHP",
    provider: row.provider ?? "",
    refundedTotal: row.refunded_total ?? 0,
    paidAt: row.paid_at ?? null,
    createdAt: row.created_at,
  };
}

export function mapStaffRefundRow(row) {
  return {
    reference: row.reference,
    paymentReference: row.payment_reference,
    orderNumber: row.order_number,
    amount: row.amount ?? 0,
    status: row.status,
    reason: row.reason ?? "",
    issuedBy: row.issued_by ?? "",
    createdAt: row.created_at,
  };
}

function buildQuery(entries) {
  const params = new URLSearchParams();
  Object.entries(entries).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function mapStaffOrderDetail(payload) {
  return {
    number: payload.number,
    status: payload.status,
    placedAt: payload.created_at,
    itemCount: payload.item_count ?? 0,
    customerEmail: payload.customer_email ?? "",
    canCancel: Boolean(payload.can_cancel),
    payment: payload.payment
      ? {
          reference: payload.payment.reference,
          method: payload.payment.method,
          status: payload.payment.status,
          amount: payload.payment.amount ?? 0,
          currency: payload.payment.currency ?? "PHP",
          provider: payload.payment.provider ?? "",
          refundedTotal: payload.payment.refunded_total ?? 0,
          paidAt: payload.payment.paid_at ?? null,
        }
      : null,
    shippingAddress: {
      fullName: payload.shipping_address?.full_name ?? "",
      phone: payload.shipping_address?.phone ?? "",
      line1: payload.shipping_address?.line1 ?? "",
      line2: payload.shipping_address?.line2 ?? "",
      city: payload.shipping_address?.city ?? "",
      province: payload.shipping_address?.province ?? "",
      postalCode: payload.shipping_address?.postal_code ?? "",
    },
    totals: {
      subtotal: payload.totals?.subtotal ?? 0,
      shipping: payload.totals?.shipping_total ?? 0,
      savings: payload.totals?.savings_total ?? 0,
      tax: payload.totals?.tax_total ?? 0,
      grandTotal: payload.totals?.grand_total ?? 0,
    },
    stores: (payload.seller_orders ?? []).map((sellerOrder) => ({
      id: sellerOrder.id,
      storeName: sellerOrder.store_name ?? "",
      status: sellerOrder.status,
      subtotal: sellerOrder.subtotal ?? 0,
      shippingFee: sellerOrder.shipping_fee ?? 0,
      total: sellerOrder.total ?? 0,
      items: (sellerOrder.items ?? []).map((item) => ({
        id: item.id,
        title: item.title ?? "",
        variant: item.variant_name ?? "",
        sku: item.sku ?? "",
        quantity: item.quantity ?? 0,
        lineTotal: item.line_total ?? 0,
      })),
    })),
    requests: (payload.requests ?? []).map((request) => ({
      id: request.id,
      kind: request.kind,
      kindLabel: request.kind_label ?? "",
      status: request.status,
      reason: request.reason ?? "",
      storeName: request.store_name ?? "",
      createdAt: request.created_at,
    })),
  };
}

export async function fetchStaffOrders({
  q = "",
  status = "",
  store = "",
  payment = "",
  page = "",
  pageSize = "",
} = {}) {
  const query = buildQuery({ q, status, store, payment, page, page_size: pageSize });
  const data = await request(OPERATIONS, `/admin/orders/${query}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffOrderRow),
  };
}

export async function fetchStaffOrderDetail(number) {
  const data = await request(
    OPERATIONS,
    `/admin/orders/${encodeURIComponent(number)}/`
  );
  return mapStaffOrderDetail(data);
}

export async function fetchStaffShipments({
  q = "",
  status = "",
  carrier = "",
  page = "",
  pageSize = "",
} = {}) {
  const query = buildQuery({ q, status, carrier, page, page_size: pageSize });
  const data = await request(OPERATIONS, `/admin/shipments/${query}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffShipmentRow),
  };
}

export async function fetchStaffRequests({
  q = "",
  kind = "",
  status = "",
  page = "",
  pageSize = "",
} = {}) {
  const query = buildQuery({ q, kind, status, page, page_size: pageSize });
  const data = await request(OPERATIONS, `/admin/requests/${query}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffRequestRow),
  };
}

export async function fetchStaffPayments({
  q = "",
  status = "",
  method = "",
  page = "",
  pageSize = "",
} = {}) {
  const query = buildQuery({ q, status, method, page, page_size: pageSize });
  const data = await request(PAYMENTS, `/admin/payments/${query}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffPaymentRow),
  };
}

export async function fetchStaffRefunds({
  q = "",
  status = "",
  page = "",
  pageSize = "",
} = {}) {
  const query = buildQuery({ q, status, page, page_size: pageSize });
  const data = await request(PAYMENTS, `/admin/refunds/${query}`);
  return {
    count: data.count ?? (data.items ?? []).length,
    items: (data.items ?? []).map(mapStaffRefundRow),
  };
}

// --- 13.6 Platform settings (one audited singleton row, §4 groups) ---------

const SETTINGS = "/api/v1/admin/settings";

export function mapStaffSettings(data) {
  return {
    platformName: data.platform_name ?? "",
    supportEmail: data.support_email ?? "",
    commissionRatePercent: data.commission_rate_percent ?? "0.00",
    defaultShippingFlatFee: data.default_shipping_flat_fee ?? "0.00",
    // Null is a real value here (a store may ship with no threshold).
    defaultFreeShippingThreshold:
      data.default_free_shipping_threshold ?? null,
    codEnabled: Boolean(data.cod_enabled),
    paymentExpiryHours: data.payment_expiry_hours ?? 24,
    defaultOrderUpdatesEmail: Boolean(data.default_order_updates_email),
    defaultPromotionsEmail: Boolean(data.default_promotions_email),
    defaultMessagingEmail: Boolean(data.default_messaging_email),
    updatedAt: data.updated_at ?? null,
    updatedByEmail: data.updated_by_email ?? null,
  };
}

export async function fetchStaffSettings() {
  return mapStaffSettings(await request(SETTINGS, "/"));
}

/** Administrator path — everything except commission (§4 keeps that with
 * finance), applied as a partial update of the singleton row. */
export async function updateStaffSettings(patch) {
  const csrf = await ensureCsrfToken();
  return mapStaffSettings(
    await request(SETTINGS, "/", { method: "PATCH", body: patch, csrf })
  );
}

/** Finance/administrator path — commission only (§4). */
export async function updateStaffCommission(patch) {
  const csrf = await ensureCsrfToken();
  return mapStaffSettings(
    await request(SETTINGS, "/commission/", { method: "PATCH", body: patch, csrf })
  );
}

// --- 19.1 Analytics & reporting --------------------------------------------

const ANALYTICS = "/api/v1/admin/analytics";

// Every figure below arrives pre-computed from the reporting aggregates: the
// dashboard renders what the server derived and never re-derives a number of
// its own (marketplace-admin rule 5). Money stays a string — never a float.

export function mapPlatformTotals(totals) {
  return {
    start: totals.start ?? null,
    end: totals.end ?? null,
    ordersCount: totals.orders_count ?? 0,
    ordersCancelled: totals.orders_cancelled ?? 0,
    ordersPaid: totals.orders_paid ?? 0,
    unitsSold: totals.units_sold ?? 0,
    productsSold: totals.products_sold ?? 0,
    // Named for what they are: sums of the daily active counts, not distinct
    // people — a customer who ordered on three days is three customer-days.
    customerDays: totals.customer_days ?? 0,
    sellerDays: totals.seller_days ?? 0,
    gmv: totals.gmv ?? "0.00",
    merchandise: totals.merchandise ?? "0.00",
    shipping: totals.shipping ?? "0.00",
    discounts: totals.discounts ?? "0.00",
    capturedTotal: totals.captured_total ?? "0.00",
    refundedTotal: totals.refunded_total ?? "0.00",
    revenue: totals.revenue ?? "0.00",
    commissionBase: totals.commission_base ?? "0.00",
    commission: totals.commission ?? "0.00",
  };
}

export function mapPlatformDay(day) {
  return {
    day: day.day,
    ordersCount: day.orders_count ?? 0,
    ordersCancelled: day.orders_cancelled ?? 0,
    ordersPaid: day.orders_paid ?? 0,
    unitsSold: day.units_sold ?? 0,
    productsSold: day.products_sold ?? 0,
    activeCustomers: day.active_customers ?? 0,
    activeSellers: day.active_sellers ?? 0,
    gmv: day.gmv ?? "0.00",
    merchandise: day.merchandise ?? "0.00",
    shipping: day.shipping ?? "0.00",
    discounts: day.discounts ?? "0.00",
    capturedTotal: day.captured_total ?? "0.00",
    refundedTotal: day.refunded_total ?? "0.00",
    revenue: day.revenue ?? "0.00",
    commissionBase: day.commission_base ?? "0.00",
    commission: day.commission ?? "0.00",
    commissionRatePercent: day.commission_rate_percent ?? "0.00",
  };
}

export function mapStoreLeaderRow(row) {
  return {
    storeId: row.store_id,
    storeName: row.store__name ?? "",
    storeSlug: row.store__slug ?? "",
    ordersCount: row.orders_count ?? 0,
    unitsSold: row.units_sold ?? 0,
    grossSales: row.gross_sales ?? "0.00",
    merchandise: row.merchandise ?? "0.00",
    sellerFundedDiscount: row.seller_funded_discount ?? "0.00",
    capturedTotal: row.captured_total ?? "0.00",
    refundedTotal: row.refunded_total ?? "0.00",
    revenue: row.revenue ?? "0.00",
    commissionBase: row.commission_base ?? "0.00",
    commission: row.commission ?? "0.00",
  };
}

export function mapTopProductRow(row) {
  return {
    productId: row.product_id,
    productTitle: row.product__title ?? "",
    storeId: row.store_id,
    storeName: row.store__name ?? "",
    unitsSold: row.units_sold ?? 0,
    ordersCount: row.orders_count ?? 0,
    merchandise: row.merchandise ?? "0.00",
  };
}

/** GET /api/v1/admin/analytics/summary/ — totals + the daily series. */
export async function fetchStaffAnalyticsSummary({ from = "", to = "" } = {}) {
  const query = buildQuery({ from, to });
  const data = await request(ANALYTICS, `/summary/${query}`);
  return {
    start: data.start ?? null,
    end: data.end ?? null,
    totals: mapPlatformTotals(data.totals ?? {}),
    days: (data.days ?? []).map(mapPlatformDay),
  };
}

/** GET /api/v1/admin/analytics/stores/ — the store leaderboard. */
export async function fetchStaffAnalyticsStores({
  from = "",
  to = "",
  limit = "",
} = {}) {
  const query = buildQuery({ from, to, limit });
  const data = await request(ANALYTICS, `/stores/${query}`);
  return (data.items ?? []).map(mapStoreLeaderRow);
}

/** GET /api/v1/admin/analytics/products/ — product activity. */
export async function fetchStaffAnalyticsProducts({
  from = "",
  to = "",
  limit = "",
} = {}) {
  const query = buildQuery({ from, to, limit });
  const data = await request(ANALYTICS, `/products/${query}`);
  return (data.items ?? []).map(mapTopProductRow);
}

// --- 19.3 Operations & seller performance ------------------------------------

// Operational metrics are counts, not pesos, and their definitions are the
// server's (§19.3): orders bucketed by where they stand at rebuild, parcels
// created/delivered, cases filed/decided/received, refunds issued/settled,
// and the support workload. The page renders them as given — no rate is
// divided here (marketplace-admin rule 5).
function operationCounts(row) {
  return {
    ordersOpen: row.orders_open ?? 0,
    ordersCompleted: row.orders_completed ?? 0,
    ordersCancelled: row.orders_cancelled ?? 0,
    ordersRefunded: row.orders_refunded ?? 0,
    shipmentsCreated: row.shipments_created ?? 0,
    shipmentsDelivered: row.shipments_delivered ?? 0,
    returnsFiled: row.returns_filed ?? 0,
    returnsApproved: row.returns_approved ?? 0,
    returnsRejected: row.returns_rejected ?? 0,
    returnsReceived: row.returns_received ?? 0,
    refundsIssued: row.refunds_issued ?? 0,
    refundsSettled: row.refunds_settled ?? 0,
    requestsFiled: row.requests_filed ?? 0,
    conversationsOpened: row.conversations_opened ?? 0,
    messagesSent: row.messages_sent ?? 0,
    disputesOpened: row.disputes_opened ?? 0,
    disputesResolved: row.disputes_resolved ?? 0,
  };
}

export function mapOperationsTotals(totals) {
  return {
    start: totals.start ?? null,
    end: totals.end ?? null,
    ...operationCounts(totals),
  };
}

export function mapOperationsDay(day) {
  return { day: day.day, ...operationCounts(day) };
}

export function mapStorePerformanceRow(row) {
  return {
    storeId: row.store_id,
    storeName: row.store__name ?? "",
    shipmentsCreated: row.shipments_created ?? 0,
    shipmentsDelivered: row.shipments_delivered ?? 0,
    returnsFiled: row.returns_filed ?? 0,
    returnsReceived: row.returns_received ?? 0,
    disputesOpened: row.disputes_opened ?? 0,
    requestsFiled: row.requests_filed ?? 0,
    messagesSent: row.messages_sent ?? 0,
  };
}

/** GET /api/v1/admin/analytics/operations/ — the operational day (§19.3). */
export async function fetchStaffAnalyticsOperations({ from = "", to = "" } = {}) {
  const query = buildQuery({ from, to });
  const data = await request(ANALYTICS, `/operations/${query}`);
  return {
    start: data.start ?? null,
    end: data.end ?? null,
    totals: mapOperationsTotals(data.totals ?? {}),
    days: (data.days ?? []).map(mapOperationsDay),
  };
}

/** GET /api/v1/admin/analytics/performance/ — seller performance (§19.3). */
export async function fetchStaffAnalyticsPerformance({
  from = "",
  to = "",
  limit = "",
} = {}) {
  const query = buildQuery({ from, to, limit });
  const data = await request(ANALYTICS, `/performance/${query}`);
  return (data.items ?? []).map(mapStorePerformanceRow);
}


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


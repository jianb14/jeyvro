import { afterEach, describe, expect, it, vi } from "vitest";
import {
  STAFF_ANALYTICS_REPORTS,
  changeStaffRole,
  createBrand,
  createCategory,
  deleteBrand,
  deleteCategory,
  fetchAdminBrands,
  fetchAdminCategories,
  fetchAdminProducts,
  fetchAdminUser,
  fetchAdminUsers,
  fetchApplicationQueue,
  fetchAuditEvents,
  fetchStaffAnalyticsOperations,
  fetchStaffAnalyticsPerformance,
  fetchStaffAnalyticsProducts,
  fetchStaffAnalyticsStores,
  fetchStaffAnalyticsSummary,
  fetchStaffMembers,
  fetchStaffOrderDetail,
  fetchStaffOrders,
  fetchStaffPayments,
  fetchStaffRefunds,
  fetchStaffRequests,
  fetchStaffSettings,
  fetchStaffShipments,
  fetchStaffStores,
  reviewApplication,
  reviewProduct,
  setStoreStatus,
  setUserStatus,
  staffAnalyticsCsvUrl,
  unpublishProduct,
  updateCategory,
  updateStaffCommission,
  updateStaffSettings,
} from "./staff";

const APPLICATION_PAYLOAD = {
  id: 4,
  applicant_email: "bacayonjian@gmail.com",
  store_slug: "jianshop",
  store_status: "pending",
  store_name: "JianShop",
  store_description: "Handmade goods.",
  contact_phone: "+63 917 000 0000",
  status: "pending",
  rejection_reason: "",
  reviewed_by: null,
  reviewed_at: null,
  created_at: "2026-09-25T12:00:00Z",
};

const STORE_PAYLOAD = {
  id: 2,
  name: "JianShop",
  slug: "jianshop",
  description: "Handmade goods.",
  owner_email: "bacayonjian@gmail.com",
  owner_name: "Jian Bacayon",
  status: "pending",
  contact_email: "bacayonjian@gmail.com",
  contact_phone: "+63 917 000 0000",
  product_count: 0,
  suspended_at: null,
  created_at: "2026-09-25T12:00:00Z",
  updated_at: "2026-09-25T12:00:00Z",
};

const AUDIT_PAYLOAD = {
  id: 9,
  actor_email: "admin@example.com",
  action: "seller_application_approved",
  object_type: "stores.sellerapplication",
  object_id: "4",
  detail: { store_id: 2, reason: "" },
  created_at: "2026-09-25T12:05:00Z",
};

const USER_PAYLOAD = {
  id: 12,
  email: "buyer@example.com",
  first_name: "Bea",
  last_name: "Buyer",
  full_name: "Bea Buyer",
  phone: "+63 917 111 2222",
  is_seller: false,
  is_staff: false,
  staff_roles: [],
  account_status: "suspended",
  suspended_at: "2026-09-26T08:00:00Z",
  email_verified: true,
  date_joined: "2026-07-01T09:00:00Z",
};

const STAFF_MEMBER_PAYLOAD = {
  id: 3,
  email: "mod@example.com",
  first_name: "Mo",
  last_name: "Derator",
  full_name: "Mo Derator",
  staff_roles: ["moderator"],
  is_staff: true,
  is_superuser: false,
  account_status: "active",
  date_joined: "2026-06-01T09:00:00Z",
};

function mockFetch(payload, { ok = true, status = ok ? 200 : 500 } = {}) {
  const fetchMock = vi.fn(async (url) => {
    // CSRF preflight always succeeds; assertions target the staff calls.
    if (String(url).includes("/csrf")) {
      return { ok: true, status: 200, json: async () => ({ detail: "csrf cookie set" }) };
    }
    return { ok, status, json: async () => payload };
  });
  vi.stubGlobal("fetch", fetchMock);
  const callWith = (method) =>
    fetchMock.mock.calls.find(([, options]) => options?.method === method);
  return { fetchMock, callWith };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("staff accessors", () => {
  it("maps the application queue and forwards the status filter", async () => {
    const { fetchMock } = mockFetch({
      count: 1,
      items: [APPLICATION_PAYLOAD],
    });
    const data = await fetchApplicationQueue({
      status: "pending",
      q: "jianshop",
      page: 1,
    });

    expect(data.count).toBe(1);
    const [item] = data.items;
    expect(item.applicantEmail).toBe("bacayonjian@gmail.com");
    expect(item.storeSlug).toBe("jianshop");
    expect(item.status).toBe("pending");
    expect(item.rejectionReason).toBe("");
    expect(item.reviewedAt).toBeNull();

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/stores/admin/applications/?");
    expect(url).toContain("status=pending");
    expect(url).toContain("q=jianshop");
  });

  it("reviews an application with the decision and reason", async () => {
    const { callWith } = mockFetch({
      ...APPLICATION_PAYLOAD,
      status: "rejected",
      rejection_reason: "Contact details unverifiable.",
      reviewed_by: 7,
      reviewed_at: "2026-09-25T12:10:00Z",
    });
    const result = await reviewApplication(4, {
      decision: "rejected",
      reason: "Contact details unverifiable.",
    });

    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/stores/admin/applications/4/review");
    expect(JSON.parse(post[1].body)).toEqual({
      decision: "rejected",
      reason: "Contact details unverifiable.",
    });
    expect(result.status).toBe("rejected");
    expect(result.rejectionReason).toBe("Contact details unverifiable.");
    expect(result.reviewedBy).toBe(7);
  });

  it("maps staff store rows and forwards status/search filters", async () => {
    const { fetchMock } = mockFetch({ count: 1, items: [STORE_PAYLOAD] });
    const data = await fetchStaffStores({ status: "pending", q: "jian" });

    const [store] = data.items;
    expect(store.ownerEmail).toBe("bacayonjian@gmail.com");
    expect(store.ownerName).toBe("Jian Bacayon");
    expect(store.productCount).toBe(0);
    expect(store.suspendedAt).toBeNull();

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/stores/admin/stores/?");
    expect(url).toContain("status=pending");
    expect(url).toContain("q=jian");
  });

  it("suspends and activates a store through the audited endpoints", async () => {
    const { callWith } = mockFetch({ ...STORE_PAYLOAD, status: "suspended" });
    await setStoreStatus(2, "suspend", "Counterfeit report.");

    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/stores/admin/stores/2/suspend");
    expect(JSON.parse(post[1].body)).toEqual({ reason: "Counterfeit report." });

    const { callWith: callWith2 } = mockFetch({ ...STORE_PAYLOAD, status: "active" });
    const activated = await setStoreStatus(2, "activate", "Cleared.");
    const activatePost = callWith2("POST");
    expect(activatePost[0]).toBe("/api/v1/stores/admin/stores/2/activate");
    expect(activated.status).toBe("active");
  });

  it("maps audit events and forwards every filter", async () => {
    const { fetchMock } = mockFetch({ count: 1, items: [AUDIT_PAYLOAD] });
    const data = await fetchAuditEvents({
      actor: "admin@",
      action: "seller_application_approved",
      objectType: "stores.sellerapplication",
      objectId: "4",
      page: 2,
    });

    const [event] = data.items;
    expect(event.actorEmail).toBe("admin@example.com");
    expect(event.objectId).toBe("4");
    expect(event.detail.reason).toBe("");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/audit/events/?");
    expect(url).toContain("actor=admin%40");
    expect(url).toContain("action=seller_application_approved");
    expect(url).toContain("object_type=stores.sellerapplication");
    expect(url).toContain("object_id=4");
    expect(url).toContain("page=2");
  });

  it("throws the §8 error envelope, message and status intact", async () => {
    mockFetch(
      { error: "forbidden", detail: "Your staff group is not permitted for this action." },
      { ok: false, status: 403 }
    );
    await expect(fetchApplicationQueue()).rejects.toMatchObject({
      status: 403,
      message: "Your staff group is not permitted for this action.",
    });
  });

  it("maps admin user rows and forwards q/status/role/page", async () => {
    const { fetchMock } = mockFetch({ count: 1, items: [USER_PAYLOAD] });
    const data = await fetchAdminUsers({
      q: "bea",
      status: "suspended",
      role: "customer",
      page: 2,
    });

    const [account] = data.items;
    expect(account.fullName).toBe("Bea Buyer");
    expect(account.accountStatus).toBe("suspended");
    expect(account.suspendedAt).toBe("2026-09-26T08:00:00Z");
    expect(account.emailVerified).toBe(true);

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/auth/admin/users/?");
    expect(url).toContain("q=bea");
    expect(url).toContain("status=suspended");
    expect(url).toContain("role=customer");
    expect(url).toContain("page=2");
  });

  it("fetches one user's detail record", async () => {
    const { fetchMock } = mockFetch(USER_PAYLOAD);
    const account = await fetchAdminUser(12);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/auth/admin/users/12/");
    expect(account.id).toBe(12);
    expect(account.isStaff).toBe(false);
  });

  it("suspends and reactivates through the audited endpoints", async () => {
    const { callWith } = mockFetch(USER_PAYLOAD);
    const suspended = await setUserStatus(12, "suspend", "Abuse report.");
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/auth/admin/users/12/suspend");
    expect(JSON.parse(post[1].body)).toEqual({ reason: "Abuse report." });
    expect(suspended.accountStatus).toBe("suspended");

    const { callWith: callWith2 } = mockFetch({
      ...USER_PAYLOAD,
      account_status: "active",
      suspended_at: null,
    });
    const active = await setUserStatus(12, "reactivate", "Cleared.");
    expect(callWith2("POST")[0]).toBe("/api/v1/auth/admin/users/12/reactivate");
    expect(active.accountStatus).toBe("active");
  });

  it("maps the staff directory and forwards the search filter", async () => {
    const { fetchMock } = mockFetch({ count: 1, items: [STAFF_MEMBER_PAYLOAD] });
    const data = await fetchStaffMembers({ q: "mod@", page: 1 });

    const [member] = data.items;
    expect(member.staffRoles).toEqual(["moderator"]);
    expect(member.isSuperuser).toBe(false);

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/auth/admin/staff/?");
    expect(url).toContain("q=mod%40");
    expect(url).toContain("page=1");
  });

  it("assigns and removes staff roles with the group payload", async () => {
    const { callWith } = mockFetch({
      ...STAFF_MEMBER_PAYLOAD,
      staff_roles: ["moderator", "support"],
    });
    const updated = await changeStaffRole(3, "assign", "support");
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/auth/admin/staff/3/roles/assign");
    expect(JSON.parse(post[1].body)).toEqual({ group: "support" });
    expect(updated.staffRoles).toEqual(["moderator", "support"]);

    const { callWith: callWith2 } = mockFetch(STAFF_MEMBER_PAYLOAD);
    await changeStaffRole(3, "remove", "support");
    expect(callWith2("POST")[0]).toBe("/api/v1/auth/admin/staff/3/roles/remove");
  });
});

describe("order & payment oversight accessors (13.5)", () => {
  it("maps order rows and forwards the server-side filters", async () => {
    const { fetchMock } = mockFetch({
      count: 1,
      items: [
        {
          number: "JV-20260926-ABCD2345",
          status: "shipped",
          created_at: "2026-09-26T02:00:00Z",
          customer_email: "buyer@example.com",
          ship_to_city: "Cebu City",
          ship_to_province: "Cebu",
          grand_total: 349,
          item_count: 2,
          store_names: ["JianShop"],
          payment_method: "cod",
          payment_status: "pending",
        },
      ],
    });
    const data = await fetchStaffOrders({
      q: "JV-2026",
      status: "shipped",
      store: "jianshop",
      payment: "pending",
      page: 2,
      pageSize: 10,
    });

    expect(data.count).toBe(1);
    const [order] = data.items;
    expect(order.number).toBe("JV-20260926-ABCD2345");
    expect(order.customerEmail).toBe("buyer@example.com");
    expect(order.grandTotal).toBe(349);
    expect(order.storeNames).toEqual(["JianShop"]);
    expect(order.paymentMethod).toBe("cod");
    expect(order.paymentStatus).toBe("pending");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/admin/orders/?");
    expect(url).toContain("q=JV-2026");
    expect(url).toContain("status=shipped");
    expect(url).toContain("store=jianshop");
    expect(url).toContain("payment=pending");
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=10");
  });

  it("maps the staff order detail snapshot", async () => {
    const { fetchMock } = mockFetch({
      number: "JV-20260926-ABCD2345",
      status: "paid",
      created_at: "2026-09-26T02:00:00Z",
      item_count: 1,
      customer_email: "buyer@example.com",
      can_cancel: false,
      payment: {
        reference: "JVPAY-20260926-8F3K2Q7A",
        method: "cod",
        status: "paid",
        amount: 349,
        currency: "PHP",
        provider: "",
        refunded_total: 50,
        paid_at: "2026-09-26T03:00:00Z",
      },
      shipping_address: {
        full_name: "Bea Buyer",
        phone: "+63 917 111 2222",
        line1: "12 Mabini Street",
        line2: "",
        city: "Cebu City",
        province: "Cebu",
        postal_code: "6000",
      },
      totals: {
        subtotal: 299,
        shipping_total: 50,
        savings_total: 0,
        tax_total: 0,
        grand_total: 349,
      },
      seller_orders: [
        {
          id: 8,
          store_name: "JianShop",
          status: "shipped",
          subtotal: 299,
          shipping_fee: 50,
          total: 349,
          items: [
            {
              id: 15,
              title: "Handmade Basket",
              variant_name: "Large",
              sku: "BASKET-L",
              quantity: 1,
              line_total: 299,
            },
          ],
        },
      ],
      requests: [
        {
          id: 4,
          kind: "return",
          kind_label: "Return",
          status: "pending",
          reason: "Wrong size",
          store_name: "JianShop",
          created_at: "2026-09-26T04:00:00Z",
        },
      ],
    });
    const detail = await fetchStaffOrderDetail("JV-20260926-ABCD2345");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/admin/orders/JV-20260926-ABCD2345/"
    );
    expect(detail.customerEmail).toBe("buyer@example.com");
    expect(detail.canCancel).toBe(false);
    expect(detail.payment.refundedTotal).toBe(50);
    expect(detail.totals.grandTotal).toBe(349);
    expect(detail.stores[0].storeName).toBe("JianShop");
    expect(detail.stores[0].items[0].title).toBe("Handmade Basket");
    expect(detail.requests[0].kindLabel).toBe("Return");
  });

  it("maps shipment rows and forwards status/carrier filters", async () => {
    const { fetchMock } = mockFetch({
      count: 1,
      items: [
        {
          tracking_number: "JVTRK-20260926-0001",
          order_number: "JV-20260926-ABCD2345",
          store_name: "JianShop",
          carrier: "jtex",
          carrier_name: "J&T Express",
          status: "in_transit",
          shipped_at: "2026-09-26T05:00:00Z",
          delivered_at: null,
          event_count: 3,
          created_at: "2026-09-26T04:30:00Z",
        },
      ],
    });
    const data = await fetchStaffShipments({
      status: "in_transit",
      carrier: "jtex",
      q: "JVTRK",
    });

    const [shipment] = data.items;
    expect(shipment.trackingNumber).toBe("JVTRK-20260926-0001");
    expect(shipment.orderNumber).toBe("JV-20260926-ABCD2345");
    expect(shipment.eventCount).toBe(3);
    expect(shipment.deliveredAt).toBeNull();

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/admin/shipments/?");
    expect(url).toContain("status=in_transit");
    expect(url).toContain("carrier=jtex");
    expect(url).toContain("q=JVTRK");
  });

  it("maps request rows and forwards kind/status filters", async () => {
    const { fetchMock } = mockFetch({
      count: 1,
      items: [
        {
          id: 4,
          kind: "refund",
          kind_label: "Refund",
          status: "pending",
          reason: "Item arrived broken",
          description: "",
          store_name: "JianShop",
          order_number: "JV-20260926-ABCD2345",
          customer_email: "buyer@example.com",
          created_at: "2026-09-26T06:00:00Z",
        },
      ],
    });
    const data = await fetchStaffRequests({ kind: "refund", status: "pending" });

    const [request] = data.items;
    expect(request.orderNumber).toBe("JV-20260926-ABCD2345");
    expect(request.customerEmail).toBe("buyer@example.com");
    expect(request.kindLabel).toBe("Refund");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/admin/requests/?");
    expect(url).toContain("kind=refund");
    expect(url).toContain("status=pending");
  });

  it("maps payment rows and forwards method/status filters", async () => {
    const { fetchMock } = mockFetch({
      count: 1,
      items: [
        {
          reference: "JVPAY-20260926-8F3K2Q7A",
          order_number: "JV-20260926-ABCD2345",
          customer_email: "buyer@example.com",
          method: "gcash",
          status: "partially_refunded",
          amount: 349,
          currency: "PHP",
          provider: "paymongo",
          refunded_total: 50,
          paid_at: "2026-09-26T03:00:00Z",
          created_at: "2026-09-26T02:05:00Z",
        },
      ],
    });
    const data = await fetchStaffPayments({ method: "gcash", status: "paid" });

    const [payment] = data.items;
    expect(payment.reference).toBe("JVPAY-20260926-8F3K2Q7A");
    expect(payment.refundedTotal).toBe(50);
    expect(payment.orderNumber).toBe("JV-20260926-ABCD2345");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/payments/admin/payments/?");
    expect(url).toContain("method=gcash");
    expect(url).toContain("status=paid");
  });

  it("maps refund rows with the issuing staff member", async () => {
    const { fetchMock } = mockFetch({
      count: 1,
      items: [
        {
          reference: "JVREF-20260926-2M8XW4QP",
          payment_reference: "JVPAY-20260926-8F3K2Q7A",
          order_number: "JV-20260926-ABCD2345",
          amount: 50,
          status: "succeeded",
          reason: "Goodwill credit",
          issued_by: "finance@jeyvro.ph",
          created_at: "2026-09-26T07:00:00Z",
        },
      ],
    });
    const data = await fetchStaffRefunds({ status: "succeeded" });

    const [refund] = data.items;
    expect(refund.reference).toBe("JVREF-20260926-2M8XW4QP");
    expect(refund.paymentReference).toBe("JVPAY-20260926-8F3K2Q7A");
    expect(refund.issuedBy).toBe("finance@jeyvro.ph");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/payments/admin/refunds/?");
    expect(url).toContain("status=succeeded");
  });
});

describe("staff catalog accessors (13.4)", () => {
  const PRODUCT_PAYLOAD = {
    id: 31,
    title: "Rattan Chair",
    slug: "rattan-chair",
    status: "pending_review",
    rejection_reason: "",
    base_price: "1299.00",
    compare_at_price: "1599.00",
    display_price: "1299.00",
    store_name: "JianShop",
    store_slug: "jianshop",
    store_owner_email: "bacayonjian@gmail.com",
    category_name: "Home & Living",
    category_slug: "home-living",
    brand_name: "Rattan Co",
    variant_count: 2,
    image_count: 3,
    primary_image: "http://testserver/media/products/a.png",
    created_at: "2026-09-26T08:00:00Z",
    updated_at: "2026-09-26T09:00:00Z",
  };

  const CATEGORY_PAYLOAD = {
    id: 7,
    parent: null,
    name: "Home & Living",
    slug: "home-living",
    description: "Nest goods.",
    position: 1,
    is_active: true,
    product_count: 4,
  };

  const BRAND_PAYLOAD = {
    id: 3,
    name: "Rattan Co",
    slug: "rattan-co",
    product_count: 2,
  };

  it("maps console rows (numbers parsed) and forwards every filter", async () => {
    const { fetchMock } = mockFetch({ count: 1, items: [PRODUCT_PAYLOAD] });
    const data = await fetchAdminProducts({
      q: "rattan",
      status: "pending_review",
      store: "jianshop",
      category: "home-living",
      page: 2,
      pageSize: 10,
    });

    const [row] = data.items;
    expect(row.storeOwnerEmail).toBe("bacayonjian@gmail.com");
    expect(row.displayPrice).toBe(1299);
    expect(row.compareAtPrice).toBe(1599);
    expect(row.variantCount).toBe(2);
    expect(row.status).toBe("pending_review");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/catalog/admin/products/?");
    expect(url).toContain("status=pending_review");
    expect(url).toContain("store=jianshop");
    expect(url).toContain("category=home-living");
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=10");
  });

  it("publishes/rejects through the review endpoint", async () => {
    const { callWith } = mockFetch({ ...PRODUCT_PAYLOAD, status: "rejected" });
    const updated = await reviewProduct(31, "rejected", "Counterfeit listing.");
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/catalog/admin/products/31/review");
    expect(JSON.parse(post[1].body)).toEqual({
      decision: "rejected",
      reason: "Counterfeit listing.",
    });
    expect(updated.status).toBe("rejected");
  });

  it("takes down a published product with a reason", async () => {
    const { callWith } = mockFetch({ ...PRODUCT_PAYLOAD, status: "unpublished" });
    await unpublishProduct(31, "Unverified claim.");
    const post = callWith("POST");
    expect(post[0]).toBe("/api/v1/catalog/admin/products/31/unpublish");
    expect(JSON.parse(post[1].body)).toEqual({ reason: "Unverified claim." });
  });

  it("maps taxonomy rows and writes categories through the audited endpoints", async () => {
    const { fetchMock } = mockFetch({ count: 1, items: [CATEGORY_PAYLOAD] });
    const data = await fetchAdminCategories({ q: "home", pageSize: 100 });
    const [category] = data.items;
    expect(category.parentId).toBeNull();
    expect(category.productCount).toBe(4);
    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/catalog/admin/categories/?");
    expect(url).toContain("q=home");
    expect(url).toContain("page_size=100");

    const { callWith } = mockFetch(CATEGORY_PAYLOAD);
    const created = await createCategory({ name: "Home & Living" });
    expect(callWith("POST")[0]).toBe("/api/v1/catalog/admin/categories/");
    expect(JSON.parse(callWith("POST")[1].body)).toEqual({ name: "Home & Living" });
    expect(created.slug).toBe("home-living");

    const { callWith: callWith2 } = mockFetch({ ...CATEGORY_PAYLOAD, name: "Rugs" });
    const renamed = await updateCategory(7, { name: "Rugs" });
    expect(callWith2("PATCH")[0]).toBe("/api/v1/catalog/admin/categories/7/");
    expect(renamed.name).toBe("Rugs");

    const { callWith: callWith3 } = mockFetch(null);
    await deleteCategory(7);
    expect(callWith3("DELETE")[0]).toBe("/api/v1/catalog/admin/categories/7/");
  });

  it("creates and deletes brands through the audited endpoints", async () => {
    const { callWith } = mockFetch(BRAND_PAYLOAD);
    const created = await createBrand({ name: "Rattan Co" });
    expect(callWith("POST")[0]).toBe("/api/v1/catalog/admin/brands/");
    expect(JSON.parse(callWith("POST")[1].body)).toEqual({ name: "Rattan Co" });
    expect(created.slug).toBe("rattan-co");

    const { fetchMock } = mockFetch({ count: 1, items: [BRAND_PAYLOAD] });
    const data = await fetchAdminBrands({ q: "rattan" });
    expect(data.items[0].productCount).toBe(2);
    expect(fetchMock.mock.calls[0][0]).toContain("/api/v1/catalog/admin/brands/?q=rattan");

    const { callWith: callWith2 } = mockFetch(null);
    await deleteBrand(3);
    expect(callWith2("DELETE")[0]).toBe("/api/v1/catalog/admin/brands/3/");
  });
});

describe("platform settings accessors (13.6)", () => {
  const SETTINGS_PAYLOAD = {
    platform_name: "Jeyvro",
    support_email: "support@jeyvro.com",
    commission_rate_percent: "5.00",
    default_shipping_flat_fee: "49.00",
    default_free_shipping_threshold: null,
    cod_enabled: true,
    payment_expiry_hours: 24,
    default_order_updates_email: true,
    default_promotions_email: false,
    default_messaging_email: true,
    updated_at: "2026-09-26T10:00:00Z",
    updated_by_email: "admin@jeyvro.ph",
  };

  it("fetches and maps the full settings row (nullable threshold kept)", async () => {
    const { fetchMock } = mockFetch(SETTINGS_PAYLOAD);
    const settings = await fetchStaffSettings();

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/admin/settings/");
    expect(settings.platformName).toBe("Jeyvro");
    expect(settings.supportEmail).toBe("support@jeyvro.com");
    expect(settings.commissionRatePercent).toBe("5.00");
    expect(settings.defaultShippingFlatFee).toBe("49.00");
    expect(settings.defaultFreeShippingThreshold).toBeNull();
    expect(settings.codEnabled).toBe(true);
    expect(settings.paymentExpiryHours).toBe(24);
    expect(settings.defaultOrderUpdatesEmail).toBe(true);
    expect(settings.defaultPromotionsEmail).toBe(false);
    expect(settings.defaultMessagingEmail).toBe(true);
    expect(settings.updatedAt).toBe("2026-09-26T10:00:00Z");
    expect(settings.updatedByEmail).toBe("admin@jeyvro.ph");
  });

  it("PATCHes general settings through the administrator path", async () => {
    const { callWith } = mockFetch({
      ...SETTINGS_PAYLOAD,
      platform_name: "Jeyvro PH",
    });
    const updated = await updateStaffSettings({ platform_name: "Jeyvro PH" });

    const patch = callWith("PATCH");
    expect(patch[0]).toBe("/api/v1/admin/settings/");
    expect(JSON.parse(patch[1].body)).toEqual({ platform_name: "Jeyvro PH" });
    expect(updated.platformName).toBe("Jeyvro PH");
  });

  it("PATCHes commission through the finance path", async () => {
    const { callWith } = mockFetch({
      ...SETTINGS_PAYLOAD,
      commission_rate_percent: "7.50",
    });
    const updated = await updateStaffCommission({
      commission_rate_percent: "7.50",
    });

    const patch = callWith("PATCH");
    expect(patch[0]).toBe("/api/v1/admin/settings/commission/");
    expect(JSON.parse(patch[1].body)).toEqual({
      commission_rate_percent: "7.50",
    });
    expect(updated.commissionRatePercent).toBe("7.50");
  });

  it("maps a fresh row's defaults before the first edit", async () => {
    mockFetch({
      platform_name: "Jeyvro",
      support_email: "support@jeyvro.com",
      commission_rate_percent: "0.00",
      default_shipping_flat_fee: "0.00",
      default_free_shipping_threshold: null,
      cod_enabled: false,
      payment_expiry_hours: 12,
      default_order_updates_email: false,
      default_promotions_email: true,
      default_messaging_email: false,
      updated_at: null,
      updated_by_email: null,
    });
    const settings = await fetchStaffSettings();
    expect(settings.codEnabled).toBe(false);
    expect(settings.paymentExpiryHours).toBe(12);
    expect(settings.updatedAt).toBeNull();
    expect(settings.updatedByEmail).toBeNull();
  });
});

describe("analytics accessors (19.1)", () => {
  const SUMMARY_PAYLOAD = {
    start: "2026-09-25",
    end: "2026-09-30",
    totals: {
      start: "2026-09-25",
      end: "2026-09-30",
      orders_count: 4,
      orders_cancelled: 5,
      orders_paid: 0,
      units_sold: 22,
      products_sold: 6,
      customer_days: 2,
      seller_days: 6,
      gmv: "28578.00",
      merchandise: "28578.00",
      shipping: "0.00",
      discounts: "0.00",
      captured_total: "0.00",
      refunded_total: "0.00",
      revenue: "0.00",
      commission_base: "0.00",
      commission: "0.00",
    },
    days: [
      {
        day: "2026-09-29",
        orders_count: 1,
        orders_cancelled: 0,
        orders_paid: 0,
        units_sold: 1,
        products_sold: 1,
        active_customers: 1,
        active_sellers: 1,
        gmv: "1500.00",
        merchandise: "1500.00",
        shipping: "0.00",
        discounts: "0.00",
        captured_total: "0.00",
        refunded_total: "0.00",
        revenue: "0.00",
        commission_base: "0.00",
        commission: "0.00",
        commission_rate_percent: "0.00",
      },
    ],
  };

  it("fetches the summary, keeping money as strings and summing nothing", async () => {
    const { fetchMock } = mockFetch(SUMMARY_PAYLOAD);
    const summary = await fetchStaffAnalyticsSummary({
      from: "2026-09-01",
      to: "2026-09-30",
    });

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/admin/analytics/summary/?");
    expect(url).toContain("from=2026-09-01");
    expect(url).toContain("to=2026-09-30");

    expect(summary.totals.gmv).toBe("28578.00");
    expect(summary.totals.commission).toBe("0.00");
    expect(summary.totals.ordersCount).toBe(4);
    // Day counts are summed, so they are named for the day they came from —
    // never dressed up as distinct people.
    expect(summary.totals.customerDays).toBe(2);

    const [day] = summary.days;
    expect(day.day).toBe("2026-09-29");
    expect(day.gmv).toBe("1500.00");
    expect(day.commissionRatePercent).toBe("0.00");
    expect(day.activeCustomers).toBe(1);
  });

  it("asks for the bare endpoint when no range is given", async () => {
    const { fetchMock } = mockFetch(SUMMARY_PAYLOAD);
    await fetchStaffAnalyticsSummary();
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/admin/analytics/summary/"
    );
  });

  it("maps the store leaderboard, seller-funded discount included", async () => {
    const { fetchMock } = mockFetch({
      start: "2026-09-01",
      end: "2026-09-30",
      items: [
        {
          store_id: 8,
          store__name: "Ilocos Weavers",
          store__slug: "ilocos-weavers",
          orders_count: 1,
          units_sold: 1,
          gross_sales: "1500.00",
          merchandise: "1500.00",
          seller_funded_discount: "0.00",
          captured_total: "0.00",
          refunded_total: "0.00",
          revenue: "0.00",
          commission_base: "0.00",
          commission: "0.00",
        },
      ],
    });
    const rows = await fetchStaffAnalyticsStores({
      from: "2026-09-01",
      to: "2026-09-30",
      limit: 10,
    });

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/admin/analytics/stores/?");
    expect(url).toContain("from=2026-09-01");
    expect(url).toContain("limit=10");

    const [row] = rows;
    expect(row.storeId).toBe(8);
    expect(row.storeName).toBe("Ilocos Weavers");
    expect(row.storeSlug).toBe("ilocos-weavers");
    // The discount the store itself funded is the figure the commission base
    // was cut against, so it travels with the row rather than being inferred.
    expect(row.sellerFundedDiscount).toBe("0.00");
    expect(row.commissionBase).toBe("0.00");
  });

  it("maps product activity rows", async () => {
    const { fetchMock } = mockFetch({
      start: "2026-09-01",
      end: "2026-09-30",
      items: [
        {
          product_id: 7,
          product__title: "Inabel Woven Throw Blanket",
          store_id: 8,
          store__name: "Ilocos Weavers",
          units_sold: 1,
          orders_count: 1,
          merchandise: "1500.00",
        },
      ],
    });
    const rows = await fetchStaffAnalyticsProducts({
      from: "2026-09-01",
      to: "2026-09-30",
      limit: 10,
    });

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/api/v1/admin/analytics/products/"
    );
    const [row] = rows;
    expect(row.productId).toBe(7);
    expect(row.productTitle).toBe("Inabel Woven Throw Blanket");
    expect(row.storeName).toBe("Ilocos Weavers");
    expect(row.merchandise).toBe("1500.00");
  });

  it("renders zeroes, not undefined, when a range has no rows at all", async () => {
    mockFetch({ start: "2026-09-01", end: "2026-09-30", totals: {}, days: [] });
    const summary = await fetchStaffAnalyticsSummary();
    expect(summary.totals.gmv).toBe("0.00");
    expect(summary.totals.ordersCount).toBe(0);
    expect(summary.totals.customerDays).toBe(0);
    expect(summary.totals.start).toBeNull();
    expect(summary.days).toEqual([]);

    const { fetchMock } = mockFetch({ start: "2026-09-01", end: "2026-09-30" });
    expect(await fetchStaffAnalyticsStores()).toEqual([]);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/admin/analytics/stores/");
  });
});

describe("operational analytics accessors (19.3)", () => {
  it("maps the operational day — counts as the server derived them", async () => {
    const { fetchMock } = mockFetch({
      start: "2026-09-01",
      end: "2026-09-30",
      totals: {
        start: "2026-09-01",
        end: "2026-09-30",
        orders_open: 3,
        orders_completed: 12,
        orders_cancelled: 1,
        orders_refunded: 2,
        shipments_created: 11,
        shipments_delivered: 9,
        returns_filed: 4,
        returns_approved: 3,
        returns_rejected: 1,
        returns_received: 2,
        refunds_issued: 3,
        refunds_settled: 2,
        requests_filed: 5,
        conversations_opened: 6,
        messages_sent: 27,
        disputes_opened: 1,
        disputes_resolved: 1,
      },
      days: [
        {
          day: "2026-09-29",
          orders_open: 1,
          orders_completed: 2,
          orders_cancelled: 0,
          orders_refunded: 0,
          shipments_created: 2,
          shipments_delivered: 1,
          returns_filed: 1,
          returns_approved: 1,
          returns_rejected: 0,
          returns_received: 0,
          refunds_issued: 1,
          refunds_settled: 0,
          requests_filed: 2,
          conversations_opened: 1,
          messages_sent: 8,
          disputes_opened: 0,
          disputes_resolved: 0,
        },
      ],
    });
    const operations = await fetchStaffAnalyticsOperations({
      from: "2026-09-01",
      to: "2026-09-30",
    });

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/admin/analytics/operations/?");
    expect(url).toContain("from=2026-09-01");
    expect(url).toContain("to=2026-09-30");

    expect(operations.totals.ordersOpen).toBe(3);
    expect(operations.totals.ordersCompleted).toBe(12);
    expect(operations.totals.shipmentsDelivered).toBe(9);
    expect(operations.totals.returnsFiled).toBe(4);
    // Settled refunds are the ledger's count, kept distinct from the issued ones.
    expect(operations.totals.refundsIssued).toBe(3);
    expect(operations.totals.refundsSettled).toBe(2);
    expect(operations.totals.messagesSent).toBe(27);
    const [day] = operations.days;
    expect(day.day).toBe("2026-09-29");
    expect(day.messagesSent).toBe(8);
  });

  it("maps store performance rows without inventing a rate", async () => {
    const { fetchMock } = mockFetch({
      start: "2026-09-01",
      end: "2026-09-30",
      items: [
        {
          store_id: 8,
          store__name: "Ilocos Weavers",
          shipments_created: 4,
          shipments_delivered: 3,
          returns_filed: 1,
          returns_received: 1,
          disputes_opened: 0,
          requests_filed: 2,
          messages_sent: 11,
        },
      ],
    });
    const rows = await fetchStaffAnalyticsPerformance({
      from: "2026-09-01",
      to: "2026-09-30",
      limit: 10,
    });

    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/v1/admin/analytics/performance/?");
    expect(url).toContain("limit=10");

    const [row] = rows;
    expect(row.storeId).toBe(8);
    expect(row.storeName).toBe("Ilocos Weavers");
    expect(row.shipmentsCreated).toBe(4);
    expect(row.shipmentsDelivered).toBe(3);
    expect(row.returnsReceived).toBe(1);
    expect(row.messagesSent).toBe(11);
    // Counts only: the page never divides two of them into a rate itself.
    expect(row.ontimeRate).toBeUndefined();
  });

  it("renders zeroes for an unbuilt operations row instead of undefined", async () => {
    mockFetch({ start: null, end: null, totals: {}, days: [] });
    const operations = await fetchStaffAnalyticsOperations();
    expect(operations.totals.ordersOpen).toBe(0);
    expect(operations.totals.returnsFiled).toBe(0);
    expect(operations.totals.disputesResolved).toBe(0);
    expect(operations.totals.start).toBeNull();
    expect(operations.days).toEqual([]);

    const { fetchMock } = mockFetch({ items: [] });
    expect(await fetchStaffAnalyticsPerformance()).toEqual([]);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/admin/analytics/performance/"
    );
  });
});

describe("report export links (19.4)", () => {
  it("builds the download URL for a report with the page's range", () => {
    expect(
      staffAnalyticsCsvUrl("summary", { from: "2026-09-01", to: "2026-09-30" })
    ).toBe(
      "/api/v1/admin/analytics/export/summary/?from=2026-09-01&to=2026-09-30"
    );
    // No range means the server's default window — not an empty query string.
    expect(staffAnalyticsCsvUrl("operations")).toBe(
      "/api/v1/admin/analytics/export/operations/"
    );
  });

  it("names every report and which gate it belongs to", () => {
    expect(STAFF_ANALYTICS_REPORTS.map((report) => report.slug)).toEqual([
      "summary",
      "stores",
      "products",
      "operations",
      "performance",
    ]);
    // The money reports are the two the API gates to finance/administrator.
    expect(
      STAFF_ANALYTICS_REPORTS.filter((report) => report.money).map(
        (report) => report.slug
      )
    ).toEqual(["summary", "stores"]);
  });
});


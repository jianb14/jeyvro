import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchApplicationQueue,
  fetchAuditEvents,
  fetchStaffStores,
  reviewApplication,
  setStoreStatus,
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
});

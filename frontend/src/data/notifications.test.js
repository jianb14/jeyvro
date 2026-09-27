import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchNotifications,
  fetchUnreadNotificationCount,
  mapNotification,
  markAllNotificationsAsRead,
  markNotificationAsRead,
} from "./notifications";

const NOTIF_PAYLOAD = {
  id: 1,
  category: "orders",
  title: "Order Shipped",
  message: "Your package is on the way.",
  action_url: "/orders/JV-1234",
  is_read: false,
  read_at: null,
  created_at: "2026-09-27T10:00:00Z",
};

function mockFetch(payload, { ok = true, status = ok ? 200 : 500 } = {}) {
  const fetchMock = vi.fn(async (url) => {
    if (String(url).includes("/csrf")) {
      return { ok: true, status: 200, json: async () => ({ csrfToken: "test-token" }) };
    }
    return { ok, status, json: async () => payload };
  });
  globalThis.fetch = fetchMock;
  return fetchMock;
}

describe("notifications data accessors", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps notification shape correctly", () => {
    const mapped = mapNotification(NOTIF_PAYLOAD);
    expect(mapped.id).toBe(1);
    expect(mapped.category).toBe("orders");
    expect(mapped.title).toBe("Order Shipped");
    expect(mapped.actionUrl).toBe("/orders/JV-1234");
    expect(mapped.isRead).toBe(false);
  });

  it("fetches notifications list and unread count", () => {
    mockFetch({ count: 1, unread_count: 1, items: [NOTIF_PAYLOAD] });
    return fetchNotifications().then((res) => {
      expect(res.count).toBe(1);
      expect(res.unreadCount).toBe(1);
      expect(res.items.length).toBe(1);
      expect(res.items[0].title).toBe("Order Shipped");
    });
  });

  it("fetches unread count endpoint", () => {
    mockFetch({ unread_count: 5 });
    return fetchUnreadNotificationCount().then((count) => {
      expect(count).toBe(5);
    });
  });

  it("marks single notification as read", () => {
    mockFetch({ ...NOTIF_PAYLOAD, is_read: true, read_at: "2026-09-27T11:00:00Z" });
    return markNotificationAsRead(1).then((res) => {
      expect(res.isRead).toBe(true);
      expect(res.readAt).toBe("2026-09-27T11:00:00Z");
    });
  });

  it("marks all notifications as read", () => {
    mockFetch({ updated: 3, unread_count: 0 });
    return markAllNotificationsAsRead().then((res) => {
      expect(res.unread_count).toBe(0);
    });
  });
});

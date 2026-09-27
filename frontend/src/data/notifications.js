/**
 * Notification accessors (Phase 15 — ROADMAP §15.2).
 *
 * Single data access point for in-app notifications and unread badge counts.
 */
import { ensureCsrfToken, request } from "../lib/api";

const BASE = "/api/v1";

export function mapNotification(n) {
  return {
    id: n.id,
    category: n.category,
    title: n.title,
    message: n.message,
    actionUrl: n.action_url ?? "",
    isRead: Boolean(n.is_read),
    readAt: n.read_at ?? null,
    createdAt: n.created_at,
  };
}

export async function fetchNotifications({ unreadOnly = false, category = null } = {}) {
  const params = new URLSearchParams();
  if (unreadOnly) params.set("unread", "1");
  if (category) params.set("category", category);
  const query = params.toString();

  const data = await request(BASE, `/notifications/${query ? `?${query}` : ""}`);
  return {
    count: data.count ?? 0,
    unreadCount: data.unread_count ?? 0,
    items: (data.items ?? []).map(mapNotification),
  };
}

export async function fetchUnreadNotificationCount() {
  const data = await request(BASE, "/notifications/unread-count/");
  return data.unread_count ?? 0;
}

export async function markNotificationAsRead(id) {
  const csrf = await ensureCsrfToken();
  const data = await request(BASE, `/notifications/${id}/read/`, {
    method: "POST",
    csrf,
  });
  return mapNotification(data);
}

export async function markAllNotificationsAsRead() {
  const csrf = await ensureCsrfToken();
  return request(BASE, "/notifications/read-all/", {
    method: "POST",
    csrf,
  });
}

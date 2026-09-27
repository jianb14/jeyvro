/**
 * Messaging accessors (Phase 15 — ROADMAP §15.1, §12.6).
 *
 * Single data access point for customer and seller conversations and threads.
 */
import { ensureCsrfToken, request } from "../lib/api";

const BASE = "/api/v1";

export function mapMessage(m) {
  return {
    id: m.id,
    conversationId: m.conversation,
    senderId: m.sender_id,
    sender: m.sender,
    body: m.body ?? "",
    attachmentUrl: m.attachment_url ?? "",
    isSystem: Boolean(m.is_system),
    isMe: Boolean(m.is_me),
    createdAt: m.created_at,
  };
}

export function mapConversation(c) {
  return {
    id: c.id,
    type: c.type,
    customer: c.customer,
    storeId: c.store,
    storeName: c.store_name ?? "",
    storeSlug: c.store_slug ?? "",
    orderId: c.order,
    orderNumber: c.order_number ?? null,
    productId: c.product,
    productTitle: c.product_title ?? null,
    productSlug: c.product_slug ?? null,
    subject: c.subject ?? "",
    status: c.status,
    unreadCount: c.unread_count ?? 0,
    lastMessage: c.last_message ? {
      id: c.last_message.id,
      body: c.last_message.body,
      senderId: c.last_message.sender_id,
      createdAt: c.last_message.created_at,
    } : null,
    messages: (c.messages ?? []).map(mapMessage),
    createdAt: c.created_at,
    updatedAt: c.updated_at,
  };
}

export async function fetchCustomerConversations() {
  const data = await request(BASE, "/conversations/");
  return {
    count: data.count ?? 0,
    unreadCount: data.unread_count ?? 0,
    items: (data.items ?? []).map(mapConversation),
  };
}

export async function fetchSellerConversations() {
  const data = await request(BASE, "/seller/conversations/");
  return {
    count: data.count ?? 0,
    unreadCount: data.unread_count ?? 0,
    items: (data.items ?? []).map(mapConversation),
  };
}

export async function fetchConversation(id) {
  const data = await request(BASE, `/conversations/${id}/`);
  return mapConversation(data);
}

export async function startConversation({ storeId, orderId, productId, type = "seller", subject = "", message = "" }) {
  const csrf = await ensureCsrfToken();
  const data = await request(BASE, "/conversations/", {
    method: "POST",
    csrf,
    body: {
      store_id: storeId,
      order_id: orderId,
      product_id: productId,
      type,
      subject,
      message,
    },
  });
  return mapConversation(data);
}

export async function sendMessage(conversationId, { body = "", attachmentUrl = "" }) {
  const csrf = await ensureCsrfToken();
  const data = await request(BASE, `/conversations/${conversationId}/messages/`, {
    method: "POST",
    csrf,
    body: { body, attachment_url: attachmentUrl },
  });
  return mapMessage(data);
}

export async function markConversationRead(conversationId) {
  const csrf = await ensureCsrfToken();
  return request(BASE, `/conversations/${conversationId}/read/`, {
    method: "POST",
    csrf,
  });
}

export async function reportConversation(conversationId, { reason, details = "" }) {
  const csrf = await ensureCsrfToken();
  return request(BASE, `/conversations/${conversationId}/report/`, {
    method: "POST",
    csrf,
    body: { reason, details },
  });
}

export async function fetchUnreadMessagesCount() {
  const data = await request(BASE, "/conversations/unread-count/");
  return data.unread_count ?? 0;
}

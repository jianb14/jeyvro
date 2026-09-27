import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchConversation,
  fetchCustomerConversations,
  fetchSellerConversations,
  fetchUnreadMessagesCount,
  mapConversation,
  mapMessage,
  markConversationRead,
  reportConversation,
  sendMessage,
  startConversation,
} from "./messaging";

const CONV_PAYLOAD = {
  id: 10,
  type: "seller",
  customer: { id: 2, email: "buyer@example.com", first_name: "Buyer", last_name: "Test" },
  store: 1,
  store_name: "Artisan Goods",
  store_slug: "artisan-goods",
  order: 5,
  order_number: "JV-2026-1234",
  product: 8,
  product_title: "Handmade Mug",
  product_slug: "handmade-mug",
  subject: "Question regarding order",
  status: "open",
  unread_count: 2,
  last_message: {
    id: 99,
    body: "Can you ship tomorrow?",
    sender_id: 2,
    created_at: "2026-09-27T12:00:00Z",
  },
  messages: [
    {
      id: 98,
      conversation: 10,
      sender_id: 1,
      sender: { id: 1, email: "seller@example.com" },
      body: "Hello!",
      attachment_url: "",
      is_system: false,
      is_me: false,
      created_at: "2026-09-27T11:00:00Z",
    },
    {
      id: 99,
      conversation: 10,
      sender_id: 2,
      sender: { id: 2, email: "buyer@example.com" },
      body: "Can you ship tomorrow?",
      attachment_url: "",
      is_system: false,
      is_me: true,
      created_at: "2026-09-27T12:00:00Z",
    },
  ],
  created_at: "2026-09-27T10:00:00Z",
  updated_at: "2026-09-27T12:00:00Z",
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

describe("messaging data accessors", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps conversation and messages correctly", () => {
    const mapped = mapConversation(CONV_PAYLOAD);
    expect(mapped.id).toBe(10);
    expect(mapped.storeName).toBe("Artisan Goods");
    expect(mapped.orderNumber).toBe("JV-2026-1234");
    expect(mapped.unreadCount).toBe(2);
    expect(mapped.messages.length).toBe(2);
    expect(mapped.messages[1].isMe).toBe(true);
  });

  it("fetches customer conversations", () => {
    mockFetch({ count: 1, unread_count: 2, items: [CONV_PAYLOAD] });
    return fetchCustomerConversations().then((res) => {
      expect(res.count).toBe(1);
      expect(res.unreadCount).toBe(2);
      expect(res.items[0].storeSlug).toBe("artisan-goods");
    });
  });

  it("fetches seller conversations", () => {
    mockFetch({ count: 1, unread_count: 2, items: [CONV_PAYLOAD] });
    return fetchSellerConversations().then((res) => {
      expect(res.count).toBe(1);
      expect(res.items.length).toBe(1);
    });
  });

  it("starts a conversation", () => {
    mockFetch(CONV_PAYLOAD);
    return startConversation({ storeId: 1, message: "Hi" }).then((res) => {
      expect(res.id).toBe(10);
    });
  });

  it("fetches a single conversation thread", () => {
    mockFetch(CONV_PAYLOAD);
    return fetchConversation(10).then((conv) => {
      expect(conv.id).toBe(10);
      expect(conv.subject).toBe("Question regarding order");
      expect(conv.messages.length).toBe(2);
    });
  });

  it("maps a standalone message", () => {
    const mapped = mapMessage(CONV_PAYLOAD.messages[1]);
    expect(mapped.conversationId).toBe(10);
    expect(mapped.isMe).toBe(true);
    expect(mapped.attachmentUrl).toBe("");
  });


  it("sends a message in conversation", () => {
    mockFetch(CONV_PAYLOAD.messages[1]);
    return sendMessage(10, { body: "Can you ship tomorrow?" }).then((res) => {
      expect(res.body).toBe("Can you ship tomorrow?");
    });
  });

  it("marks conversation as read", () => {
    mockFetch({ success: true });
    return markConversationRead(10).then((res) => {
      expect(res.success).toBe(true);
    });
  });

  it("reports a conversation", () => {
    mockFetch({ success: true, status: "reported" });
    return reportConversation(10, { reason: "Spam" }).then((res) => {
      expect(res.status).toBe("reported");
    });
  });

  it("fetches unread messages count", () => {
    mockFetch({ unread_count: 4 });
    return fetchUnreadMessagesCount().then((count) => {
      expect(count).toBe(4);
    });
  });
});

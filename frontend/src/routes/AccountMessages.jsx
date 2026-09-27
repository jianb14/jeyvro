/**
 * Buyer messages route (Phase 15 — ROADMAP §15.1, §12.6).
 *
 * `/account/messages` — the buyer's side of the messenger, reached from the
 * navbar profile menu and from notification action URLs. Threads are opened
 * with stores from product/order pages, so the page itself only lists,
 * reads, replies, and reports.
 */
import { Navbar } from "../components/layout/Navbar";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { ConversationInbox } from "../components/messaging/ConversationInbox";
import { fetchCustomerConversations } from "../data/messaging";

const loadConversations = () => fetchCustomerConversations();

const getCounterpart = (conv) => conv.storeName || "Store";

export function AccountMessages() {
  return (
    <div className="min-h-screen bg-sand-50 dark:bg-night-950">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <Breadcrumb
          items={[
            { label: "Home", to: "/" },
            { label: "Account", to: "/account" },
            { label: "Messages" },
          ]}
        />
        <div className="mt-6">
          <ConversationInbox
            title="Messages"
            subtitle="Conversations with Jeyvro stores about their products and your orders."
            emptyTitle="No conversations yet"
            emptyDescription="Open a store page or an order and choose “Message store” to start a conversation."
            loadConversations={loadConversations}
            getCounterpart={getCounterpart}
            counterpartRole="Store"
            reportHeading="Report this conversation"
          />
        </div>
      </main>
    </div>
  );
}

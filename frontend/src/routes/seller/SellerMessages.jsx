/**
 * Seller messages route (Phase 15 — ROADMAP §15.1, §12.6).
 *
 * Thin wrapper around the shared inbox: the seller's loader and the
 * "buyer" counterpart copy are the only seller-specific parts.
 */
import { ConversationInbox } from "../../components/messaging/ConversationInbox";
import { fetchSellerConversations } from "../../data/messaging";

const loadConversations = () => fetchSellerConversations();

const getCounterpart = (conv) =>
  conv.customer?.first_name || conv.customer?.email || "Buyer";

export function SellerMessages() {
  return (
    <ConversationInbox
      title="Customer messages"
      subtitle="Product questions and order follow-ups from your buyers (§12.6)."
      emptyTitle="No customer messages"
      emptyDescription="When buyers ask about your products or orders, their messages land here."
      loadConversations={loadConversations}
      getCounterpart={getCounterpart}
      counterpartRole="Buyer"
      reportHeading="Report this customer"
    />
  );
}

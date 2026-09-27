/**
 * "Message store" / "Contact support" affordance (Phase 15 — ROADMAP §15.1,
 * §11.3).
 *
 * One button + modal shared by the product and order surfaces. The buyer
 * writes the opening message; the backend reuses an open thread for the same
 * (customer, store, order, product) and answers with it, so the buyer lands
 * straight in the conversation. Guests are sent to sign in first — messaging
 * is account-scoped on the server.
 */
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { startConversation } from "../../data/messaging";
import { useAuth } from "../../features/auth/AuthContext";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { MessageSquareIcon } from "../ui/Icons";
import { useToast } from "../ui/ToastProvider";

export function MessageStoreButton({
  storeId = null,
  orderId = null,
  productId = null,
  type = "seller",
  label,
  heading,
  description,
  placeholder = "Hi! I have a question about…",
  variant = "outline",
  size = "sm",
  className,
}) {
  const { user } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const isSupport = type === "support";
  const title = heading || (isSupport ? "Contact support" : "Message the store");

  const handleOpen = () => {
    if (!user) {
      push({
        tone: "info",
        title: "Sign in to send a message",
        description: "Conversations live in your account inbox.",
      });
      navigate("/login", { state: { from: location.pathname } });
      return;
    }
    setError(null);
    setOpen(true);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const body = message.trim();
    if (!body || sending) return;
    setSending(true);
    setError(null);
    try {
      const conversation = await startConversation({
        storeId,
        orderId,
        productId,
        type,
        message: body,
      });
      setOpen(false);
      setMessage("");
      push({
        tone: "success",
        title: "Message sent",
        description: "Continue the conversation in your inbox.",
      });
      navigate(`/account/messages?id=${conversation.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <Button variant={variant} size={size} className={className} onClick={handleOpen}>
        <MessageSquareIcon size={size === "sm" ? 14 : 16} />
        {label || title}
      </Button>

      {open && (
        <Modal
          open={open}
          onClose={() => setOpen(false)}
          title={title}
          description={description}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <Alert tone="danger">{error}</Alert>}
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              rows={4}
              autoFocus
              placeholder={placeholder}
              className="w-full rounded-xl border border-sand-300 bg-white p-3 text-sm text-sand-900 placeholder:text-sand-400 focus:border-moss-500 focus:outline-none dark:border-night-700 dark:bg-night-800 dark:text-sand-100"
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" loading={sending} disabled={!message.trim()}>
                Send message
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

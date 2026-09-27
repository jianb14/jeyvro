/**
 * Shared conversation inbox (Phase 15 — ROADMAP §15.1, §12.6).
 *
 * Two-pane messenger used by the buyer (`/account/messages`) and seller
 * (`/seller/messages`) routes. Both audiences share the same UI: only the
 * loader, the counterpart display, and the copy differ — so the behaviour
 * (selection via `?id=`, read-marking on open, reply, report) lives here.
 *
 * Opening a thread marks it read server-side (ConversationDetailView), so
 * the list badge is cleared locally instead of issuing a second request.
 */
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { fetchConversation, reportConversation, sendMessage } from "../../data/messaging";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { EmptyState } from "../ui/EmptyState";
import { Modal } from "../ui/Modal";
import { Spinner } from "../ui/Spinner";
import {
  AlertTriangleIcon,
  MessageSquareIcon,
  PackageIcon,
  SendIcon,
  TagIcon,
} from "../ui/Icons";
import { cx } from "../../lib/cx";

const REPORT_REASONS = [
  "Spam or advertising",
  "Harassment or abuse",
  "Suspicious or fraud attempt",
  "Other",
];

export function ConversationInbox({
  title,
  subtitle,
  emptyTitle,
  emptyDescription,
  loadConversations,
  getCounterpart,
  counterpartRole = "Buyer",
  reportHeading = "Report this conversation",
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeId = searchParams.get("id");

  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  // The open thread is keyed by conversation id: `convDetail.id` records which
  // request produced `data`, so a stale thread can never render under a freshly
  // selected id — and clearing the pane needs no setState inside an effect.
  const [convDetail, setConvDetail] = useState({ id: null, data: null });
  const [failedThreadId, setFailedThreadId] = useState(null);
  const [messageInput, setMessageInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState(REPORT_REASONS[0]);
  const [reportDetails, setReportDetails] = useState("");
  const [reporting, setReporting] = useState(false);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    loadConversations()
      .then((res) => {
        if (cancelled) return;
        setConversations(res.items);
        if (res.items.length > 0 && !searchParams.get("id")) {
          setSearchParams({ id: String(res.items[0].id) }, { replace: true });
        }
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadConversations]);

  // Derived, never stored: the open thread only renders when the loaded detail
  // matches the id in the URL, and the spinner shows until that match exists.
  const activeConv =
    activeId && convDetail.id === String(activeId) ? convDetail.data : null;
  const threadLoading =
    Boolean(activeId) && !activeConv && failedThreadId !== activeId;

  useEffect(() => {
    if (!activeId) return undefined;
    let cancelled = false;
    fetchConversation(activeId)
      .then((conv) => {
        if (cancelled) return;
        setConvDetail({ id: String(activeId), data: conv });
        setFailedThreadId(null);
        setConversations((prev) =>
          prev.map((item) => (item.id === conv.id ? { ...item, unreadCount: 0 } : item))
        );
      })
      .catch((err) => {
        if (cancelled) return;
        setConvDetail({ id: null, data: null });
        setFailedThreadId(activeId);
        setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [activeId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConv?.messages]);

  const handleSend = async (event) => {
    event.preventDefault();
    const body = messageInput.trim();
    if (!body || !activeConv || sending) return;
    setSending(true);
    try {
      const newMessage = await sendMessage(activeConv.id, { body });
      setConvDetail((prev) => ({
        ...prev,
        data: { ...prev.data, messages: [...(prev.data.messages ?? []), newMessage] },
      }));
      setMessageInput("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  const handleReport = async () => {
    if (!activeConv) return;
    setReporting(true);
    try {
      await reportConversation(activeConv.id, {
        reason: reportReason,
        details: reportDetails,
      });
      setConvDetail((prev) => ({ ...prev, data: { ...prev.data, status: "reported" } }));
      setReportOpen(false);
      setReportDetails("");
    } catch (err) {
      setError(err.message);
    } finally {
      setReporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-sand-400">
        <Spinner size={28} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-sand-900 dark:text-sand-100">
          {title}
        </h1>
        {subtitle && <p className="mt-1 text-sm text-sand-600 dark:text-sand-400">{subtitle}</p>}
      </div>

      {error && (
        <Alert tone="danger" title="Something went wrong" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {conversations.length === 0 ? (
        <EmptyState icon={MessageSquareIcon} title={emptyTitle} description={emptyDescription} />
      ) : (
        <div className="grid min-h-[520px] grid-cols-1 overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-soft md:grid-cols-12 dark:border-night-800 dark:bg-night-900">
          <div className="border-b border-sand-200 md:col-span-5 md:border-b-0 md:border-r dark:border-night-800">
            <div className="max-h-[600px] divide-y divide-sand-100 overflow-y-auto dark:divide-night-800">
              {conversations.map((conv) => {
                const isSelected = String(conv.id) === String(activeId);
                const counterpart = getCounterpart(conv);
                return (
                  <button
                    key={conv.id}
                    type="button"
                    onClick={() => setSearchParams({ id: String(conv.id) })}
                    className={cx(
                      "flex w-full flex-col gap-1.5 p-4 text-left transition-colors",
                      isSelected
                        ? "bg-sand-100/70 dark:bg-night-800"
                        : "hover:bg-sand-50 dark:hover:bg-night-800/40"
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-xs font-semibold text-sand-900 dark:text-sand-100">
                        {counterpart}
                      </span>
                      {conv.unreadCount > 0 && (
                        <span className="shrink-0 rounded-full bg-moss-600 px-2 py-0.5 text-[10px] font-semibold text-white dark:bg-moss-500">
                          {conv.unreadCount} new
                        </span>
                      )}
                    </div>
                    <p className="truncate text-xs font-medium text-sand-800 dark:text-sand-200">
                      {conv.subject}
                    </p>
                    {conv.lastMessage?.body && (
                      <p className="line-clamp-1 text-xs text-sand-500 dark:text-sand-400">
                        {conv.lastMessage.body}
                      </p>
                    )}
                    <div className="mt-0.5 flex items-center gap-2">
                      {conv.orderNumber && (
                        <span className="inline-flex items-center gap-1 rounded bg-sand-200/60 px-1.5 py-0.5 text-[10px] text-sand-700 dark:bg-night-700 dark:text-sand-300">
                          <PackageIcon size={10} />
                          {conv.orderNumber}
                        </span>
                      )}
                      {conv.productTitle && (
                        <span className="inline-flex max-w-[140px] items-center gap-1 truncate rounded bg-sand-200/60 px-1.5 py-0.5 text-[10px] text-sand-700 dark:bg-night-700 dark:text-sand-300">
                          <TagIcon size={10} />
                          {conv.productTitle}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col md:col-span-7">
            {threadLoading ? (
              <div className="flex flex-1 items-center justify-center py-16 text-sand-400">
                <Spinner size={24} />
              </div>
            ) : activeConv ? (
              <>
                <div className="flex items-center justify-between gap-3 border-b border-sand-200 px-5 py-4 dark:border-night-800">
                  <div className="min-w-0">
                    <h2 className="truncate font-display text-sm font-semibold text-sand-900 dark:text-sand-100">
                      {activeConv.subject}
                    </h2>
                    <p className="truncate text-xs text-sand-500 dark:text-sand-400">
                      With {getCounterpart(activeConv)}
                    </p>
                  </div>
                  {activeConv.status === "reported" ? (
                    <span className="shrink-0 rounded-full bg-warning-100 px-2 py-0.5 text-[10px] font-medium text-warning-800 dark:bg-warning-950/60 dark:text-warning-200">
                      Reported
                    </span>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0 text-sand-500"
                      onClick={() => setReportOpen(true)}
                    >
                      <AlertTriangleIcon size={14} />
                      Report
                    </Button>
                  )}
                </div>

                <div className="flex-1 space-y-4 overflow-y-auto p-5">
                  {(activeConv.messages ?? []).map((msg) => (
                    <div
                      key={msg.id}
                      className={cx("flex flex-col", msg.isMe ? "items-end" : "items-start")}
                    >
                      <div
                        className={cx(
                          "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm",
                          msg.isMe
                            ? "rounded-br-sm bg-moss-700 text-white dark:bg-moss-600"
                            : "rounded-bl-sm bg-sand-100 text-sand-900 dark:bg-night-800 dark:text-sand-100"
                        )}
                      >
                        {msg.body}
                      </div>
                      <span className="mt-1 text-[10px] text-sand-400 dark:text-sand-500">
                        {msg.isMe ? "You" : counterpartRole} ·{" "}
                        {new Date(msg.createdAt).toLocaleString("en-PH", {
                          dateStyle: "short",
                          timeStyle: "short",
                        })}
                      </span>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                <form
                  onSubmit={handleSend}
                  className="flex items-center gap-2 border-t border-sand-200 p-4 dark:border-night-800"
                >
                  <input
                    type="text"
                    value={messageInput}
                    onChange={(event) => setMessageInput(event.target.value)}
                    placeholder="Write a message…"
                    className="h-10 flex-1 rounded-xl border border-sand-300 bg-white px-3.5 text-sm text-sand-900 placeholder:text-sand-400 focus:border-moss-500 focus:outline-none dark:border-night-700 dark:bg-night-800 dark:text-sand-100"
                  />
                  <Button type="submit" size="sm" loading={sending} disabled={!messageInput.trim()}>
                    <SendIcon size={14} />
                    Send
                  </Button>
                </form>
              </>
            ) : (
              <div className="flex flex-1 items-center justify-center py-16 text-sm text-sand-400">
                Select a conversation to open it.
              </div>
            )}
          </div>
        </div>
      )}

      {reportOpen && activeConv && (
        <Modal
          open={reportOpen}
          onClose={() => setReportOpen(false)}
          title={reportHeading}
          description="Flag the thread for staff moderation review (§15.1)."
        >
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="report-reason"
                className="text-xs font-medium text-sand-800 dark:text-sand-200"
              >
                Reason
              </label>
              <select
                id="report-reason"
                value={reportReason}
                onChange={(event) => setReportReason(event.target.value)}
                className="h-10 w-full rounded-xl border border-sand-300 bg-white px-3 text-sm text-sand-900 focus:border-moss-500 focus:outline-none dark:border-night-700 dark:bg-night-800 dark:text-sand-100"
              >
                {REPORT_REASONS.map((reason) => (
                  <option key={reason} value={reason}>
                    {reason}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="report-details"
                className="text-xs font-medium text-sand-800 dark:text-sand-200"
              >
                Details (optional)
              </label>
              <textarea
                id="report-details"
                value={reportDetails}
                onChange={(event) => setReportDetails(event.target.value)}
                rows={3}
                placeholder="Describe what happened…"
                className="w-full rounded-xl border border-sand-300 bg-white p-3 text-sm text-sand-900 placeholder:text-sand-400 focus:border-moss-500 focus:outline-none dark:border-night-700 dark:bg-night-800 dark:text-sand-100"
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setReportOpen(false)}>
                Cancel
              </Button>
              <Button variant="destructive" size="sm" loading={reporting} onClick={handleReport}>
                Submit report
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

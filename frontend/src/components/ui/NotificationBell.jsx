/**
 * Notification bell (Phase 15 — ROADMAP §15.2).
 *
 * Navbar popover: unread badge polled every 30s, list of the latest 50
 * notifications, per-item and mark-all read, and navigation to the
 * notification's action URL when one is set. Rendered only for
 * authenticated users (returns null otherwise).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../features/auth/AuthContext";
import {
  fetchNotifications,
  fetchUnreadNotificationCount,
  markAllNotificationsAsRead,
  markNotificationAsRead,
} from "../../data/notifications";
import { BellIcon, CheckIcon } from "./Icons";
import { Spinner } from "./Spinner";
import { cx } from "../../lib/cx";

const POLL_INTERVAL_MS = 30000;

export function NotificationBell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const rootRef = useRef(null);

  const loadUnreadCount = useCallback(() => {
    if (!user) return;
    fetchUnreadNotificationCount()
      .then(setUnreadCount)
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!user) return undefined;
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [user, loadUnreadCount]);

  // Loading lives in an event handler, not an effect: opening the panel is a
  // user action, so the fetch (and the spinner) start there.
  const openPanel = useCallback(() => {
    setOpen(true);
    setLoading(true);
    fetchNotifications()
      .then((res) => {
        setNotifications(res.items);
        setUnreadCount(res.unreadCount);
      })
      .catch(() => setNotifications([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onDocumentMouseDown = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false);
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocumentMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onDocumentMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!user) return null;

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsAsRead();
      setUnreadCount(0);
      setNotifications((prev) => prev.map((item) => ({ ...item, isRead: true })));
    } catch {
      loadUnreadCount();
    }
  };

  const handleItemClick = async (notif) => {
    if (!notif.isRead) {
      try {
        await markNotificationAsRead(notif.id);
        setUnreadCount((count) => Math.max(0, count - 1));
        setNotifications((prev) =>
          prev.map((item) => (item.id === notif.id ? { ...item, isRead: true } : item))
        );
      } catch {
        // Keep the popover usable — the badge re-syncs on the next poll.
      }
    }
    if (notif.actionUrl) {
      setOpen(false);
      navigate(notif.actionUrl);
    }
  };

  return (
    <div ref={rootRef} className="relative inline-block">
      <button
        type="button"
        onClick={() => (open ? setOpen(false) : openPanel())}
        aria-label={`Notifications, ${unreadCount} unread`}
        aria-expanded={open}
        className="relative inline-flex size-10 items-center justify-center rounded-lg text-sand-600 transition-colors hover:text-moss-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-sand-300 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400"
      >
        <BellIcon size={20} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-moss-600 px-1 text-[10px] font-semibold text-white dark:bg-moss-500">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="animate-scale-in absolute top-full right-0 z-40 mt-2 w-80 overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-dropdown sm:w-96 dark:border-night-700 dark:bg-night-900"
        >
          <div className="flex items-center justify-between border-b border-sand-100 px-4 py-3 dark:border-night-800">
            <h3 className="font-display text-sm font-semibold text-sand-900 dark:text-sand-100">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="inline-flex items-center gap-1 text-xs font-medium text-moss-700 transition-colors hover:text-moss-800 dark:text-moss-400 dark:hover:text-moss-300"
              >
                <CheckIcon size={14} />
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 divide-y divide-sand-100 overflow-y-auto dark:divide-night-800">
            {loading ? (
              <div className="flex justify-center py-8 text-sand-400">
                <Spinner size={20} />
              </div>
            ) : notifications.length === 0 ? (
              <p className="py-8 text-center text-sm text-sand-500 dark:text-sand-400">
                No notifications yet.
              </p>
            ) : (
              notifications.map((notif) => (
                <button
                  key={notif.id}
                  type="button"
                  onClick={() => handleItemClick(notif)}
                  className={cx(
                    "flex w-full flex-col gap-1 px-4 py-3 text-left transition-colors hover:bg-sand-50 dark:hover:bg-night-800/60",
                    !notif.isRead && "bg-moss-50/60 dark:bg-moss-950/20"
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-semibold text-sand-900 dark:text-sand-100">
                      {notif.title}
                    </span>
                    {!notif.isRead && (
                      <span className="size-2 shrink-0 rounded-full bg-moss-600 dark:bg-moss-400" />
                    )}
                  </span>
                  <span className="line-clamp-2 text-xs text-sand-600 dark:text-sand-300">
                    {notif.message}
                  </span>
                  <span className="text-[10px] text-sand-400 dark:text-sand-500">
                    {new Date(notif.createdAt).toLocaleString("en-PH", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

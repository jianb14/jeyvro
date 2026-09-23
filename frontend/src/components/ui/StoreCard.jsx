import { cx } from "../../lib/cx";
import { Avatar } from "./Avatar";
import { Rating } from "./Rating";
import { Button } from "./Button";
import { MapPinIcon } from "./Icons";

export function StoreCard({ store, onFollow, className }) {
  return (
    <div
      className={cx(
        "flex items-center gap-4 rounded-2xl border border-sand-200 bg-white p-5 shadow-soft dark:border-night-800 dark:bg-night-900",
        className
      )}
    >
      <Avatar name={store.name} size="lg" src={store.logo} />
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 font-medium text-sand-900 dark:text-sand-100">
          <span className="truncate">{store.name}</span>
          {store.verified && (
            <span title="Verified seller" className="shrink-0 text-moss-600 dark:text-moss-400">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">
                <path d="M12 2 9.8 4.6l-3.4-.5-.6 3.4L3 9.6l1.5 3.1L3 15.8l2.8 2.1.6 3.4 3.4-.5L12 23.4l2.2-2.6 3.4.5.6-3.4 2.8-2.1-1.5-3.1L21 9.6l-2.8-2.1-.6-3.4-3.4.5z" />
                <path d="m10.7 14.3-2-2-1.1 1.1 3.1 3.1 5.7-5.7-1.1-1.1z" fill="#ffffff" />
              </svg>
            </span>
          )}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-sand-500 dark:text-sand-400">
          <Rating value={store.rating} readonly size="sm" />
          <span className="tabular-nums">{store.products} products</span>
          <span className="flex items-center gap-1">
            <MapPinIcon size={12} /> {store.location}
          </span>
        </div>
      </div>
      <Button variant={store.following ? "secondary" : "primary"} size="sm" onClick={onFollow}>
        {store.following ? "Following" : "+ Follow"}
      </Button>
    </div>
  );
}

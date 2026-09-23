import { cx } from "../../lib/cx";
import { Avatar } from "./Avatar";
import { Rating } from "./Rating";
import { Badge } from "./Badge";
import { ShieldCheckIcon, HeartIcon } from "./Icons";

export function ReviewCard({ review, className }) {
  return (
    <article
      className={cx(
        "flex flex-col gap-3 rounded-2xl border border-sand-200 bg-white p-5 dark:border-night-800 dark:bg-night-900",
        className
      )}
    >
      <div className="flex items-center gap-3">
        <Avatar name={review.author} size="sm" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-sand-900 dark:text-sand-100">{review.author}</p>
          <div className="flex items-center gap-2">
            <Rating value={review.rating} readonly size="sm" />
            {review.verifiedPurchase && (
              <Badge tone="success" variant="soft" size="sm" icon={ShieldCheckIcon}>
                Verified
              </Badge>
            )}
          </div>
        </div>
        <span className="shrink-0 text-xs text-sand-400">{review.date}</span>
      </div>

      <p className="text-sm leading-relaxed text-sand-600 dark:text-sand-300">{review.text}</p>

      {review.photos?.length > 0 && (
        <div className="flex gap-2">
          {review.photos.map((seed, i) => (
            <div
              key={i}
              className="size-14 overflow-hidden rounded-lg border border-sand-200 dark:border-night-700"
              style={{ backgroundColor: ["#e4ecdc", "#f5ebd6", "#e3edf4"][seed % 3] }}
              aria-label="Review photo"
              role="img"
            />
          ))}
        </div>
      )}

      <button
        type="button"
        className="inline-flex w-fit items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium text-sand-500 transition-colors hover:bg-sand-100 hover:text-sand-800 dark:hover:bg-night-800 dark:hover:text-sand-200"
      >
        <HeartIcon size={13} /> Helpful ({review.helpful})
      </button>
    </article>
  );
}

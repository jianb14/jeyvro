import { cx } from "../../lib/cx";

const SIZES = {
  xs: "size-6 text-[10px]",
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-12 text-base",
  xl: "size-16 text-lg",
};

const BG_COLORS = ["bg-moss-600", "bg-warning-500", "bg-info-500", "bg-danger-500", "bg-sand-600", "bg-success-600"];

const STATUS_COLORS = {
  online: "bg-success-500",
  away: "bg-warning-400",
  busy: "bg-danger-500",
  offline: "bg-sand-400",
};

function hashName(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return h;
}

function initialsOf(name) {
  return name
    .trim()
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function Avatar({ name = "?", src, size = "md", status, className }) {
  const bg = BG_COLORS[hashName(name) % BG_COLORS.length];
  return (
    <span className={cx("relative inline-flex shrink-0", className)}>
      {src ? (
        <img src={src} alt={name} className={cx("rounded-full object-cover", SIZES[size])} />
      ) : (
        <span
          aria-hidden="true"
          className={cx("inline-flex items-center justify-center rounded-full font-medium text-white", SIZES[size], bg)}
        >
          {initialsOf(name)}
        </span>
      )}
      {status && (
        <span
          title={status}
          className={cx(
            "absolute bottom-0 right-0 block size-2.5 rounded-full ring-2 ring-white dark:ring-night-900",
            STATUS_COLORS[status]
          )}
        />
      )}
    </span>
  );
}

export function AvatarGroup({ people = [], max = 4, size = "md", className }) {
  const shown = people.slice(0, max);
  const extra = people.length - shown.length;
  return (
    <div className={cx("flex -space-x-2.5", className)}>
      {shown.map((p) => (
        <span key={p.name} className="rounded-full ring-2 ring-white dark:ring-night-900">
          <Avatar {...p} size={size} />
        </span>
      ))}
      {extra > 0 && (
        <span
          className={cx(
            "inline-flex items-center justify-center rounded-full bg-sand-200 font-medium text-sand-600 ring-2 ring-white dark:bg-night-700 dark:text-sand-300 dark:ring-night-900",
            SIZES[size]
          )}
        >
          +{extra}
        </span>
      )}
    </div>
  );
}

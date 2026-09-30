import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { cx } from "../../lib/cx";
import { useAuth } from "../../features/auth/AuthContext";
import { useWishlist } from "../../features/wishlist/WishlistContext";
import { Price } from "./Price";
import { Rating } from "./Rating";
import { ProductArt } from "./ProductArt";
import { StockIndicator } from "./StockIndicator";
import { useToast } from "./ToastProvider";
import { HeartIcon, HeartSolidIcon, ShoppingCartIcon, StoreIcon, VerifiedBadgeIcon } from "./Icons";

export function ProductCard({ product, onAddToCart, className }) {
  const { user } = useAuth();
  const { isSaved, toggle } = useWishlist();
  const { push } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [favBusy, setFavBusy] = useState(false);
  // Wishlist state is server truth (Phase 7.2) — derived, never mirrored.
  const fav = isSaved(product.id);
  const soldOut = product.stock === 0;

  const handleFav = async () => {
    if (!user) {
      push({
        tone: "info",
        title: "Sign in to save items",
        description: "Your wishlist follows your account.",
      });
      navigate("/login", { state: { from: location.pathname } });
      return;
    }
    if (favBusy) return;
    setFavBusy(true);
    try {
      const saved = await toggle(product.id);
      push({
        tone: "success",
        title: saved ? "Saved to wishlist" : "Removed from wishlist",
        description: product.title,
      });
    } catch (err) {
      push({
        tone: "danger",
        title: "Wishlist update failed",
        description: err.data?.detail || err.message,
      });
    } finally {
      setFavBusy(false);
    }
  };

  return (
    <div
      className={cx(
        "group flex flex-col overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-soft transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lift dark:border-night-800 dark:bg-night-900",
        soldOut && "opacity-75",
        className
      )}
    >
      <div className="relative">
        <Link to={`/product/${product.id}`} aria-label={product.title} className="block">
          {product.image ? (
            <img
              src={product.image}
              alt={product.title}
              loading="lazy"
              className="aspect-[4/3] w-full object-cover"
            />
          ) : (
            <ProductArt seed={product.seed} className="aspect-[4/3] w-full" />
          )}
        </Link>
        {soldOut || product.isNew ? (
          <CornerRibbon
            tone={soldOut ? "neutral" : "moss"}
            label={soldOut ? "SOLD OUT" : "NEW"}
          />
        ) : null}
        <button
          type="button"
          onClick={handleFav}
          disabled={favBusy}
          aria-label={fav ? "Remove from wishlist" : "Add to wishlist"}
          aria-pressed={fav}
          className={cx(
            "absolute right-3 top-3 flex size-9 items-center justify-center rounded-full bg-white/90 shadow-soft backdrop-blur transition-all hover:scale-110 dark:bg-night-800/90",
            fav ? "text-danger-500" : "text-sand-400 hover:text-danger-400"
          )}
        >
          {fav ? <HeartSolidIcon size={18} /> : <HeartIcon size={18} />}
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-4">
        <Link
          to={`/product/${product.id}`}
          className="line-clamp-2 min-h-10 text-sm font-medium leading-snug text-sand-900 transition-colors hover:text-moss-700 dark:text-sand-100 dark:hover:text-moss-300"
        >
          {product.title}
        </Link>
        <Price amount={product.price} originalAmount={product.originalPrice} discount={product.discount} size="md" />
        <div className="flex items-center gap-1.5 text-xs text-sand-500 dark:text-sand-400">
          <Rating value={product.rating} readonly size="sm" />
          <span className="tabular-nums">({product.rating})</span>
          <span aria-hidden="true">·</span>
          <span className="tabular-nums">{product.sold} sold</span>
        </div>
        <StockIndicator count={product.stock} />
        <StoreLine product={product} />
        <AddButton soldOut={soldOut} onClick={() => onAddToCart?.(product)} />
      </div>
    </div>
  );
}

// A corner tape, not a pill — and the geometry is the whole point.
//
// The first attempt parked a short rotated strip a few pixels inside the
// photo (left-2 top-3), which read as a sticker floating on the picture: it
// reached neither edge, so nothing about it said "corner". What sells a
// marketplace ribbon is the opposite — a band that spans the corner and gets
// cut off BY it, so its two ends disappear under the top and left edges.
//
// How this hangs together: the band is a wide element rotated -45° whose
// centre is pinned at (INSET, INSET) via translate -50%, -50%. Rotation runs
// the band along the corner diagonal, so one end leaves through the top edge
// and the other through the left edge. The wrapper's overflow-hidden does the
// cutting, which is why the band can be far longer than the visible run and
// still finish flush — no hard-coded clip path, and it re-cuts itself if the
// grid ever changes the card width.
//
// The inset is not free. The rotated text's corner reaches
// (textWidth / 2 + lineHeight / 2) * 0.707 out from the centre, and the clip
// shaves anything that crosses x=0 or y=0. "SOLD OUT" is the worst case at
// ~61px wide with an ~11px line box, so it needs inset >= ~27px; 30 leaves
// margin. Pull the inset down and the S and the final T get sliced off.
//
// 30 is spelled out in the class string rather than interpolated, and that is
// load-bearing: Tailwind extracts candidates by scanning source text, so a
// `left-[${INSET}px]` template literal produces no `left-[30px]` rule at all
// and the band silently falls back to `left: auto`.
//
// pointer-events-none because the tape sits on top of the product image, and
// that image is the link — a tape you can tap but that goes nowhere is worse
// than no tape at all.
const RIBBON_TONES = {
  moss: "bg-moss-600",
  neutral: "bg-sand-500",
};

function CornerRibbon({ tone = "moss", label }) {
  return (
    <div className="pointer-events-none absolute inset-0 z-10 overflow-hidden">
      <span
        className={cx(
          "absolute flex h-6 w-[140%] items-center justify-center whitespace-nowrap",
          "left-[30px] top-[30px] -translate-x-1/2 -translate-y-1/2 -rotate-45",
          "text-[9px] font-semibold uppercase tracking-[0.12em] text-white",
          RIBBON_TONES[tone]
        )}
      >
        {label}
      </span>
    </div>
  );
}

function StoreLine({ product }) {
  const inner = (
    <>
      <StoreIcon size={13} className="shrink-0" />
      <span className="truncate">{product.store}</span>
      {product.verified && (
        <span title="Verified seller" className="shrink-0 text-moss-600 dark:text-moss-400">
          <VerifiedBadgeIcon size={14} />
        </span>
      )}
    </>
  );
  const className = "flex min-w-0 items-center gap-1.5 text-xs text-sand-500 dark:text-sand-400";
  if (!product.storeSlug) {
    return <div className={className}>{inner}</div>;
  }
  return (
    <Link
      to={`/store/${product.storeSlug}`}
      className={cx(className, "transition-colors hover:text-moss-700 dark:hover:text-moss-300")}
    >
      {inner}
    </Link>
  );
}

function AddButton({ soldOut, onClick }) {
  return (
    <button
      type="button"
      disabled={soldOut}
      onClick={onClick}
      className={cx(
        "mt-2 inline-flex h-9 items-center justify-center gap-2 rounded-lg text-sm font-medium transition-[background-color,border-color,color,transform] active:scale-[0.98]",
        soldOut
          ? "cursor-not-allowed bg-sand-100 text-sand-400 dark:bg-night-800 dark:text-sand-600"
          : "bg-moss-600 text-white hover:bg-moss-700 dark:bg-moss-500 dark:hover:bg-moss-600"
      )}
    >
      <ShoppingCartIcon size={16} />
      {soldOut ? "Sold out" : "Add to cart"}
    </button>
  );
}

export function ProductGrid({ products = [], onAddToCart, columns = 3, className }) {
  const COLS = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-2 lg:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4" };
  return (
    <div className={cx("grid grid-cols-1 gap-5", COLS[columns], className)}>
      {products.map((p) => (
        <ProductCard key={p.id} product={p} onAddToCart={onAddToCart} />
      ))}
    </div>
  );
}

export function ProductGridSkeleton({ count = 6, columns = 3 }) {
  const COLS = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-2 lg:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4" };
  return (
    <div className={cx("grid grid-cols-1 gap-5", COLS[columns])} aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex animate-pulse flex-col gap-3 rounded-2xl border border-sand-200 p-4 dark:border-night-800">
          <div className="aspect-[4/3] w-full rounded-xl bg-sand-200/80 dark:bg-night-800" />
          <div className="h-3 w-3/4 rounded bg-sand-200/80 dark:bg-night-800" />
          <div className="h-3 w-1/2 rounded bg-sand-200/80 dark:bg-night-800" />
        </div>
      ))}
    </div>
  );
}

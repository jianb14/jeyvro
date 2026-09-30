/**
 * HeroBanner (Phase 6.1) — the marketplace's opening statement.
 *
 * A single banner card: copy on the left, imagery on the right, decorative
 * botanicals behind both. It replaces the plain stacked hero that used to sit
 * inline in routes/Home.jsx; it lives in its own file because a layout piece
 * belongs in components/layout/ and because Home.jsx is a data-orchestration
 * route, not a place to grow markup.
 *
 * The copy reads like a person, not a shout: a Title Case heading (it used to
 * render in all caps) and a subtitle that says the same thing the shelves
 * below actually do — no "marketplace API" jargon on a customer-facing card.
 * There is no "starting at ₱…" line even though banners like this usually
 * carry one: Jeyvro has no single headline price, and inventing a number to
 * make the card look fuller is exactly the kind of fake deal the promo cards
 * promise never to run.
 *
 * The photo is the one thing here the project does not own — it is a remote
 * URL chosen by the shop owner and swappable in one place (HERO_PHOTO). Two
 * consequences are handled rather than ignored:
 *   - the photo is `absolute`, so it sits out of flow: the box is reserved by
 *     the column instead of by the image, and `width`/`height` still declare
 *     the CDN's real ratio. Neither the bytes arriving late nor the photo's own
 *     aspect ratio can resize the card or shift the page down (frontend-
 *     performance);
 *   - `onError` swaps in a flat token panel, so a dead network or a moved URL
 *     leaves a branded shape instead of a broken-image icon.
 * In dark mode the image gets a brightness trim — a daylight photo left at
 * full strength is the brightest thing on a night-950 page.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { cx } from "../../lib/cx";
import { Button } from "../ui/Button";
import { ArrowRightIcon, LogoMark } from "../ui/Icons";

// The mint-green backdrop is deliberate — it is the brand's own colour family,
// and unlike a lit studio sweep it does not gradient from corner to corner
// (which is what the first photo here did). A model is what earns the heading:
// "Local Goods, Chosen With Care" lands harder next to someone actually holding
// the goods up than next to an empty still life, and the goods sit beside his
// face so the blob's left edge only ever bites empty backdrop. The image is the
// one thing this component does not own: a remote URL swappable in one place,
// with an onError fallback below in case it ever stops answering.
//
// The source is portrait on purpose. Asking the CDN for a `fit=crop` would bake
// one landscape band into the bytes, so instead the full frame is served and the
// per-breakpoint `object-[50%_…]` anchor on the <img> picks the band in CSS —
// where it can still be re-tuned when the card's box changes.
const HERO_PHOTO = {
  src: "https://images.pexels.com/photos/9324377/pexels-photo-9324377.jpeg?auto=compress&cs=tinysrgb&w=1200",
  width: 1200,
  height: 1800,
  alt: "Model smiling while holding up a bar of soap against a solid mint-green backdrop",
};

// The container blob is a real curve, not a border-radius approximation:
// `clipPathUnits="objectBoundingBox"` means the same path scales with the
// column instead of being pinned to one width. It is static geometry, so the
// id is a plain literal — a `useId()` value would contain characters React 19
// does not guarantee are CSS-safe inside the `url(#…)` we hand to Tailwind.
function BlobClip() {
  return (
    <svg aria-hidden="true" className="absolute size-0">
      <defs>
        <clipPath id="jeyvro-hero-blob" clipPathUnits="objectBoundingBox">
          <path d="M0.26 0C0.06 0.2 0 0.4 0 0.55 0 0.72 0.08 0.88 0.26 1L1 1 1 0Z" />
        </clipPath>
      </defs>
    </svg>
  );
}

// Decorative branch. Deliberately aria-hidden and text-moss — it is a shape,
// not a message, so it must never appear in the accessibility tree and must
// never be the only thing carrying a meaning.
function HeroSprig({ className }) {
  return (
    <svg viewBox="0 0 96 96" fill="none" className={className} aria-hidden="true">
      <path
        d="M10 86C26 68 44 48 86 10"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <ellipse cx="32" cy="64" rx="12" ry="5" transform="rotate(-45 32 64)" fill="currentColor" />
      <ellipse cx="46" cy="50" rx="12" ry="5" transform="rotate(-45 46 50)" fill="currentColor" />
      <ellipse cx="60" cy="36" rx="12" ry="5" transform="rotate(-45 60 36)" fill="currentColor" />
      <ellipse cx="74" cy="22" rx="12" ry="5" transform="rotate(-45 74 22)" fill="currentColor" />
    </svg>
  );
}

export function HeroBanner({ className }) {
  const [photoFailed, setPhotoFailed] = useState(false);

  return (
    <section
      className={cx(
        "relative isolate animate-slide-up overflow-hidden rounded-2xl border border-sand-200 bg-sand-50 shadow-soft dark:border-night-800 dark:bg-night-900",
        className
      )}
    >
      <BlobClip />

      {/* Soft background shapes. Sand and moss only — the semantic ramps are
          reserved for status, so the peach blobs in the reference become the
          neutral they map to in this palette. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <span className="absolute -left-24 -top-24 size-56 rounded-full bg-moss-100/70 dark:bg-moss-900/40" />
        <span className="absolute -bottom-24 left-1/4 size-64 rounded-full bg-sand-200/50 dark:bg-night-800/70" />
      </div>

      <HeroSprig className="pointer-events-none absolute right-3 top-3 hidden size-20 text-moss-300 sm:block dark:text-moss-800" />

      {/* The card stays deliberately short — the first product shelf must still
          be reachable without a scroll marathon — but it is no longer stunted:
          at lg the copy column sets a 420px floor, the shortest stage that lets
          a portrait photo hold the model's face and the goods together instead
          of cropping them to a sliver. It is a floor, not a fixed height, so a
          wrapped heading or a longer translation still grows the card rather
          than overflowing it. */}
      <div className="relative grid lg:grid-cols-[1.05fr_1fr] lg:min-h-[420px]">
        <div className="flex flex-col justify-center p-6 sm:p-8 lg:p-10">
          <h1 className="max-w-xl font-display text-2xl font-bold leading-tight tracking-tight text-sand-900 sm:text-3xl lg:text-4xl dark:text-sand-100">
            Local Goods, {" "}
            <span className="text-moss-600 dark:text-moss-400">Chosen With Care</span>
          </h1>

          <p className="mt-3 max-w-md text-sm leading-relaxed text-sand-500 sm:text-base dark:text-sand-400">
            Independent sellers, honest prices, and stock you can trust — every
            find below is picked by hand, never paid placement.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/products">
              <Button size="lg" trailingIcon={ArrowRightIcon}>
                Browse products
              </Button>
            </Link>
            <Link to="/sell">
              <Button size="lg" variant="outline">
                Sell on Jeyvro
              </Button>
            </Link>
          </div>
        </div>

        {/* The image column carries no height of its own at lg: the photo is
            `absolute`, so it sits out of flow and cannot drag the row taller
            than the copy column wants. That is what keeps the first shelf
            reachable without a scroll — a square photo left in flow is what
            used to pin the row to its own aspect ratio, no matter how little
            padding the card had. Below lg it is a short strip.

            The photo is portrait while the column is landscape, so `object-cover`
            only ever reveals a horizontal band of it and the anchor decides
            which band. The model's head and the goods span roughly 11%–47% of
            the source, so the `object-center` default would slice straight
            through his face; the anchor pins the band over that range instead —
            higher on the narrow small-screen strips (which see less of the
            source) and down at 11% on the tall lg stage (which sees nearly half). */}
        <div className="relative h-44 w-full overflow-hidden sm:h-56 lg:h-auto lg:[clip-path:url(#jeyvro-hero-blob)]">
          {photoFailed ? (
            <div className="flex size-full items-center justify-center bg-moss-100 dark:bg-moss-900">
              <LogoMark size={64} />
            </div>
          ) : (
            <img
              src={HERO_PHOTO.src}
              alt={HERO_PHOTO.alt}
              width={HERO_PHOTO.width}
              height={HERO_PHOTO.height}
              loading="eager"
              fetchPriority="high"
              decoding="async"
              onError={() => setPhotoFailed(true)}
              className="absolute inset-0 size-full object-cover object-[50%_22%] lg:object-[50%_11%] dark:brightness-90"
            />
          )}
        </div>
      </div>
    </section>
  );
}

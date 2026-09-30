/**
 * PromoStrip — the storefront's campaign banners.
 *
 * The reference design this replaces had hardcoded artwork per campaign. That
 * is not an option here: a campaign is a database fact, and a slug→photo map
 * in the frontend would break for every campaign staff create afterwards
 * (catalog rule 7). So each banner is a branded panel built from the campaign's
 * own server-resolved fields — its name, its description, and the real count
 * of rules inside it. No invented discount percentage, no "Up to 30% off" the
 * server never promised.
 *
 * Placement is deliberate: directly under the category grid, so the page reads
 * hero → browse by category → current deals → featured products. A shopper who
 * just showed interest in Fashion meets the Fashion deal one scroll later.
 *
 * The strip renders nothing at all when there is no live campaign. An empty
 * promo band is worse than no band — it advertises a marketplace that has
 * nothing on offer.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchPublicCampaigns } from "../../data/promotions";
import { Skeleton } from "../ui/Skeleton";
import { ArrowRightIcon, LogoMark } from "../ui/Icons";

// The band shows the two strongest live campaigns; past that it competes with
// the product shelves it is meant to send people down to.
const MAX_BANNERS = 2;

function isLive(campaign) {
  if (!campaign.startsAt) return true;
  if (new Date(campaign.startsAt) > new Date()) return false;
  if (campaign.endsAt && new Date(campaign.endsAt) < new Date()) return false;
  return true;
}

function PromoBanner({ campaign }) {
  const { name, description, promotionCount, storeName } = campaign;
  const count = promotionCount ?? 0;
  // A seller campaign is scoped to one store, so it says whose sale it is;
  // a platform campaign is the marketplace's own and needs no byline.
  const eyebrow = storeName
    ? `${storeName} sale`
    : count > 0
      ? `${count} active offer${count === 1 ? "" : "s"}`
      : "Marketplace offer";

  return (
    <div className="relative flex min-h-[132px] flex-col justify-center overflow-hidden rounded-2xl border border-moss-200 bg-moss-100 p-5 sm:min-h-[152px] sm:p-6 dark:border-moss-900 dark:bg-moss-950">
      {/* The panel is decoration behind the copy, so it is aria-hidden and can
          never be mistaken for an image the band failed to load. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-6 -top-8 opacity-20 dark:opacity-25"
      >
        <LogoMark size={140} />
      </div>

      <div className="relative">
        <p className="text-xs font-semibold uppercase tracking-wide text-moss-700 dark:text-moss-300">
          {eyebrow}
        </p>
        <h3 className="mt-1.5 font-display text-lg font-bold tracking-tight text-sand-900 sm:text-xl dark:text-sand-100">
          {name}
        </h3>
        {description ? (
          <p className="mt-1.5 line-clamp-2 max-w-sm text-sm text-sand-600 dark:text-sand-300">
            {description}
          </p>
        ) : null}
        <Link
          to="/products"
          className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-moss-700 transition-colors hover:text-moss-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-moss-300 dark:hover:text-moss-200 dark:focus-visible:outline-moss-400"
        >
          Shop now
          <ArrowRightIcon size={16} />
        </Link>
      </div>
    </div>
  );
}

export function PromoStrip() {
  const [state, setState] = useState({ campaigns: null, error: null });

  useEffect(() => {
    let alive = true;
    fetchPublicCampaigns()
      .then((items) => {
        // The server filters is_active but not the date window, so the client
        // drops anything already finished rather than showing a dead campaign.
        if (alive) {
          setState({ campaigns: items.filter(isLive).slice(0, MAX_BANNERS), error: null });
        }
      })
      .catch(() => {
        // A failed promo fetch must never break the homepage — the band simply
        // does not appear, and everything below it still renders.
        if (alive) setState({ campaigns: [], error: true });
      });
    return () => {
      alive = false;
    };
  }, []);

  if (state.campaigns === null) {
    return (
      <section className="flex flex-col gap-4" aria-hidden="true">
        <Skeleton className="h-7 w-56" />
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, index) => (
            <Skeleton key={index} className="h-[132px] rounded-2xl sm:h-[152px]" />
          ))}
        </div>
      </section>
    );
  }

  if (state.campaigns.length === 0) return null;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-4">
        <h2 className="font-display text-xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">
          On sale now
        </h2>
        <Link
          to="/products"
          className="shrink-0 text-sm font-medium text-moss-700 transition-colors hover:text-moss-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:text-moss-300 dark:hover:text-moss-200 dark:focus-visible:outline-moss-400"
        >
          View all
        </Link>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {state.campaigns.map((campaign) => (
          <PromoBanner key={campaign.id} campaign={campaign} />
        ))}
      </div>
    </section>
  );
}
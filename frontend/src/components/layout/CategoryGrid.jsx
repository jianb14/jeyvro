/**
 * CategoryGrid — the storefront's "Shop by category" cards.
 *
 * Every category is a database fact the staff manage at /staff/taxonomy; this
 * component never holds a list of its own (catalog rule 7). It renders
 * whatever `useCategories` hands it, so a category a staff member creates an
 * hour ago appears here on its own, with no code change.
 *
 * The photo on each card is `cover_image`, resolved server-side from the
 * category's newest published product (Category has no image field of its own).
 * When a category has nothing sellable yet the card draws a branded moss panel
 * with the logo mark instead of a broken-image icon — the same fallback
 * HeroBanner uses for a dead hero photo, so the two read as one system.
 *
 * `productCount` is the server's own count of buyable products. It is shown
 * honestly: a category with 0 says "0 items" rather than hiding the card,
 * because a storefront that quietly drops empty departments looks broken
 * rather than curated.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Skeleton } from "../ui/Skeleton";
import { LogoMark } from "../ui/Icons";

function CategoryCard({ category }) {
  const [imageFailed, setImageFailed] = useState(false);
  const { name, slug, coverImage, productCount } = category;
  const count = productCount ?? 0;
  // An empty department still links through — /category/:slug renders the
  // browse empty state, which is a better answer than a card that goes nowhere.
  const showPhoto = coverImage && !imageFailed;

  return (
    <Link
      to={`/category/${slug}`}
      className="group flex flex-col overflow-hidden rounded-2xl border border-sand-200 bg-white transition-all hover:-translate-y-0.5 hover:border-moss-300 hover:shadow-lift focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 dark:border-night-800 dark:bg-night-900 dark:hover:border-moss-700 dark:focus-visible:outline-moss-400"
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-sand-100 dark:bg-night-800">
        {showPhoto ? (
          <img
            src={coverImage}
            alt=""
            loading="lazy"
            decoding="async"
            onError={() => setImageFailed(true)}
            className="size-full object-cover transition-transform duration-300 group-hover:scale-105 motion-reduce:transition-none"
          />
        ) : (
          // No sellable product yet (or the photo 404s): a branded panel reads
          // as deliberate, where an empty grey box would read as a bug.
          <div className="flex size-full items-center justify-center bg-moss-100 dark:bg-moss-900">
            <LogoMark size={44} className="opacity-70" />
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-0.5 p-3 sm:p-4">
        <h3 className="truncate text-sm font-semibold text-sand-900 dark:text-sand-100">
          {name}
        </h3>
        <p className="text-xs text-sand-500 dark:text-sand-400">
          {count === 1 ? "1 item" : `${count} items`}
        </p>
      </div>
    </Link>
  );
}

export function CategoryGrid({ categories, loading = false }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="overflow-hidden rounded-2xl border border-sand-200 dark:border-night-800">
            <Skeleton className="aspect-[4/3] rounded-none" />
            <div className="space-y-2 p-3 sm:p-4">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!categories || categories.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4">
      {categories.map((category) => (
        <CategoryCard key={category.slug} category={category} />
      ))}
    </div>
  );
}
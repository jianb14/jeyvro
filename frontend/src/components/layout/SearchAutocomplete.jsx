/**
 * Search field with live autocomplete (§18.1 "autocomplete", "suggestions").
 *
 * Deliberately uses *prefix* suggestions from /api/v1/search/suggest/ rather
 * than ranked results: a shopper typing "bask" needs "Basket" to appear while
 * they are still mid-word, and the full ranked set belongs on the results
 * page. Any failure closes the panel instead of raising an error banner on a
 * keystroke — a broken suggest endpoint degrades to a plain search box, and
 * Enter still submits the query.
 *
 * The input owns its own text so the desktop and mobile instances in the
 * navbar can coexist without sharing (and fighting over) one value.
 */
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { cx } from "../../lib/cx";
import { getSuggestions, MIN_SUGGEST_LENGTH } from "../../data/search";
import { PackageIcon, SearchIcon, StoreIcon, TagIcon, XIcon } from "../ui/Icons";

const DEBOUNCE_MS = 250;

function buildGroups(data) {
  const definitions = [
    {
      label: "Products",
      icon: PackageIcon,
      items: (data.products ?? []).map((product) => ({
        key: `p:${product.slug}`,
        label: product.title,
        meta: product.storeName,
        path: `/product/${product.slug}`,
      })),
    },
    {
      label: "Stores",
      icon: StoreIcon,
      items: (data.stores ?? []).map((store) => ({
        key: `s:${store.slug}`,
        label: store.name,
        meta: store.productCount ? `${store.productCount} products` : "",
        path: `/store/${store.slug}`,
      })),
    },
    {
      label: "Categories",
      icon: TagIcon,
      items: (data.categories ?? []).map((category) => ({
        key: `c:${category.slug}`,
        label: category.name,
        meta: category.productCount ? `${category.productCount} products` : "",
        path: `/category/${category.slug}`,
      })),
    },
  ];
  // One running index across every group so ArrowUp/ArrowDown never have to
  // know where a group boundary is.
  let index = -1;
  return definitions
    .filter((group) => group.items.length > 0)
    .map((group) => ({
      ...group,
      items: group.items.map((item) => ({ ...item, icon: group.icon, index: (index += 1) })),
    }));
}

export function SearchAutocomplete({
  className,
  inputClassName,
  placeholder = "Search products…",
  onSubmit,
  onSelect,
}) {
  const [value, setValue] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  // Suggestions are stamped with the needle that produced them. Anything the
  // shopper sees is derived during render rather than written from an effect
  // (frontend-state rule 7), which also keeps a pending request from being
  // rendered as if it belonged to the current text.
  const [suggestions, setSuggestions] = useState({ needle: "", groups: [] });
  const listId = useId();
  const inputRef = useRef(null);

  const needle = value.trim();
  const groups = suggestions.groups;
  const flat = useMemo(() => groups.flatMap((group) => group.items), [groups]);
  const visible = open && needle.length >= MIN_SUGGEST_LENGTH;
  // Stale-while-revalidate: the previous matches stay on screen while the next
  // request is in flight, so the panel never flickers empty on a keystroke.
  const loading = visible && suggestions.needle !== needle;

  useEffect(() => {
    if (needle.length < MIN_SUGGEST_LENGTH) return undefined;
    let cancelled = false;
    const timer = setTimeout(() => {
      getSuggestions(needle)
        .then((data) => {
          if (cancelled) return;
          setSuggestions({ needle, groups: buildGroups(data) });
          // A new result set invalidates the old highlight.
          setActiveIndex(-1);
        })
        .catch(() => {
          if (cancelled) return;
          setSuggestions({ needle, groups: [] });
          setOpen(false);
        });
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [needle]);

  const close = () => {
    setOpen(false);
    setActiveIndex(-1);
  };

  // Wiping the text must also drop the stale suggestion set, or the panel would
  // keep rendering the previous needle's matches under an empty box.
  const clear = () => {
    setValue("");
    setSuggestions({ needle: "", groups: [] });
    setActiveIndex(-1);
    inputRef.current?.focus();
  };

  const choose = (item) => {
    close();
    onSelect?.(item.path);
  };

  const submit = (event) => {
    event.preventDefault();
    close();
    onSubmit?.(needle);
  };

  const handleKeyDown = (event) => {
    if (event.key === "Escape") {
      if (open) {
        event.preventDefault();
        close();
      }
      return;
    }
    if (!visible || flat.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => Math.min(current + 1, flat.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      // Releasing the highlight back to the input lets the shopper press
      // Enter to search their literal text instead of the highlighted row.
      setActiveIndex((current) => Math.max(current - 1, -1));
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      choose(flat[activeIndex]);
    }
  };

  return (
    <div
      className={cx("relative", className)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) close();
      }}
    >
      <form onSubmit={submit} role="search" className="relative">
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sand-400">
          <SearchIcon size={16} />
        </span>
        <input
          ref={inputRef}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setOpen(true);
            // A new keystroke invalidates the old highlight.
            setActiveIndex(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          role="combobox"
          aria-expanded={visible}
          aria-controls={visible ? listId : undefined}
          aria-autocomplete="list"
          aria-activedescendant={
            visible && activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined
          }
          aria-label="Search products"
          placeholder={placeholder}
          autoComplete="off"
          // This component owns the right padding: the caller's inputClassName
          // must not set `pr-*`, because the clear button widens the gutter
          // while it is visible. Two competing `pr-*` classes resolve by
          // stylesheet order, not by the order written here.
          className={cx(inputClassName, value ? "pr-10" : "pr-3.5")}
        />
        {value && (
          // type="button" keeps it from firing the form's submit handler.
          <button
            type="button"
            onClick={clear}
            aria-label="Clear search"
            className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-sand-400 transition-colors hover:bg-sand-100 hover:text-sand-700 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-moss-500 dark:hover:bg-night-800 dark:hover:text-sand-100 dark:focus-visible:outline-moss-400"
          >
            <XIcon size={15} />
          </button>
        )}
      </form>

      {visible && (
        // preventDefault on mousedown keeps focus in the input, so the panel
        // cannot close between mousedown and click and eat the selection.
        <div
          className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-sand-200 bg-white shadow-pop dark:border-night-800 dark:bg-night-900"
          onMouseDown={(event) => event.preventDefault()}
        >
          {flat.length === 0 ? (
            <p className="px-4 py-3 text-sm text-sand-500 dark:text-sand-400">
              {loading ? "Searching…" : <>No suggestions for “{needle}”</>}
            </p>
          ) : (
            <div
              id={listId}
              role="listbox"
              aria-label="Search suggestions"
              className="max-h-80 overflow-y-auto py-1.5"
            >
              {groups.map((group) => (
                <div key={group.label} role="group" aria-label={group.label}>
                  <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-widest text-sand-400">
                    {group.label}
                  </p>
                  {group.items.map((item) => (
                    <div
                      key={item.key}
                      id={`${listId}-${item.index}`}
                      role="option"
                      aria-selected={item.index === activeIndex}
                      onClick={() => choose(item)}
                      onMouseEnter={() => setActiveIndex(item.index)}
                      className={cx(
                        "flex cursor-pointer items-center gap-3 px-3 py-2 text-sm",
                        item.index === activeIndex
                          ? "bg-moss-100 text-moss-900 dark:bg-moss-900/60 dark:text-moss-100"
                          : "text-sand-700 dark:text-sand-300"
                      )}
                    >
                      <item.icon size={15} className="shrink-0 opacity-60" />
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      {item.meta && (
                        <span className="max-w-[45%] shrink-0 truncate text-xs text-sand-400">
                          {item.meta}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          <button
            type="button"
            onClick={() => {
              close();
              onSubmit?.(needle);
            }}
            className="block w-full border-t border-sand-200 px-4 py-2.5 text-left text-sm font-medium text-moss-700 transition-colors hover:bg-sand-50 dark:border-night-800 dark:text-moss-300 dark:hover:bg-night-800"
          >
            See all results for “{needle}”
          </button>
        </div>
      )}
    </div>
  );
}


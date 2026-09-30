/**
 * AuthShell — the frame that both /login and /register sit inside.
 *
 * The two routes were near-identical: a bare `max-w-md` card floating on an
 * empty sand-coloured page, with the whole viewport to either side of it. That
 * is the plainest possible reading of "sign in", and it wasted the one screen
 * where a brand can actually say something before the user types a password.
 * This shell replaces it with a two-column stage — artwork on the left, the
 * form on the right — which is the pattern every marketplace of this size uses.
 *
 * The artwork column is desktop-only. On phones it would push the form below
 * the fold, and a sign-in box that needs scrolling to reach the password field
 * is worse than a plain one, so below `lg` the shell collapses to just the
 * form. The shell is a floor, not a fixed height: a tall viewport lets the
 * artwork grow to fill it, and a short one (landscape phone, split screen)
 * simply scrolls.
 *
 * The photo is remote and swappable in one place per route, mirroring
 * HeroBanner: the <img> is absolutely positioned so late bytes cannot shift
 * the layout, `width`/`height` still declare the CDN's true ratio, and
 * `onError` falls back to a flat moss panel with the mark — a dead URL leaves
 * a branded shape rather than a broken-image glyph (frontend-performance).
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { cx } from "../../lib/cx";
import { ArrowLeftIcon, LogoLockup, LogoMark } from "../ui/Icons";

/**
 * @param {object} props
 * @param {{src:string,width:number,height:number,alt:string,position?:string}} props.photo
 * @param {string} props.eyebrow   Small label above the headline.
 * @param {string} props.headline  The panel's main line.
 * @param {string} props.blurb     One supporting sentence.
 * @param {Array<{icon:Function,title:string,body:string}>} props.highlights
 * @param {import("react").ReactNode} props.children  The form column.
 */
export function AuthShell({ photo, eyebrow, headline, blurb, highlights = [], children }) {
  const [photoFailed, setPhotoFailed] = useState(false);

  return (
    <div className="min-h-screen bg-sand-50 dark:bg-night-950">
      <main className="mx-auto grid w-full max-w-6xl items-center gap-10 px-4 py-8 sm:px-6 lg:min-h-screen lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:px-8 lg:py-12">
        <ArtworkColumn
          photo={photo}
          eyebrow={eyebrow}
          headline={headline}
          blurb={blurb}
          highlights={highlights}
          photoFailed={photoFailed}
          onPhotoError={() => setPhotoFailed(true)}
        />
        <div className="flex w-full flex-col items-center gap-6">
          {/* Stands in for the Navbar this layout drops, and is the mobile half
              of the exit. `lg:hidden` because the artwork column carries its own
              ghost version of this link on desktop — two "back to the store"
              controls on one screen would be one too many.

              It is a real, focusable, announced link rather than decoration:
              below `lg` the picture is gone, so this is the only way back into
              the store for anyone who arrived by typing the URL. */}
          <Link
            to="/"
            className="flex items-center gap-1.5 rounded text-sm font-medium text-sand-500 transition-colors hover:text-moss-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 lg:hidden dark:text-sand-400 dark:hover:text-moss-300 dark:focus-visible:outline-moss-400"
          >
            <ArrowLeftIcon size={15} />
            Back to the store
          </Link>
          {children}
        </div>
      </main>
    </div>
  );
}

function ArtworkColumn({ photo, eyebrow, headline, blurb, highlights, photoFailed, onPhotoError }) {
  return (
    // Decoration is hidden from assistive tech piecemeal rather than by
    // putting `aria-hidden` on the whole section, because the section now also
    // holds the way back into the store. An `aria-hidden` ancestor would make
    // that link unreachable to screen readers and illegal to focus — the exact
    // dead end the link exists to prevent.
    <section className="relative hidden lg:block">
      <div className="relative isolate flex min-h-[600px] flex-col overflow-hidden rounded-3xl bg-moss-900 p-10 shadow-lift">
        <div className="absolute inset-0" aria-hidden="true">
          {photoFailed ? (
            <div className="absolute inset-0 flex items-center justify-center bg-moss-800">
              <LogoMark size={96} className="opacity-40" />
            </div>
          ) : (
            <img
              src={photo.src}
              alt=""
              width={photo.width}
              height={photo.height}
              loading="lazy"
              decoding="async"
              onError={onPhotoError}
              // Portrait or landscape source in a squarer stage, so `object-cover`
              // crops away most of the frame and `object-position` decides which
              // band survives. It is a prop rather than a fixed value because the
              // two routes use photos with genuinely different subjects: one is a
              // shopper framed head-to-toe, the other a seller leaning over boxes,
              // and the band that keeps the first readable slices the second in
              // half. Anchoring near the top favours faces, which is what the
              // lightly-scrimmed lower half of this panel is showing off.
              className={cx(
                "absolute inset-0 size-full object-cover dark:brightness-90",
                photo.position
              )}
            />
          )}

        {/* Two scrims, because one gradient cannot do this job. The copy sits in
            the upper half, so a single ramp dense at the top either drowns the
            photo entirely or leaves the caption unreadable.

            The first is a flat, light moss wash. It is what makes the photo read
            as *ours* rather than stock imagery, and it is deliberately faint. The
            second is a gradient doing the one job only a gradient can: dark
            enough across the top where the headline and highlights sit, then
            easing to fully transparent by the bottom edge.

            That ease is the whole point. This used to carry a `from-35%` hard
            stop, which pinned the first 35% of the panel at full opacity and
            drew a flat moss slab across the top of the photo with a visible
            seam where the ramp began — it read as a broken image, not a
            vignette. A single continuous ramp with no intermediate stop
            (`via-…-45%`, `to-…-95%`) has no edge to see: the darkening is
            strongest where the white copy actually sits and simply gets out of
            the way as the subject comes into frame. */}
          <div className="absolute inset-0 bg-moss-950/15" />
          <div className="absolute inset-0 bg-linear-to-b from-moss-950/70 via-moss-950/55 via-45% to-transparent to-95%" />
        </div>

        <div className="relative flex flex-col gap-10 pb-14" aria-hidden="true">
          {/* No logo up here. The brand mark used to sit at the top of this
              panel in white, which meant the wordmark lived in two places at
              once once the form column grew its own lockup — and the white
              version had to be hand-filtered (`[filter:brightness(0)_invert(1)]!`)
              to survive LogoMark's internal dark-mode brightness lift, with an
              `!` important to stop dark mode re-tinting it. The copy now owns
              the top of the panel and the brand lives once, in the column
              people actually came here to use. */}

          <div className="flex flex-col gap-3">
            <p className="flex items-center gap-2 text-xs font-semibold tracking-[0.18em] text-moss-200 uppercase">
              <span className="h-px w-8 bg-moss-400/70" />
              {eyebrow}
            </p>
            <h2 className="max-w-sm font-display text-3xl leading-tight font-bold text-balance text-white">
              {headline}
            </h2>
            <p className="max-w-sm text-sm leading-relaxed text-sand-200/90">{blurb}</p>
          </div>

          <ul className="flex flex-col gap-3">
            {highlights.map(({ icon: Icon, title, body }) => (
              <li key={title} className="flex items-start gap-3">
                <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-white/12 text-moss-100 ring-1 ring-white/15">
                  <Icon size={16} />
                </span>
                <span className="flex flex-col">
                  <span className="text-sm font-semibold text-white">{title}</span>
                  <span className="text-xs leading-relaxed text-sand-300/80">{body}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* The exit lives *on* the artwork now, bottom-left, as a ghost pill.
            It used to float above the form in the sand-coloured column, which
            put the only escape from this screen on the opposite side of the
            viewport from the picture it belongs to. Anchored here it reads as
            part of the image — a real control, with a real focus ring and a
            translucent surface that keeps white text legible over whatever the
            photo happens to be doing in that corner.

            It deliberately sits outside the `aria-hidden` copy wrapper above:
            the marketing copy is noise to announce, but a link that strands
            someone on a page they cannot leave is not. */}
        <Link
          to="/"
          className="absolute bottom-10 left-10 inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm transition-colors hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        >
          <ArrowLeftIcon size={15} />
          Back to the store
        </Link>
      </div>
    </section>
  );
}

/**
 * The form column. It exists so /login and /register cannot drift apart again:
 * identical width, identical title scale, identical footer treatment.
 *
 * This is deliberately *not* a card any more. It used to be a `rounded-2xl`
 * white panel with a border and a shadow, and on a full-height split screen
 * that boxed the form in the middle of a lot of empty sand — the exact "floating
 * login box" look the split layout exists to replace. Dropping the container
 * lets the form sit directly on the page, which is also what the reference
 * pattern this was modelled on does.
 *
 * `brand` renders the Jeyvro lockup above the title. It lives here rather than
 * in the artwork panel so the wordmark appears exactly once per page, next to
 * the thing people came to do.
 */
export function AuthCard({ brand = true, title, description, children, footer }) {
  return (
    <div className="animate-slide-up flex w-full max-w-md flex-col gap-6">
      <div className="flex flex-col items-center gap-4 text-center">
        {brand && <LogoLockup size={40} />}
        <div className="flex flex-col gap-2">
          <h1 className="font-display text-3xl font-bold tracking-tight text-balance text-sand-900 dark:text-sand-50">
            {title}
          </h1>
          <p className="text-sm leading-relaxed text-sand-500 dark:text-sand-400">
            {description}
          </p>
        </div>
      </div>
      {children}
      {footer && (
        // The footer is where the "other" auth route lives. There is no rule
        // above it any more: a `border-t` drew a hard line under the social
        // buttons and made the sign-up link read as a separate, lesser step
        // rather than the obvious next thing to do. Space alone is enough to
        // group it, and it keeps the form reading as one continuous column.
        <div className="text-center text-sm text-sand-500 dark:text-sand-400">{footer}</div>
      )}
    </div>
  );
}

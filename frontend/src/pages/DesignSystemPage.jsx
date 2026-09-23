import { Navbar } from "../components/layout/Navbar";
import { FoundationsSection } from "../sections/FoundationsSection";
import { ButtonsSection } from "../sections/ButtonsSection";
import { FormsSection } from "../sections/FormsSection";
import { SelectionSection } from "../sections/SelectionSection";
import { DataDisplaySection } from "../sections/DataDisplaySection";
import { FeedbackSection } from "../sections/FeedbackSection";
import { NavigationSection } from "../sections/NavigationSection";
import { OverlaysSection } from "../sections/OverlaysSection";
import { ChipsSection } from "../sections/ChipsSection";
import { ProgressionSection } from "../sections/ProgressionSection";
import { WorkspaceSection } from "../sections/WorkspaceSection";
import { MarketplaceSection } from "../sections/MarketplaceSection";
import { LogoMark, LeafIcon, GithubIcon } from "../components/ui/Icons";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

const NAV_SECTIONS = [
  { id: "foundations", label: "Foundations" },
  { id: "buttons", label: "Buttons & Badges" },
  { id: "forms", label: "Form Controls" },
  { id: "selection", label: "Selection Controls" },
  { id: "data-display", label: "Data Display" },
  { id: "feedback", label: "Feedback" },
  { id: "navigation", label: "Navigation" },
  { id: "overlays", label: "Overlays" },
  { id: "chips", label: "Chips & Rating" },
  { id: "progression", label: "Steppers & Timeline" },
  { id: "workspace", label: "Workspace Patterns" },
  { id: "marketplace", label: "Marketplace" },
];

function Hero() {
  return (
    <div id="overview" className="scroll-mt-24">
      <div className="flex flex-wrap items-center gap-2.5">
        <Badge tone="moss" dot variant="soft">v1.0 — Stable</Badge>
        <Badge tone="neutral" variant="outline">React 19 · Tailwind v4</Badge>
        <Badge tone="neutral" variant="outline">Light / Dark</Badge>
      </div>
      <h1 className="mt-5 max-w-2xl font-display text-4xl font-semibold tracking-tight text-sand-900 dark:text-sand-100 sm:text-5xl">
        The Jeyvro Design&nbsp;System — <span className="text-moss-600 dark:text-moss-400">calm by design.</span>
      </h1>
      <p className="mt-4 max-w-xl text-base leading-relaxed text-sand-500 dark:text-sand-400">
        Isang kumpletong component library: brand foundations, essential UI components
        with variants, at demo page — lahat ready for production, walang gradients,
        walang sakit sa mata.
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Button size="lg" leadingIcon={LeafIcon} onClick={() => document.getElementById("foundations")?.scrollIntoView({ behavior: "smooth" })}>
          Explore components
        </Button>
        <Button size="lg" variant="outline" leadingIcon={GithubIcon}>
          View source
        </Button>
      </div>
      <div className="mt-10 flex flex-wrap items-center gap-8 border-y border-sand-200 py-5 dark:border-night-800">
        {[
          ["45", "Components"],
          ["70+", "Variants"],
          ["6", "Color scales"],
          ["100%", "Dark mode"],
        ].map(([num, label]) => (
          <div key={label} className="flex items-baseline gap-2">
            <span className="font-display text-2xl font-semibold text-moss-700 dark:text-moss-300">{num}</span>
            <span className="text-sm text-sand-500 dark:text-sand-400">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SidebarNav() {
  return (
    <nav aria-label="Sections" className="sticky top-24 hidden w-52 shrink-0 flex-col gap-1 lg:flex">
      <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-widest text-sand-400">
        On this page
      </p>
      {NAV_SECTIONS.map((s) => (
        <a
          key={s.id}
          href={`#${s.id}`}
          className="rounded-lg px-3 py-2 text-sm text-sand-500 transition-colors hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
        >
          {s.label}
        </a>
      ))}
      <div className="mt-4 rounded-xl border border-moss-200 bg-moss-50 p-4 dark:border-moss-900 dark:bg-moss-950/40">
        <LogoMark size={24} />
        <p className="mt-2 text-xs leading-relaxed text-moss-800 dark:text-moss-200">
          Built with React 19 + Tailwind CSS v4. Zero gradients, promise.
        </p>
      </div>
    </nav>
  );
}

export function DesignSystemPage() {
  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
        <div className="animate-slide-up pt-12 sm:pt-16">
          <Hero />
          <div className="mt-14 flex gap-12">
            <SidebarNav />
            <div className="min-w-0 flex-1">
              <FoundationsSection />
              <ButtonsSection />
              <FormsSection />
              <SelectionSection />
              <DataDisplaySection />
              <FeedbackSection />
              <NavigationSection />
              <OverlaysSection />
              <ChipsSection />
              <ProgressionSection />
              <WorkspaceSection />
              <MarketplaceSection />
            </div>
          </div>
        </div>
      </main>
      <footer className="border-t border-sand-200 py-8 dark:border-night-800">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <LogoMark size={22} />
            <span className="text-sm text-sand-500 dark:text-sand-400">
              Jeyvro Design System · {new Date().getFullYear()}
            </span>
          </div>
          <p className="text-xs text-sand-400">Calm green. No gradients. Kumpleto na.</p>
        </div>
      </footer>
    </>
  );
}

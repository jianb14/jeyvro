import { useState } from "react";
import { Section, Demo } from "./shared";
import { Tabs, TabPanel } from "../components/ui/Tabs";
import { Breadcrumb } from "../components/ui/Breadcrumb";
import { Pagination } from "../components/ui/Pagination";
import { Accordion } from "../components/ui/Accordion";
import { BellIcon, SettingsIcon, UserIcon } from "../components/ui/Icons";

const FAQ = [
  {
    id: "q1",
    title: "What is the Jeyvro Design System?",
    content:
      "It's a complete, calm component library for React + Tailwind CSS v4 — from brand tokens (colors, type, shadows) to essential UI components with variants, all dark-mode ready.",
  },
  {
    id: "q2",
    title: "Can I customize the colors?",
    content:
      "Yes. All colors are defined as CSS variables in index.css under the Tailwind @theme block. Change the moss scale once and every component follows.",
  },
  {
    id: "q3",
    title: "Is it accessible?",
    content:
      "Components use semantic HTML with proper roles (tablist, radiogroup, dialog, switch), visible focus outlines, aria attributes, and keyboard support for menus, modals, and pagination.",
  },
  {
    id: "q4",
    title: "Does it support dark mode?",
    content:
      "Fully. The Navbar theme toggle switches a .dark class on the root; every component has tuned dark surfaces so nothing gets eye-straining.",
  },
];

export function NavigationSection() {
  const [page, setPage] = useState(3);

  return (
    <Section
      id="navigation"
      title="Navigation"
      description="Tabs (line & pill), breadcrumbs, pagination, at accordion — para sa maayos na pag-navigate."
    >
      <Demo label="Tabs — line variant" className="w-full" align="column">
        <Tabs
          variant="line"
          tabs={[
            { id: "overview", label: "Overview", icon: BellIcon },
            { id: "profile", label: "Profile", icon: UserIcon },
            { id: "settings", label: "Settings", icon: SettingsIcon },
          ]}
        />
        <TabPanel>
          <p className="text-sm text-sand-500 dark:text-sand-400">
            Line tabs sit on a border with an animated moss underline for the active item.
          </p>
        </TabPanel>
      </Demo>

      <Demo label="Tabs — pill variant">
        <Tabs
          variant="pill"
          tabs={[
            { id: "day", label: "Day" },
            { id: "week", label: "Week" },
            { id: "month", label: "Month" },
            { id: "year", label: "Year" },
          ]}
          defaultTab="week"
        />
      </Demo>

      <Demo label="Breadcrumb & Pagination">
        <Breadcrumb
          items={[
            { label: "Home", href: "#overview" },
            { label: "Projects", href: "#overview" },
            { label: "Design System" },
          ]}
        />
        <div className="flex flex-col items-start gap-2">
          <Pagination total={9} initial={3} onChange={setPage} />
          <p className="text-xs text-sand-400">Current page: {page}</p>
        </div>
      </Demo>

      <Demo label="Accordion" className="w-full">
        <Accordion className="w-full" items={FAQ} />
      </Demo>
    </Section>
  );
}

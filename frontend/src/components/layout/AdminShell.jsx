/**
 * Admin console shell — the operator-side chrome for /staff.
 *
 * The storefront `Navbar` is deliberately NOT used here. It carries a cart
 * badge, a wishlist, a product search and a live category rail — all of which
 * are shopping affordances, and every one of them is a click that takes an
 * operator out of the console they came to work in. An admin shell states what
 * surface you are on before you touch anything.
 *
 * What survives from the storefront is the identity (the brand name) and a
 * deliberate "View storefront" escape hatch, because staff moderate what the
 * public actually sees and need to see it as a shopper does.
 *
 * This shell is presentational: it renders whatever `sections` it is handed and
 * knows nothing about roles. Group-based nav filtering stays with the layout
 * that owns the auth state, so the access rules live in one place (§4).
 *
 * Deliberately absent: any metric, chart or export. Platform analytics is
 * Phase 19 (ROADMAP §19.1) and reads from reporting aggregates — a dashboard
 * that queries live OLTP tables to fill this frame is exactly what that phase
 * exists to prevent.
 */
import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { cx } from "../../lib/cx";
import { useAuth } from "../../features/auth/AuthContext";
import { Avatar } from "../ui/Avatar";
import { Badge } from "../ui/Badge";
import { Drawer } from "../ui/Drawer";
import { DropdownMenu } from "../ui/DropdownMenu";
import { ThemeToggle } from "../ui/ThemeToggle";
import {
  ExternalLinkIcon,
  LogoLockup,
  LogOutIcon,
  MenuIcon,
  UserIcon,
} from "../ui/Icons";

const navClass = ({ isActive }) =>
  cx(
    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-moss-100 text-moss-800 dark:bg-moss-900 dark:text-moss-200"
      : "text-sand-600 hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
  );

/** One block per section. An empty section renders nothing at all — a heading
    with no links under it reads as a broken menu, and a role that cannot use a
    whole section should not see its label (§4 hides what the backend refuses). */
function SectionLinks({ sections, onNavigate }) {
  return (
    <>
      {sections.map((section) => (
        <div key={section.label} className="mb-5 last:mb-0">
          <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-sand-400 dark:text-sand-500">
            {section.label}
          </p>
          <div className="flex flex-col gap-0.5">
            {section.items.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={navClass}
                onClick={onNavigate}
              >
                <Icon size={16} className="shrink-0" />
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

export function AdminShell({
  sections = [],
  title = "Operator console",
  roles = [],
  navLabel = "Staff navigation",
  children,
}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(false);

  const displayName = user ? user.first_name || user.email : "";

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <div className="min-h-dvh bg-sand-50 dark:bg-night-950">
      {/* Fixed rail: the console is a workspace, so its navigation does not
          scroll away with the page the way a storefront header does. The
          content column below is offset by the same width on lg. */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-sand-200 bg-white lg:flex dark:border-night-800 dark:bg-night-900">
        {/* The real logo lockup, not a typed-out wordmark: the hexagon mark plus
            the Michroma wordmark is the brand, and reproducing it in body type
            would be a different-looking logo. Same component the storefront
            header uses, so the identity is genuinely one thing. Centred in its
            own band with no rule under it — the rail reads as one surface, and
            the logo is a badge on it rather than a section header. */}
        <div className="flex h-16 shrink-0 items-center justify-center">
          <LogoLockup size={28} />
        </div>

        <div className="px-5 py-4">
          <p className="text-sm font-medium text-sand-900 dark:text-sand-100">
            {title}
          </p>
          {roles.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {roles.map((role) => (
                <Badge key={role} tone="moss" size="sm">
                  {role.replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          )}
        </div>

        <nav aria-label={navLabel} className="flex-1 overflow-y-auto px-3 py-5">
          <SectionLinks sections={sections} />
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-sand-200 bg-sand-50/85 px-4 backdrop-blur-md sm:px-6 lg:px-8 dark:border-night-800 dark:bg-night-950/85">
          <button
            onClick={() => setNavOpen(true)}
            aria-label="Open console navigation"
            className="-ml-1 inline-flex size-10 items-center justify-center rounded-lg text-sand-600 transition-colors hover:bg-sand-100 hover:text-sand-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moss-500 lg:hidden dark:text-sand-300 dark:hover:bg-night-800"
          >
            <MenuIcon size={20} />
          </button>
          {/* The rail is hidden below lg, so the logo has to be restated here or
              a phone user has no idea which surface they are on. */}
          <LogoLockup size={26} className="lg:hidden" />

          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            {user && (
              <DropdownMenu
                align="end"
                trigger={
                  <button
                    aria-label="Account menu"
                    className="rounded-full outline-offset-2 outline-moss-600/60 focus-visible:outline-2"
                  >
                    <Avatar name={displayName} size="sm" />
                  </button>
                }
                items={[
                  {
                    key: "profile",
                    label: "My account",
                    icon: UserIcon,
                    onSelect: () => navigate("/account"),
                  },
                  {
                    key: "storefront",
                    label: "View storefront",
                    icon: ExternalLinkIcon,
                    onSelect: () => navigate("/"),
                  },
                  { key: "sep", divider: true },
                  {
                    key: "logout",
                    label: "Log out",
                    icon: LogOutIcon,
                    tone: "danger",
                    onSelect: handleLogout,
                  },
                ]}
              />
            )}
          </div>
        </header>

        <main className="px-4 py-8 sm:px-6 lg:px-8">{children}</main>
      </div>

      <Drawer
        open={navOpen}
        onClose={() => setNavOpen(false)}
        side="left"
        title={title}
      >
        <nav aria-label={navLabel} className="flex flex-col gap-0.5 px-1">
          <SectionLinks
            sections={sections}
            onNavigate={() => setNavOpen(false)}
          />
        </nav>
      </Drawer>
    </div>
  );
}

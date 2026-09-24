import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTheme } from "../../lib/useTheme";
import { useAuth } from "../../features/auth/AuthContext";
import { LogoMark, MenuIcon, XIcon, SunIcon, MoonIcon, GithubIcon } from "../ui/Icons";
import { Button } from "../ui/Button";
import { Avatar } from "../ui/Avatar";
import { DropdownMenu } from "../ui/DropdownMenu";
import {
  UserIcon,
  SettingsIcon,
  LogOutIcon,
  BellIcon,
  HeartIcon,
  DownloadIcon,
  StoreIcon,
} from "../ui/Icons";

const NAV_LINKS = [
  { label: "Overview", href: "#overview" },
  { label: "Foundations", href: "#foundations" },
  { label: "Components", href: "#buttons" },
  { label: "Patterns", href: "#data-display" },
];

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="inline-flex size-10 items-center justify-center rounded-xl border border-sand-300 bg-white text-sand-600 transition-all hover:border-moss-400 hover:text-moss-700 dark:border-night-700 dark:bg-night-900 dark:text-sand-300 dark:hover:border-moss-600 dark:hover:text-moss-300"
    >
      {theme === "dark" ? <SunIcon size={16} /> : <MoonIcon size={16} />}
    </button>
  );
}

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-sand-200/80 bg-sand-50/85 backdrop-blur-md dark:border-night-800 dark:bg-night-950/85">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <a href="#overview" className="flex items-center gap-2.5">
          <LogoMark size={30} />
          <span className="font-display text-xl font-semibold tracking-tight text-sand-900 dark:text-sand-100">
            Jeyvro
          </span>
        </a>

        <div className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="rounded-lg px-3.5 py-2 text-sm font-medium text-sand-600 transition-colors hover:bg-sand-100 hover:text-sand-900 dark:text-sand-400 dark:hover:bg-night-800 dark:hover:text-sand-100"
            >
              {link.label}
            </a>
          ))}
        </div>

        <div className="hidden items-center gap-2.5 md:flex">
          <DropdownMenu
            align="end"
            trigger={
              <button
                aria-label="Notifications"
                className="relative inline-flex size-10 items-center justify-center rounded-xl border border-sand-300 bg-white text-sand-600 transition-all hover:border-moss-400 hover:text-moss-700 dark:border-night-700 dark:bg-night-900 dark:text-sand-300"
              >
                <BellIcon size={16} />
                <span className="absolute right-2.5 top-2.5 size-2 rounded-full bg-danger-500 ring-2 ring-white dark:ring-night-900" />
              </button>
            }
            items={[
              { key: "t1", label: "Welcome to Jeyvro DS", icon: HeartIcon, onSelect: () => {} },
              { key: "t2", label: "New components available", icon: BellIcon, onSelect: () => {} },
              { key: "sep", divider: true },
              { key: "t3", label: "Download changelog", icon: DownloadIcon, shortcut: "⌘D", onSelect: () => {} },
            ]}
          />
          <ThemeToggle />
          {loading ? null : user ? (
            <DropdownMenu
              align="end"
              trigger={
                <button aria-label="Account menu" className="rounded-full outline-offset-2 outline-moss-600/60 focus-visible:outline-2">
                  <Avatar name={user.first_name || user.email} size="sm" status="online" />
                </button>
              }
              items={[
                { key: "profile", label: "My account", icon: UserIcon, onSelect: () => navigate("/account") },
                { key: "sell", label: "Sell on Jeyvro", icon: StoreIcon, onSelect: () => navigate("/sell") },
                { key: "settings", label: "Settings", icon: SettingsIcon, onSelect: () => navigate("/account") },
                { key: "sep", divider: true },
                { key: "logout", label: "Log out", icon: LogOutIcon, tone: "danger", onSelect: handleLogout },
              ]}
            />
          ) : (
            <>
              <Link to="/login">
                <Button variant="outline" size="sm">Log in</Button>
              </Link>
              <Link to="/register">
                <Button size="sm">Sign up</Button>
              </Link>
            </>
          )}
        </div>

        <button
          onClick={() => setMobileOpen((o) => !o)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          className="inline-flex size-10 items-center justify-center rounded-xl border border-sand-300 bg-white text-sand-600 dark:border-night-700 dark:bg-night-900 dark:text-sand-300 md:hidden"
        >
          {mobileOpen ? <XIcon size={18} /> : <MenuIcon size={18} />}
        </button>
      </nav>

      {mobileOpen && (
        <div className="animate-fade-in border-t border-sand-200 bg-sand-50 px-4 pb-5 pt-3 dark:border-night-800 dark:bg-night-950 md:hidden">
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-100 dark:text-sand-300 dark:hover:bg-night-800"
              >
                {link.label}
              </a>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <ThemeToggle />
            <Button className="flex-1" leadingIcon={GithubIcon}>
              Get Started
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}

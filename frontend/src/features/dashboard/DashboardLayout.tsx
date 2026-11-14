import { Suspense, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { BrandMark } from "../../shared/ui/brand";
import { WARM_GLASS } from "../../shared/ui/brandStyles";
import { Loading } from "../../shared/ui/primitives";
import { useMe } from "../auth/useMe";
import { useSignOut } from "../auth/useSignOut";
import { PLATFORM_TERMS_PATH } from "../legal/PlatformTermsPage";
import { visibleLinks, type DashboardSection } from "./navigation";

// Íconos de línea del menú, dibujados con el color del texto.
const ICONS: Record<DashboardSection, ReactNode> = {
  home: <path d="M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1z" />,
  agenda: (
    <>
      <rect x="4" y="5" width="16" height="15" rx="2" />
      <path d="M8 3v4M16 3v4M4 10h16" />
    </>
  ),
  appointments: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" />
    </>
  ),
  customers: (
    <>
      <circle cx="9" cy="8.5" r="3.2" />
      <path d="M3.5 19c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5M15.5 6a3 3 0 0 1 0 6M17 14.5c2 .5 3.2 2 3.5 4.5" />
    </>
  ),
  services: <path d="M6 4v16M6 4l8 8-8 8M14 12h6" />,
  team: (
    <>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5" />
    </>
  ),
  resources: (
    <>
      <rect x="4" y="4" width="7" height="7" rx="1.5" />
      <rect x="13" y="4" width="7" height="7" rx="1.5" />
      <rect x="4" y="13" width="7" height="7" rx="1.5" />
      <rect x="13" y="13" width="7" height="7" rx="1.5" />
    </>
  ),
  hours: (
    <>
      <circle cx="12" cy="13" r="7.5" />
      <path d="M12 9v4h3M9 2.5h6" />
    </>
  ),
  reports: <path d="M4 20h16M7 16v-5M12 16V7M17 16v-8" />,
  company: (
    <path d="M4 21V6a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v15M14 10h5a1 1 0 0 1 1 1v10M3 21h18M8 9h2M8 13h2M8 17h2" />
  ),
};

function Icon({ section }: { section: DashboardSection }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="size-5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ICONS[section]}
    </svg>
  );
}

// El menú en tres grupos, como la referencia: el día a día, el negocio y la gestión.
const GROUPS: { label: string; sections: DashboardSection[] }[] = [
  { label: "dashboard.groups.daily", sections: ["home", "agenda", "appointments", "customers"] },
  { label: "dashboard.groups.business", sections: ["services", "team", "resources", "hours"] },
  { label: "dashboard.groups.management", sections: ["reports", "company"] },
];

function initials(name: string, email: string) {
  return (name.trim() || email)
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

/** Marco del panel del negocio: vidrio blanco y rojo metalizado, menú según rol y módulos, y el
 *  contenido de cada sección en el `Outlet`. Solo se usa dentro de `AuthGate`. */
export default function DashboardLayout() {
  const { t } = useTranslation();
  const me = useMe();
  const signOut = useSignOut();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");

  if (!me.data) return null;
  const visible = new Set(visibleLinks(me.data).map((link) => link.section));
  const links = new Map(visibleLinks(me.data).map((link) => [link.section, link]));
  const user = me.data.user;
  const businessName = me.data.tenant?.name ?? t("app.name");
  const canSearch = visible.has("customers");

  function search(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    navigate(q ? `/clientes?q=${encodeURIComponent(q)}` : "/clientes");
    setMenuOpen(false);
  }

  const sidebar = (
    <nav
      id="menu-panel"
      aria-label={t("nav.main")}
      className={`flex h-full flex-col gap-5 overflow-y-auto p-4 [scrollbar-width:none] ${WARM_GLASS}`}
    >
      <Link to="/panel" className="px-1 pt-1">
        <BrandMark name={businessName} />
      </Link>

      <div className="rounded-2xl border border-white/12 bg-white/8 px-4 py-3">
        <p className="truncate font-semibold">{user.full_name || user.email}</p>
        <p className="text-sm text-white/70">{t(`dashboard.roles.${me.data.role}`)}</p>
      </div>

      {GROUPS.map((group) => {
        const sections = group.sections.filter((section) => visible.has(section));
        if (sections.length === 0) return null;
        return (
          <div key={group.label} className="flex flex-col gap-1">
            <p className="px-3 text-sm text-white/55">{t(group.label)}</p>
            {sections.map((section) => (
              <NavLink
                key={section}
                to={links.get(section)!.path}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `flex min-h-10 items-center gap-3 rounded-2xl px-3 font-medium transition-colors focus-visible:outline-2 ${
                    isActive ? "metal" : "text-white/85 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                <Icon section={section} />
                <span className="flex-1">{t(`dashboard.nav.${section}`)}</span>
              </NavLink>
            ))}
          </div>
        );
      })}

      <Link
        to={PLATFORM_TERMS_PATH}
        className="mt-auto px-1 text-sm text-white/60 underline hover:text-white"
      >
        {t("platformTerms.link")}
      </Link>
    </nav>
  );

  return (
    <div className="platform owner min-h-screen">
      <a
        href="#contenido"
        className="sr-only rounded bg-white px-3 py-2 focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50"
      >
        {t("nav.skip")}
      </a>

      <div className="mx-auto flex max-w-[1500px] gap-5 p-3 sm:p-4">
        <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-[272px] shrink-0 lg:block">
          {sidebar}
        </aside>

        {menuOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <button
              type="button"
              aria-label={t("nav.closeMenu")}
              className="absolute inset-0 bg-black/40"
              onClick={() => setMenuOpen(false)}
            />
            <div className="relative h-full w-[min(86vw,300px)] p-3">{sidebar}</div>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <header className="glass sticky top-3 z-30 flex items-center gap-3 rounded-[24px] border px-3 py-3 sm:px-4">
            <button
              type="button"
              aria-label={t("nav.openMenu")}
              aria-expanded={menuOpen}
              className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-white/70 lg:hidden"
              onClick={() => setMenuOpen(true)}
            >
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="size-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <path d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </button>
            {canSearch ? (
              <form role="search" onSubmit={search} className="min-w-0 flex-1">
                <label className="flex min-h-11 items-center gap-3 rounded-2xl bg-white/70 px-4 ring-1 ring-black/5 focus-within:ring-2 focus-within:ring-[var(--pf-green)]">
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    className="size-5 shrink-0 text-[var(--pf-muted)]"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  >
                    <circle cx="11" cy="11" r="6.5" />
                    <path d="m16 16 4 4" />
                  </svg>
                  <span className="sr-only">{t("dashboard.searchLabel")}</span>
                  <input
                    type="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={t("dashboard.searchPlaceholder")}
                    className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--pf-muted)]"
                  />
                </label>
              </form>
            ) : (
              <p className="min-w-0 flex-1 truncate font-semibold">{businessName}</p>
            )}
            <div className="hidden items-center gap-3 md:flex">
              <span
                aria-hidden="true"
                className="flex size-11 items-center justify-center rounded-full bg-[var(--pf-green-soft)] text-sm font-semibold text-[var(--pf-green-ink)]"
              >
                {initials(user.full_name, user.email)}
              </span>
              <span className="min-w-0">
                <span className="block max-w-40 truncate text-sm font-semibold">
                  {user.full_name || user.email}
                </span>
                <span className="block text-sm text-[var(--pf-muted)]">
                  {t(`dashboard.roles.${me.data.role}`)}
                </span>
              </span>
            </div>
            <button
              type="button"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
              className="min-h-11 shrink-0 rounded-2xl bg-white/70 px-4 text-sm font-medium ring-1 ring-black/5 hover:bg-white focus-visible:outline-2"
            >
              {t("nav.signOut")}
            </button>
          </header>

          <main id="contenido" className="platform-main min-w-0 pb-10">
            <Suspense fallback={<Loading />}>
              <Outlet />
            </Suspense>
          </main>
        </div>
      </div>
    </div>
  );
}

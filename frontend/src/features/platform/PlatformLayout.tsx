import { useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useMe } from "../auth/useMe";
import { useSignOut } from "../auth/useSignOut";
import { PLATFORM_TERMS_PATH } from "../legal/PlatformTermsPage";
import { BrandMark } from "../../shared/ui/brand";
import { DARK_GLASS } from "../../shared/ui/brandStyles";
import { usePlatformSummary } from "./api";

// Íconos de línea del menú, dibujados con el color del texto.
const ICONS: Record<string, ReactNode> = {
  summary: <path d="M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1z" />,
  tenants: (
    <>
      <path d="M4 21V6a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v15M14 10h5a1 1 0 0 1 1 1v10M3 21h18" />
      <path d="M8 9h2M8 13h2M8 17h2M17 14h0M17 17h0" />
    </>
  ),
  plans: <path d="m12 4 8 4-8 4-8-4zM4 12l8 4 8-4M4 16l8 4 8-4" />,
  audit: <path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6z M9 12l2 2 4-4" />,
  security: (
    <>
      <rect x="5" y="10" width="14" height="10" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </>
  ),
};

function Icon({ name }: { name: string }) {
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
      {ICONS[name]}
    </svg>
  );
}

// Vidrio oscuro de la barra lateral, como la referencia.
const SIDEBAR_SURFACE = `flex h-full flex-col gap-6 overflow-y-auto p-4 ${DARK_GLASS}`;

const GROUPS = [
  {
    label: "nav.groupPlatform",
    links: [
      { to: "/resumen", key: "summary" },
      { to: "/empresas", key: "tenants" },
      { to: "/planes", key: "plans" },
    ],
  },
  {
    label: "nav.groupControl",
    links: [
      { to: "/auditoria", key: "audit" },
      { to: "/seguridad", key: "security" },
    ],
  },
] as const;

function initials(name: string, email: string) {
  const source = name.trim() || email;
  return source
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function PlatformLayout() {
  const { t } = useTranslation();
  const me = useMe();
  const signOut = useSignOut();
  const summary = usePlatformSummary();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");

  const user = me.data?.user;
  const suspended = summary.data?.suspended ?? 0;
  const codesLeft = me.data?.two_factor_enabled ? me.data.recovery_codes_left : null;
  const badges: Partial<Record<string, number>> = {
    tenants: suspended > 0 ? suspended : undefined,
    security: codesLeft !== null && codesLeft <= 3 ? codesLeft : undefined,
  };

  function search(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    navigate(q ? `/empresas?q=${encodeURIComponent(q)}` : "/empresas");
    setMenuOpen(false);
  }

  const sidebar = (
    <nav aria-label={t("nav.main")} className={SIDEBAR_SURFACE}>
      <Link to="/resumen" className="px-1 pt-1">
        <BrandMark />
      </Link>

      <div className="rounded-2xl border border-white/12 bg-white/8 px-4 py-3">
        <p className="font-semibold">{t("nav.workspace")}</p>
        <p className="text-sm text-white/70">
          {summary.data
            ? t("nav.workspaceLine", {
                count: summary.data.total,
                plans: t("nav.plansCount", { count: summary.data.by_plan.length }),
              })
            : "—"}
        </p>
      </div>

      {GROUPS.map((group) => (
        <div key={group.label} className="flex flex-col gap-1">
          <p className="px-3 text-sm text-white/55">{t(group.label)}</p>
          {group.links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `flex min-h-11 items-center gap-3 rounded-2xl px-3 font-medium transition-colors focus-visible:outline-2 ${
                  isActive ? "metal" : "text-white/85 hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <Icon name={link.key} />
              <span className="flex-1">{t(`nav.${link.key}`)}</span>
              {badges[link.key] !== undefined && (
                <span className="rounded-full bg-white/90 px-2 text-xs font-semibold text-[var(--pf-ink)] tabular-nums">
                  {badges[link.key]}
                </span>
              )}
            </NavLink>
          ))}
        </div>
      ))}

      <div className="mt-auto flex flex-col gap-2 px-1 text-sm">
        <Link to={PLATFORM_TERMS_PATH} className="text-white/60 underline hover:text-white">
          {t("platformTerms.link")}
        </Link>
      </div>
    </nav>
  );

  return (
    <div className="platform min-h-screen">
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
              className="flex size-11 items-center justify-center rounded-2xl bg-white/70 lg:hidden"
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
                <span className="sr-only">{t("nav.searchLabel")}</span>
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={t("nav.searchPlaceholder")}
                  className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--pf-muted)]"
                />
              </label>
            </form>
            {user && (
              <div className="hidden items-center gap-3 sm:flex">
                <span
                  aria-hidden="true"
                  className="flex size-11 items-center justify-center rounded-full bg-[var(--pf-green-soft)] text-sm font-semibold text-[var(--pf-green-ink)]"
                >
                  {initials(user.full_name, user.email)}
                </span>
                <span className="hidden min-w-0 md:block">
                  <span className="block truncate text-sm font-semibold">
                    {user.full_name || user.email}
                  </span>
                  <span className="block truncate text-sm text-[var(--pf-muted)]">
                    {t("nav.roleSuperadmin")}
                  </span>
                </span>
              </div>
            )}
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
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

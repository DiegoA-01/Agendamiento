import { Suspense, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router-dom";
import type { Theme } from "../../shared/api/types";
import { LanguageSwitcher } from "../../shared/ui/LanguageSwitcher";
import { Button, Loading } from "../../shared/ui/primitives";
import { useMe } from "../auth/useMe";
import { useSignOut } from "../auth/useSignOut";
import { visibleLinks } from "./navigation";

function themeStyle(theme: Partial<Theme>): CSSProperties {
  return {
    "--color-primary": theme.primary,
    "--color-secondary": theme.secondary,
    "--color-background": theme.background,
    "--color-surface": theme.surface,
    "--color-text": theme.text,
  } as CSSProperties;
}

/** Marco del panel del negocio: aplica el tema, muestra el menú según rol y módulos, y deja el
 *  contenido de cada sección en el `Outlet`. Solo se usa dentro de `AuthGate`. */
export default function DashboardLayout() {
  const { t } = useTranslation();
  const me = useMe();
  const signOut = useSignOut();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!me.data) return null;
  const links = visibleLinks(me.data);

  return (
    <div
      style={themeStyle(me.data.theme)}
      className="min-h-screen bg-[var(--color-background,#f8fafc)] text-[var(--color-text,#0f172a)]"
    >
      <a
        href="#contenido"
        className="sr-only rounded bg-white px-3 py-2 focus:not-sr-only focus:absolute focus:top-2 focus:left-2"
      >
        {t("nav.skip")}
      </a>
      <header className="border-b border-black/10 bg-[var(--color-surface,#ffffff)]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="min-w-0 flex-1 truncate font-semibold">
            {me.data.tenant?.name ?? t("app.name")}
          </span>
          <Button
            variant="secondary"
            className="md:hidden"
            aria-expanded={menuOpen}
            aria-controls="menu-panel"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {t("dashboard.menu")}
          </Button>
          <div className="flex flex-wrap items-center gap-3">
            <LanguageSwitcher />
            <span className="hidden text-sm opacity-80 sm:inline">{me.data.user.full_name}</span>
            <Button
              variant="secondary"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
            >
              {t("nav.signOut")}
            </Button>
          </div>
        </div>
      </header>
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 md:flex-row">
        <nav
          id="menu-panel"
          aria-label={t("nav.main")}
          className={`${menuOpen ? "block" : "hidden"} md:block md:w-56 md:shrink-0`}
        >
          <ul className="flex flex-col gap-1">
            {links.map((link) => (
              <li key={link.section}>
                <NavLink
                  to={link.path}
                  onClick={() => setMenuOpen(false)}
                  className={({ isActive }) =>
                    `block rounded-lg border-l-4 px-3 py-2 text-sm font-medium ${
                      isActive
                        ? "border-[var(--color-primary,#0f172a)] bg-[var(--color-surface,#ffffff)] font-semibold"
                        : "border-transparent hover:bg-black/5"
                    }`
                  }
                >
                  {t(`dashboard.nav.${link.section}`)}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <main id="contenido" className="min-w-0 flex-1">
          <Suspense fallback={<Loading />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}

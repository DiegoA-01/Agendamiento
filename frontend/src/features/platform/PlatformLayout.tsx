import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../../shared/api/client";
import { LanguageSwitcher } from "../../shared/ui/LanguageSwitcher";
import { Button } from "../../shared/ui/primitives";
import { useMe } from "../auth/useMe";

const LINKS = [
  { to: "/empresas", label: "nav.tenants" },
  { to: "/planes", label: "nav.plans" },
  { to: "/auditoria", label: "nav.audit" },
] as const;

export function PlatformLayout() {
  const { t } = useTranslation();
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const signOut = useMutation({
    mutationFn: () => api<void>("/api/v1/auth/logout/", { method: "POST" }),
    onSuccess: () => {
      queryClient.clear();
      navigate("/login", { replace: true });
    },
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <a
        href="#contenido"
        className="sr-only rounded bg-white px-3 py-2 focus:not-sr-only focus:absolute focus:top-2 focus:left-2"
      >
        {t("nav.skip")}
      </a>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="font-semibold text-slate-900">
            {t("app.name")} · {t("nav.brand")}
          </span>
          <nav aria-label={t("nav.main")} className="flex flex-1 flex-wrap gap-1">
            {LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium ${
                    isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
                  }`
                }
              >
                {t(link.label)}
              </NavLink>
            ))}
          </nav>
          <div className="flex flex-wrap items-center gap-3">
            <LanguageSwitcher />
            {me.data && <span className="text-sm text-slate-600">{me.data.user.email}</span>}
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
      <main id="contenido" className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}

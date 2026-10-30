import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useMe } from "../features/auth/useMe";
import { api } from "../shared/api/client";
import { LanguageSwitcher } from "../shared/ui/LanguageSwitcher";
import { Badge, Button, Card } from "../shared/ui/primitives";

/** Marcador del panel del negocio (llega en M4+). Ya aplica el tema del negocio. */
export function DashboardPlaceholder() {
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

  if (!me.data) return null;
  const { theme, tenant, user, modules } = me.data;
  const style = {
    "--color-primary": theme.primary,
    "--color-secondary": theme.secondary,
    "--color-background": theme.background,
    "--color-surface": theme.surface,
    "--color-text": theme.text,
  } as CSSProperties;

  return (
    <div
      style={style}
      className="min-h-screen bg-[var(--color-background)] text-[var(--color-text)]"
    >
      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-10">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">{t("auth.panelTitle")}</h1>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <Button variant="secondary" onClick={() => signOut.mutate()}>
              {t("nav.signOut")}
            </Button>
          </div>
        </header>
        <Card className="flex flex-col gap-3 !bg-[var(--color-surface)]">
          <p>
            {t("auth.panelWelcome", {
              name: user.full_name,
              business: tenant?.name ?? "",
            })}
          </p>
          <div className="flex flex-wrap gap-2">
            {modules.map((key) => (
              <Badge key={key} tone="info">
                {t(`modules.${key}`)}
              </Badge>
            ))}
          </div>
          <p className="text-sm opacity-80">{t("auth.panelSoon")}</p>
        </Card>
      </main>
    </div>
  );
}

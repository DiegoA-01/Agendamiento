import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "../../shared/ui/LanguageSwitcher";
import { EmptyState } from "../../shared/ui/primitives";

/** Página pública vacía del esqueleto (Fase 0): la reserva y las páginas legales llegan en M6. */
export function PublicComingSoon({ pageKey, milestone }: { pageKey: string; milestone: string }) {
  const { t } = useTranslation();
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-10">
      <div className="flex items-center justify-between">
        <span className="font-semibold">{t("app.name")}</span>
        <LanguageSwitcher />
      </div>
      <h1 className="text-2xl font-semibold">{t(`booking.pages.${pageKey}.title`)}</h1>
      <EmptyState>{t("booking.comingSoon", { milestone })}</EmptyState>
    </main>
  );
}

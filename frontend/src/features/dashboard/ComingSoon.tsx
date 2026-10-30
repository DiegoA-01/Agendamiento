import { useTranslation } from "react-i18next";
import { EmptyState, PageHeader } from "../../shared/ui/primitives";
import type { DashboardSection } from "./navigation";

/** Pantalla provisional de una sección cuyo contenido llega en un hito posterior. */
export function ComingSoon({ section }: { section: DashboardSection }) {
  const { t } = useTranslation();
  return (
    <>
      <PageHeader title={t(`dashboard.nav.${section}`)} />
      <EmptyState>{t("dashboard.comingSoon")}</EmptyState>
    </>
  );
}

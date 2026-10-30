import { Suspense, lazy, type ComponentType } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";
import { EmptyState, Loading } from "../../shared/ui/primitives";
import { AuthGate } from "../auth/AuthGate";
import { useMe } from "../auth/useMe";
import { DASHBOARD_LINKS, canSee, visibleLinks, type DashboardSection } from "./navigation";

// El panel va en paquetes aparte: quien reserva desde el celular no descarga código del panel.
const DashboardLayout = lazy(() => import("./DashboardLayout"));

/** Una pantalla por sección, cada una en su carpeta (cada frente es dueño de las suyas). */
const PAGES: Record<DashboardSection, ComponentType> = {
  agenda: lazy(() => import("./agenda/AgendaPage")),
  appointments: lazy(() => import("./appointments/AppointmentsPage")),
  customers: lazy(() => import("./customers/CustomersPage")),
  services: lazy(() => import("./services/ServicesPage")),
  team: lazy(() => import("./team/TeamPage")),
  resources: lazy(() => import("./resources/ResourcesPage")),
  hours: lazy(() => import("./hours/HoursPage")),
  reports: lazy(() => import("./reports/ReportsPage")),
  company: lazy(() => import("./company/CompanyPage")),
};

/** Sesión obligatoria, tema del negocio y menú alrededor de todas las secciones. */
export function DashboardShell() {
  return (
    <AuthGate>
      <Suspense fallback={<Loading />}>
        <DashboardLayout />
      </Suspense>
    </AuthGate>
  );
}

/** Pantalla de una sección. Sin permiso vuelve al inicio del panel en lugar de mostrar un 403. */
export function SectionPage({ section }: { section: DashboardSection }) {
  const me = useMe();
  const link = DASHBOARD_LINKS.find((item) => item.section === section);
  if (!me.data || !link || !canSee(me.data, link)) return <Navigate to="/panel" replace />;
  const Page = PAGES[section];
  return <Page />;
}

/** `/panel` lleva a la primera sección que la persona puede ver. */
export function DashboardHome() {
  const { t } = useTranslation();
  const me = useMe();
  if (!me.data) return null;
  const [first] = visibleLinks(me.data);
  if (!first) return <EmptyState>{t("dashboard.noSections")}</EmptyState>;
  return <Navigate to={first.path} replace />;
}

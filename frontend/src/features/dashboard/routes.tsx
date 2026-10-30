import { Route } from "react-router-dom";
import { DashboardHome, DashboardShell, SectionPage } from "./DashboardShell";
import { DASHBOARD_LINKS } from "./navigation";

/** Rutas del panel del negocio (spec §13), para montar dentro de `<Routes>`. */
export function dashboardRoutes() {
  return (
    <Route element={<DashboardShell />}>
      <Route path="/panel" element={<DashboardHome />} />
      {DASHBOARD_LINKS.map(({ section, path }) => (
        <Route key={section} path={`${path}/*`} element={<SectionPage section={section} />} />
      ))}
    </Route>
  );
}

import { Navigate, Route, Routes } from "react-router-dom";
import { AuditPage } from "./AuditPage";
import { PlansPage } from "./PlansPage";
import { PlatformLayout } from "./PlatformLayout";
import { TenantCreatePage } from "./TenantCreatePage";
import { TenantDetailPage } from "./TenantDetailPage";
import { TenantsPage } from "./TenantsPage";

/** Todo el panel del Super Admin. Se carga en un paquete aparte (lazy) para que los clientes
 *  que reservan desde el celular no descarguen código de administración. */
export default function PlatformArea() {
  return (
    <Routes>
      <Route element={<PlatformLayout />}>
        <Route path="empresas" element={<TenantsPage />} />
        <Route path="empresas/nueva" element={<TenantCreatePage />} />
        <Route path="empresas/:id" element={<TenantDetailPage />} />
        <Route path="planes" element={<PlansPage />} />
        <Route path="auditoria" element={<AuditPage />} />
        <Route path="*" element={<Navigate to="/empresas" replace />} />
      </Route>
    </Routes>
  );
}

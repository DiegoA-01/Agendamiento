import { Route } from "react-router-dom";
import { PublicComingSoon } from "./PublicComingSoon";

/** Rutas públicas del host del negocio (spec §13). Son el esqueleto: el asistente de reserva, la
 *  gestión por enlace y los textos legales llegan en M6; con esto `App.tsx` ya no cambia. */
export const PUBLIC_PAGES = [
  { path: "/reservar", pageKey: "book" },
  { path: "/cita/:token", pageKey: "manage" },
  { path: "/terminos", pageKey: "terms" },
  { path: "/privacidad", pageKey: "privacy" },
  { path: "/cookies", pageKey: "cookies" },
] as const;

export function publicRoutes() {
  return PUBLIC_PAGES.map(({ path, pageKey }) => (
    <Route key={path} path={path} element={<PublicComingSoon pageKey={pageKey} milestone="M6" />} />
  ));
}

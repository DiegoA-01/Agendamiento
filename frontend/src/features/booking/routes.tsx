import { Route } from "react-router-dom";
import { PublicLayout } from "./PublicLayout";
import { PublicPage, type PublicPageKey } from "./PublicPage";

/** Rutas públicas del host del negocio (spec §13), dentro del marco con el tema del negocio. */
export const PUBLIC_PAGES: readonly { path: string; pageKey: PublicPageKey }[] = [
  { path: "/reservar", pageKey: "book" },
  { path: "/cita/:token", pageKey: "manage" },
  { path: "/terminos", pageKey: "terms" },
  { path: "/privacidad", pageKey: "privacy" },
  { path: "/cookies", pageKey: "cookies" },
];

export function publicRoutes() {
  return (
    <Route element={<PublicLayout />}>
      {PUBLIC_PAGES.map(({ path, pageKey }) => (
        <Route key={path} path={path} element={<PublicPage pageKey={pageKey} />} />
      ))}
    </Route>
  );
}

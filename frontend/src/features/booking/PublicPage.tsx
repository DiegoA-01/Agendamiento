import { lazy, Suspense } from "react";
import { Loading } from "../../shared/ui/primitives";

// Cada página en su paquete: quien entra a reservar desde el celular descarga solo esa.
const BookPage = lazy(() => import("./BookPage"));
const ManagePage = lazy(() => import("./ManagePage"));
const LegalPage = lazy(() => import("./LegalPage"));

export type PublicPageKey = "book" | "manage" | "terms" | "privacy" | "cookies";

export function PublicPage({ pageKey }: { pageKey: PublicPageKey }) {
  return (
    <Suspense fallback={<Loading />}>
      {pageKey === "book" ? (
        <BookPage />
      ) : pageKey === "manage" ? (
        <ManagePage />
      ) : (
        <LegalPage page={pageKey} />
      )}
    </Suspense>
  );
}

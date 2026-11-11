import { lazy, Suspense } from "react";
import { Loading } from "../../shared/ui/primitives";
import { BookingDialog } from "./BookingDialog";

// Cada página en su paquete: quien entra a reservar desde el celular descarga solo esa.
const BookPage = lazy(() => import("./BookPage"));
const LandingPage = lazy(() => import("./LandingPage"));
const ManagePage = lazy(() => import("./ManagePage"));
const LegalPage = lazy(() => import("./LegalPage"));

export type PublicPageKey = "book" | "manage" | "terms" | "privacy" | "cookies";

// Igual a `BOOKING_TITLE_ID` de BookPage; se repite para no cargar ese paquete antes de tiempo.
const BOOKING_TITLE_ID = "booking-title";

export function PublicPage({ pageKey }: { pageKey: PublicPageKey }) {
  if (pageKey === "book") {
    // R9: la reserva es una ventana encima de la portada; al cerrarla se queda la portada.
    return (
      <Suspense fallback={<Loading />}>
        <LandingPage />
        <BookingDialog labelledBy={BOOKING_TITLE_ID}>
          <Suspense fallback={<Loading />}>
            <BookPage />
          </Suspense>
        </BookingDialog>
      </Suspense>
    );
  }
  return (
    <Suspense fallback={<Loading />}>
      {pageKey === "manage" ? <ManagePage /> : <LegalPage page={pageKey} />}
    </Suspense>
  );
}

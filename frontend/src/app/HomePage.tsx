import { lazy, Suspense } from "react";
import { PublicLayout } from "../features/booking/PublicLayout";
import { Loading } from "../shared/ui/primitives";

const LandingPage = lazy(() => import("../features/booking/LandingPage"));

/** Portada del host de un negocio: su página pública con el botón de reservar (spec §13). */
export function HomePage() {
  return (
    <PublicLayout>
      <Suspense fallback={<Loading />}>
        <LandingPage />
      </Suspense>
    </PublicLayout>
  );
}

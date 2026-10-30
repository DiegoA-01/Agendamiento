import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthGate } from "../features/auth/AuthGate";
import { ChangePasswordPage } from "../features/auth/ChangePasswordPage";
import { LoginPage } from "../features/auth/LoginPage";
import { ForgotPasswordPage, ResetPasswordPage } from "../features/auth/RecoverPages";
import { isPlatformHost } from "../shared/host";
import { Loading } from "../shared/ui/primitives";
import { DashboardPlaceholder } from "./DashboardPlaceholder";
import { HomePage } from "./HomePage";

// El panel del Super Admin es un paquete aparte: solo lo descarga quien entra a admin.<dominio>.
const PlatformArea = lazy(() => import("../features/platform/PlatformArea"));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

function accountRoutes() {
  return (
    <>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/recuperar" element={<ForgotPasswordPage />} />
      <Route path="/recuperar/confirmar" element={<ResetPasswordPage />} />
      <Route
        path="/cambiar-clave"
        element={
          <AuthGate allowMustChange>
            <ChangePasswordPage />
          </AuthGate>
        }
      />
    </>
  );
}

function AppRoutes() {
  // En admin.<dominio> vive el panel del Super Admin; en cualquier otro host, un negocio.
  if (isPlatformHost()) {
    return (
      <Routes>
        {accountRoutes()}
        <Route
          path="/*"
          element={
            <AuthGate platform>
              <Suspense fallback={<Loading />}>
                <PlatformArea />
              </Suspense>
            </AuthGate>
          }
        />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      {accountRoutes()}
      <Route
        path="/panel"
        element={
          <AuthGate>
            <DashboardPlaceholder />
          </AuthGate>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

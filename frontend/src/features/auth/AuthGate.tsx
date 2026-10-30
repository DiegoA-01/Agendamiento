import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";
import { ApiError } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import { ErrorBox, Loading } from "../../shared/ui/primitives";
import { useMe } from "./useMe";

interface AuthGateProps {
  children: ReactNode;
  /** Solo el Super Admin (panel de la plataforma). */
  platform?: boolean;
  /** La pantalla de cambio de contraseña es la única que no redirige a sí misma. */
  allowMustChange?: boolean;
}

/** Protege una pantalla: sin sesión va al login; con contraseña temporal, al cambio forzado. */
export function AuthGate({ children, platform = false, allowMustChange = false }: AuthGateProps) {
  const { t } = useTranslation();
  const me = useMe();

  if (me.isPending) return <Loading />;
  if (me.isError) {
    const unauthenticated = me.error instanceof ApiError && me.error.status === 401;
    if (unauthenticated) return <Navigate to="/login" replace />;
    return <ErrorBox message={describeError(t, me.error)} onRetry={() => void me.refetch()} />;
  }
  if (me.data.must_change_password && !allowMustChange) {
    return <Navigate to="/cambiar-clave" replace />;
  }
  if (platform && !me.data.is_platform_admin) return <Navigate to="/login" replace />;
  return children;
}

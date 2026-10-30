import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../../shared/api/client";

/** Cierra la sesión, olvida los datos en caché y vuelve al login. */
export function useSignOut() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("/api/v1/auth/logout/", { method: "POST" }),
    onSuccess: () => {
      queryClient.clear();
      navigate("/login", { replace: true });
    },
  });
}

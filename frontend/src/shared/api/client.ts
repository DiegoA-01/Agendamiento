export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    detail: string,
  ) {
    super(detail);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
    credentials: "same-origin",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.code ?? "error", body.detail ?? response.statusText);
  }
  return response.json() as Promise<T>;
}

export interface Health {
  status: "ok" | "degraded";
  checks: Record<string, "ok" | "fail">;
}

export const fetchHealth = () => api<Health>("/healthz/");

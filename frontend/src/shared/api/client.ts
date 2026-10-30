export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    detail: string,
    public fields: Record<string, string[]> = {},
  ) {
    super(detail);
  }
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const CSRF_COOKIE = "csrftoken";

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const entry = document.cookie.split("; ").find((row) => row.startsWith(`${name}=`));
  return entry ? decodeURIComponent(entry.slice(name.length + 1)) : null;
}

/** El token CSRF vive en una cookie. Django lo rota al iniciar sesión, por eso se lee en cada
 *  petición y nunca se guarda en memoria. Si no hay cookie todavía, se pide una. */
async function csrfToken(): Promise<string | null> {
  const existing = readCookie(CSRF_COOKIE);
  if (existing) return existing;
  await fetch("/api/v1/auth/csrf/", { credentials: "same-origin" });
  return readCookie(CSRF_COOKIE);
}

interface RequestOptions {
  method?: string;
  body?: unknown;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (!SAFE_METHODS.has(method)) {
    const token = await csrfToken();
    if (token) headers["X-CSRFToken"] = token;
  }

  const response = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (response.status === 204) return undefined as T;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      data?.code ?? "unknown",
      data?.detail ?? response.statusText,
      data?.fields ?? {},
    );
  }
  return data as T;
}

export interface Health {
  status: "ok" | "degraded";
  checks: Record<string, "ok" | "fail">;
}

export const fetchHealth = () => api<Health>("/healthz/");

/** Las listas paginadas devuelven la URL completa de la página siguiente; solo hace falta su
 *  cursor, porque las peticiones van siempre al mismo origen. */
export function cursorFrom(nextUrl: string | null): string | undefined {
  if (!nextUrl) return undefined;
  return new URL(nextUrl, "http://placeholder.invalid").searchParams.get("cursor") ?? undefined;
}

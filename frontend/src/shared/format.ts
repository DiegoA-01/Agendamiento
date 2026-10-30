export function formatDateTime(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  );
}

export function formatDate(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(iso));
}

/** Dominio base del panel: `admin.localhost:8080` → `localhost:8080`. */
export function baseDomainFrom(host: string): string {
  return host.replace(/^admin\./i, "");
}

/** Dirección pública de un negocio a partir de su subdominio. */
export function tenantUrl(slug: string, location: Pick<Location, "protocol" | "host">): string {
  return `${location.protocol}//${slug}.${baseDomainFrom(location.host)}`;
}

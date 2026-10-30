/** El panel del Super Admin vive en `admin.<dominio>`; cualquier otro host es de un negocio. */
export function isPlatformHost(hostname: string = window.location.hostname): boolean {
  return hostname.toLowerCase().startsWith("admin.");
}

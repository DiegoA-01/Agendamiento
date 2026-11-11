/** Porcentaje entero de `count` sobre `total` (0 si no hay negocios), para las barras del resumen. */
export function share(count: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((count / total) * 100);
}

/** Meses del resumen del Inicio, en días locales del negocio (`YYYY-MM-DD`). */

/** `YYYY-MM` de los últimos `count` meses, del más viejo al actual. */
export function lastMonths(today: string, count: number): string[] {
  const [year, month] = today.split("-").map(Number);
  return Array.from({ length: count }, (_, index) => {
    const offset = month - 1 - (count - 1 - index);
    const y = year + Math.floor(offset / 12);
    const m = ((offset % 12) + 12) % 12;
    return `${y}-${String(m + 1).padStart(2, "0")}`;
  });
}

/** Ventas por mes con los meses sin ventas en cero, para que la gráfica no salte meses. */
export function fillMonths(
  months: string[],
  rows: { key: string; sales: string }[],
): { month: string; sales: number }[] {
  const byMonth = new Map(rows.map((row) => [row.key.slice(0, 7), Number(row.sales)]));
  return months.map((month) => ({ month, sales: byMonth.get(month) ?? 0 }));
}

/** Cambio porcentual redondeado, o `null` si no hay base para comparar. */
export function percentChange(current: number, previous: number): number | null {
  if (previous <= 0) return null;
  return Math.round(((current - previous) / previous) * 1000) / 10;
}

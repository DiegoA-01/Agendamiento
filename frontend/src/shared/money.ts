/** Formatea un monto que llega como texto decimal (`"30000.00"`) en la moneda del negocio. Solo
 *  para mostrar: los montos se envían a la API como texto, nunca como número. */
export function formatMoney(value: string, currency: string, locale: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;
  const fractionDigits = Number.isInteger(amount) ? 0 : 2;
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: 2,
  }).format(amount);
}

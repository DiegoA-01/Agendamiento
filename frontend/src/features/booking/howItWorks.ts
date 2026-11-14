import type { PublicCategory, PublicService } from "../../shared/api/types";

/** Pantallas del celular de la portada: los tres pasos de la reserva (R9) y la confirmación. */
export const DEMO_STEPS = ["services", "schedule", "details", "done"] as const;
export type DemoStep = (typeof DEMO_STEPS)[number];

/** Tiempo que se queda cada pantalla antes de pasar sola a la siguiente. */
export const DEMO_INTERVAL_MS = 4000;

/** Índice de la pantalla siguiente; después de la confirmación vuelve a empezar. */
export function nextDemoStep(index: number): number {
  return (index + 1) % DEMO_STEPS.length;
}

/** Los primeros servicios del negocio para mostrar en el celular (sin pedir nada extra a la API). */
export function demoServices(categories: PublicCategory[] | undefined, limit = 3): PublicService[] {
  return (categories ?? []).flatMap((category) => category.services).slice(0, limit);
}

/** Los próximos días (YYYY-MM-DD) desde `today`, para la fila de días del celular. */
export function nextDays(today: string, count: number): string[] {
  const start = new Date(`${today}T12:00:00Z`);
  return Array.from({ length: count }, (_, offset) => {
    const day = new Date(start);
    day.setUTCDate(start.getUTCDate() + offset);
    return day.toISOString().slice(0, 10);
  });
}

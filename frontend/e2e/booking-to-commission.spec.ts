import { type Page, expect, test } from "@playwright/test";

/** Criterio de aceptación de M10 (spec §14): reservar → completar → comisión.
 *
 *  1. Un cliente abre la reserva desde la portada (una ventana de 3 pasos, R9) sin cuenta.
 *  2. El dueño entra al panel, encuentra la cita en `/citas`, la inicia y la completa.
 *  3. La comisión aparece en `/reportes`.
 */

const SERVICE = "Corte clásico";

function businessUrl(path: string): string {
  return `http://${process.env.E2E_SLUG}.localhost:8080${path}`;
}

async function dismissCookies(page: Page) {
  const banner = page.getByRole("button", { name: "Entendido" });
  if (await banner.isVisible().catch(() => false)) await banner.click();
}

async function next(page: Page) {
  await page.getByRole("button", { name: "Continuar" }).click();
}

test("un cliente reserva, el dueño completa la cita y ve la comisión", async ({ page }) => {
  const customer = `Cliente E2E ${Date.now().toString(36)}`;

  // --- 1. Reserva pública ---------------------------------------------------------------------
  // El aviso de cookies se cierra antes de abrir la ventana: con ella abierta, el fondo no recibe
  // clics.
  await page.goto(businessUrl("/"));
  await dismissCookies(page);
  await page.getByRole("link", { name: "Reservar cita" }).click();
  const booking = page.getByRole("dialog", { name: "¿Qué te quieres hacer?" });
  await expect(booking).toBeVisible();

  // El nombre del botón de elegir empieza por el servicio; el de "Ver el detalle de …" no.
  await page.getByRole("button", { name: new RegExp(`^${SERVICE}`) }).click();
  await next(page);

  const professionalButton = page
    .getByRole("button", { pressed: false })
    .filter({ hasNotText: "Cualquiera" })
    .filter({ has: page.locator("span.font-medium") })
    .first();
  const professional = (
    await professionalButton.locator("span.font-medium").first().innerText()
  ).trim();
  await professionalButton.click();

  // Día y hora van en el mismo paso que el profesional (R9).
  // Primer día disponible; si el mes ya no tiene, el siguiente.
  const available = page.getByRole("button", { name: /: Disponible$/ });
  await expect(page.getByRole("list", { name: "Convenciones del calendario" })).toBeVisible();
  if ((await available.count()) === 0) {
    await page.getByRole("button", { name: "Mes siguiente" }).click();
    await expect(available.first()).toBeVisible();
  }
  await available.first().click();

  await page
    .getByRole("button", { name: /^\d{1,2}:\d{2}/ })
    .first()
    .click();
  await next(page);

  await page.getByLabel("Nombre completo").fill(customer);
  await page.getByLabel("Celular").fill("300 555 0101");
  await page.getByLabel("Correo").fill("cliente.e2e@example.com");
  await page.getByLabel(/Autorizo el tratamiento de mis datos/).check();

  const created = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/public/appointments/") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirmar reserva" }).click();
  const response = await created;
  expect(response.status()).toBe(201);
  const booked = (await response.json()) as { start_at: string };
  const day = booked.start_at.slice(0, 10); // fecha local del negocio (lleva el desfase)
  await expect(page.getByText("¡Listo, tu cita está reservada!")).toBeVisible();

  // --- 2. El dueño completa la cita -----------------------------------------------------------
  await page.goto(businessUrl("/login"));
  await page.getByLabel("Correo").fill(process.env.E2E_OWNER_EMAIL!);
  await page.getByLabel("Contraseña").fill(process.env.E2E_OWNER_PASSWORD!);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).not.toHaveURL(/\/login/);

  await page.goto(businessUrl("/citas"));
  await page.getByLabel("Desde").fill(day);
  await page.getByLabel("Hasta").fill(day);
  // Cada acción cierra el detalle y la tarjeta muestra el estado nuevo: se vuelve a abrir.
  const card = page.getByRole("button", { name: new RegExp(customer) });
  await card.click();
  await page.getByRole("button", { name: "Iniciar" }).click();
  await expect(card).toContainText("En curso");
  await card.click();
  await page.getByRole("button", { name: "Completar" }).click();
  await expect(card).toContainText("Completada");

  // --- 3. La comisión aparece en los reportes -------------------------------------------------
  await page.goto(businessUrl("/reportes"));
  await page.getByLabel("Desde").fill(day);
  await page.getByLabel("Hasta").fill(day);
  await page.getByRole("tab", { name: "Comisiones" }).click();

  const row = page.getByRole("row").filter({ hasText: SERVICE }).filter({ hasText: professional });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText("COP");

  await page.getByRole("tab", { name: "Ventas" }).click();
  // Tarjeta "Citas" del resumen de ventas: la cita completada cuenta.
  const appointmentsCard = page
    .locator("section")
    .filter({ has: page.getByText("Citas", { exact: true }) })
    .filter({ hasNotText: "Ventas" });
  await expect(appointmentsCard).toHaveText(/Citas\s*1$/);
});

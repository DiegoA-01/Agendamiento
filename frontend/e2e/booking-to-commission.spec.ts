import { type Page, expect, test } from "@playwright/test";

/** Criterio de aceptación de M10 (spec §14): reservar → completar → comisión.
 *
 *  1. Un cliente reserva en `/reservar` sin cuenta.
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
  await page.goto(businessUrl("/reservar"));
  await dismissCookies(page);

  await page.getByRole("button", { name: new RegExp(SERVICE) }).click();
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
  await next(page);

  // Primer día disponible; si el mes ya no tiene, el siguiente.
  const available = page.getByRole("button", { name: /: Disponible$/ });
  await expect(page.getByRole("list", { name: "Convenciones del calendario" })).toBeVisible();
  if ((await available.count()) === 0) {
    await page.getByRole("button", { name: "Mes siguiente" }).click();
    await expect(available.first()).toBeVisible();
  }
  await available.first().click();
  await next(page);

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
  const booking = (await response.json()) as { start_at: string };
  const day = booking.start_at.slice(0, 10); // fecha local del negocio (lleva el desfase)
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
  await page.getByRole("button", { name: new RegExp(customer) }).click();

  await page.getByRole("button", { name: "Iniciar" }).click();
  await expect(page.getByRole("button", { name: "Completar" })).toBeVisible();
  await page.getByRole("button", { name: "Completar" }).click();
  await expect(page.getByText("Completada").first()).toBeVisible();

  // --- 3. La comisión aparece en los reportes -------------------------------------------------
  await page.goto(businessUrl("/reportes"));
  await page.getByLabel("Desde").fill(day);
  await page.getByLabel("Hasta").fill(day);
  await page.getByRole("tab", { name: "Comisiones" }).click();

  const row = page.getByRole("row").filter({ hasText: SERVICE }).filter({ hasText: professional });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText("COP");

  await page.getByRole("tab", { name: "Ventas" }).click();
  await expect(page.getByText("Citas", { exact: true }).locator("..")).toContainText("1");
});

import { execSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";

/** Crea un negocio nuevo para esta corrida con `seed_demo` (todos los módulos, 3 profesionales,
 *  horario de lunes a sábado de 9 a 19). Un subdominio distinto en cada corrida evita choques
 *  con datos de corridas anteriores.
 *
 *  `E2E_SEED_CMD` permite cambiar cómo se llama al backend (por defecto, Docker Compose). */
export default function globalSetup() {
  const slug = `e2e-${Date.now().toString(36)}`;
  const password = `E2e-${randomBytes(9).toString("base64url")}!`;
  const command =
    process.env.E2E_SEED_CMD ?? "docker compose exec -T api python manage.py seed_demo";
  execSync(`${command} --slug ${slug} --password ${password}`, {
    cwd: fileURLToPath(new URL("../..", import.meta.url)),
    stdio: "pipe",
  });
  process.env.E2E_SLUG = slug;
  process.env.E2E_OWNER_EMAIL = `propietario@${slug}.test`;
  process.env.E2E_OWNER_PASSWORD = password;
}

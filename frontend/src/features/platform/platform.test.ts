import { describe, expect, it } from "vitest";
import i18n from "../../shared/i18n";
import { ApiError } from "../../shared/api/client";
import { applyServerErrors, describeError, fieldMessage } from "../../shared/api/errors";
import { isPlatformHost } from "../../shared/host";
import { contrastRatio, isHexColor, MIN_TEXT_CONTRAST } from "./contrast";
import {
  changePasswordSchema,
  domainSchema,
  planSchema,
  tenantCreateSchema,
  themeSchema,
} from "./schemas";

const t = i18n.t.bind(i18n);

const validTenant = {
  name: "Barbería El Filo",
  slug: "elfilo",
  plan_id: "00000000-0000-0000-0000-000000000001",
  vertical: "barbershop",
  timezone: "America/Bogota",
  currency: "COP",
  language: "es",
  owner_name: "Diego Dueño",
  owner_email: "dueno@elfilo.com",
} as const;

function firstMessage(result: { success: boolean; error?: { issues: { message: string }[] } }) {
  return result.success ? null : result.error?.issues[0]?.message;
}

describe("contraste (debe coincidir con el backend)", () => {
  it("da los valores de referencia de WCAG", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrastRatio("#ffffff", "#ffffff")).toBeCloseTo(1, 5);
    expect(contrastRatio("#767676", "#ffffff")).toBeCloseTo(4.54, 2);
    expect(contrastRatio("#ffffff", "#000000")).toBe(contrastRatio("#000000", "#ffffff"));
  });

  it("el gris claro sobre blanco no llega al mínimo", () => {
    expect(contrastRatio("#cccccc", "#ffffff")).toBeLessThan(MIN_TEXT_CONTRAST);
  });

  it("solo acepta colores de 6 dígitos", () => {
    expect(isHexColor("#1f2937")).toBe(true);
    expect(isHexColor("#FFF")).toBe(false);
    expect(isHexColor("rojo")).toBe(false);
  });
});

describe("validaciones de formularios", () => {
  it("acepta una empresa válida y normaliza el subdominio", () => {
    const result = tenantCreateSchema.safeParse({ ...validTenant, slug: "  ElFilo " });
    expect(result.success && result.data.slug).toBe("elfilo");
  });

  it.each([
    [{ slug: "admin" }, "slugReserved"],
    [{ slug: "con espacios" }, "slugFormat"],
    [{ slug: "-guion" }, "slugFormat"],
    [{ name: " " }, "required"],
    [{ currency: "PESOS" }, "currencyFormat"],
    [{ owner_email: "no-es-correo" }, "emailFormat"],
    [{ plan_id: "" }, "required"],
  ])("rechaza %j con el mensaje %s", (change, message) => {
    expect(firstMessage(tenantCreateSchema.safeParse({ ...validTenant, ...change }))).toBe(message);
  });

  it("valida el tema color por color", () => {
    const good = {
      primary: "#0f766e",
      secondary: "#b45309",
      background: "#ffffff",
      surface: "#f0fdfa",
      text: "#0f172a",
    };
    expect(themeSchema.safeParse(good).success).toBe(true);
    expect(firstMessage(themeSchema.safeParse({ ...good, text: "negro" }))).toBe("hexFormat");
  });

  it("valida dominios propios", () => {
    expect(domainSchema.safeParse({ host: " WWW.ElFilo.com " }).success).toBe(true);
    for (const host of ["sinpunto", "https://www.elfilo.com", "no es host"]) {
      expect(firstMessage(domainSchema.safeParse({ host }))).toBe("hostFormat");
    }
  });

  it("valida los límites del plan", () => {
    const plan = {
      name: "Pro",
      modules: ["booking"],
      max_professionals: 5,
      max_locations: 1,
      apply_to_tenants: false,
    };
    expect(planSchema.safeParse(plan).success).toBe(true);
    expect(firstMessage(planSchema.safeParse({ ...plan, max_locations: 0 }))).toBe("min1");
    expect(planSchema.safeParse({ ...plan, modules: ["teletransporte"] }).success).toBe(false);
  });

  it("exige contraseña nueva larga y repetida igual", () => {
    const base = { current_password: "x", new_password: "una-clave-larga-1", repeat_password: "" };
    expect(firstMessage(changePasswordSchema.safeParse({ ...base, new_password: "corta" }))).toBe(
      "passwordMin",
    );
    expect(firstMessage(changePasswordSchema.safeParse({ ...base, repeat_password: "otra" }))).toBe(
      "passwordsMismatch",
    );
    expect(
      changePasswordSchema.safeParse({ ...base, repeat_password: base.new_password }).success,
    ).toBe(true);
  });
});

describe("mensajes de error", () => {
  // Códigos que puede devolver el backend: todos deben tener texto en los dos idiomas.
  const backendCodes = [
    "invalid_credentials",
    "two_factor_required",
    "invalid_two_factor_code",
    "two_factor_setup_required",
    "two_factor_already_enabled",
    "two_factor_setup_not_started",
    "weak_password",
    "invalid_current_password",
    "invalid_reset_token",
    "unknown_host",
    "tenant_suspended",
    "not_found",
    "not_authenticated",
    "permission_denied",
    "validation_error",
    "invalid_theme",
    "low_contrast",
    "plan_in_use",
    "host_taken",
    "invalid_host",
    "reserved_host",
    "cannot_delete_subdomain",
    "dns_lookup_failed",
    "module_disabled",
  ];
  const zodKeys = [
    "required",
    "emailFormat",
    "hexFormat",
    "slugFormat",
    "slugReserved",
    "currencyFormat",
    "hostFormat",
    "min1",
    "passwordMin",
    "passwordsMismatch",
  ];

  it.each(["es", "en"])("cada código del backend tiene texto en %s", async (language) => {
    await i18n.changeLanguage(language);
    for (const code of backendCodes) {
      const text = describeError(t, new ApiError(400, code, ""));
      expect(text, code).not.toBe(t("errors.unknown"));
    }
    await i18n.changeLanguage("es");
  });

  it.each(["es", "en"])("cada mensaje de validación tiene texto en %s", async (language) => {
    await i18n.changeLanguage(language);
    for (const key of zodKeys) expect(fieldMessage(t, key), key).not.toBe(key);
    await i18n.changeLanguage("es");
  });

  it("un código desconocido o un error raro usa el mensaje genérico", () => {
    expect(describeError(t, new ApiError(500, "inventado", ""))).toBe(t("errors.unknown"));
    expect(describeError(t, new Error("boom"))).toBe(t("errors.unknown"));
  });

  it("el texto escrito por el servidor pasa tal cual", () => {
    expect(fieldMessage(t, "Ese subdominio ya existe")).toBe("Ese subdominio ya existe");
    expect(fieldMessage(t, undefined)).toBeUndefined();
  });

  it("marca solo los campos del formulario que el servidor rechazó", () => {
    const marked: Record<string, string | undefined> = {};
    const setError = (name: string, error: { message?: string }) => {
      marked[name] = error.message;
    };
    const error = new ApiError(400, "validation_error", "", {
      slug: ["Reservado", "Otro"],
      plan_id: ["No existe"],
      ajeno: ["ignorar"],
    });
    const result = applyServerErrors(error, setError as never, ["slug", "plan_id"]);
    expect(result).toBe(true);
    expect(marked).toEqual({ slug: "Reservado Otro", plan_id: "No existe" });
    expect(applyServerErrors(new Error("x"), setError as never, ["slug"])).toBe(false);
  });
});

describe("host del panel", () => {
  it("el panel del Super Admin vive en admin.*", () => {
    expect(isPlatformHost("admin.localhost")).toBe(true);
    expect(isPlatformHost("ADMIN.tudominio.com")).toBe(true);
    expect(isPlatformHost("elfilo.localhost")).toBe(false);
    expect(isPlatformHost("administracion.com")).toBe(false);
  });
});

describe("plurales", () => {
  it.each([
    ["es", 1, "1 sede"],
    ["es", 3, "3 sedes"],
    ["en", 1, "1 location"],
    ["en", 2, "2 locations"],
  ])("en %s, %i da '%s'", async (language, count, expected) => {
    await i18n.changeLanguage(language);
    expect(i18n.t("plans.locationsShort", { count })).toBe(expected);
    await i18n.changeLanguage("es");
  });
});

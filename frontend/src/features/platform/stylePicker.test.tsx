import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToString } from "react-dom/server";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it } from "vitest";
import type { TenantDetail } from "../../shared/api/types";
import i18n from "../../shared/i18n";
import { StylePicker } from "./StylePicker";

function render(publicStyle: TenantDetail["public_style"]) {
  const tenant = { id: "t1", slug: "demo", public_style: publicStyle } as TenantDetail;
  return renderToString(
    <QueryClientProvider client={new QueryClient()}>
      <I18nextProvider i18n={i18n}>
        <StylePicker tenant={tenant} />
      </I18nextProvider>
    </QueryClientProvider>,
  );
}

describe("selector de estilo de la reserva", () => {
  it("marca como elegido y guardado el estilo actual del negocio", () => {
    const html = render("barbershop");
    const checked = html.match(/role="radio" aria-checked="true"[^>]*>/g) ?? [];
    expect(checked).toHaveLength(1);
    expect(checked[0]).toContain("style-option-on");
    const saved = html.split("Guardado").length - 1;
    expect(saved).toBe(1);
    expect(html.indexOf("Barbería clásica")).toBeLessThan(html.indexOf("Guardado"));
  });

  it("con automático guardado, la opción automática es la elegida", () => {
    const html = render("");
    expect(html).toMatch(/aria-checked="true"[^>]*style-option-on[\s\S]*Automático/);
  });
});

import { renderToString } from "react-dom/server";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it } from "vitest";
import i18n from "../i18n";
import { TextField } from "./primitives";

function render(type: string) {
  return renderToString(
    <I18nextProvider i18n={i18n}>
      <TextField label="Contraseña" type={type} />
    </I18nextProvider>,
  );
}

describe("campo de contraseña", () => {
  it("trae el botón del ojo para mostrar la contraseña, oculta al empezar", () => {
    const html = render("password");
    expect(html).toContain('type="password"');
    expect(html).toContain('aria-label="Mostrar contraseña"');
    expect(html).toContain('aria-pressed="false"');
  });

  it("los demás campos no traen el ojo", () => {
    expect(render("email")).not.toContain("Mostrar contraseña");
  });
});

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const KEY = "cookie_notice";

function alreadySeen(): boolean {
  try {
    return globalThis.localStorage?.getItem(KEY) === "seen";
  } catch {
    return false;
  }
}

/** Aviso de cookies. La reserva solo usa cookies necesarias (seguridad del formulario) y guarda el
 *  idioma elegido; no hay cookies de publicidad ni de analítica, así que no hay nada que aceptar o
 *  rechazar: es un aviso informativo con enlace a la política del negocio. */
export function CookieBanner() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(() => !alreadySeen());
  if (!visible) return null;

  return (
    <div
      role="region"
      aria-label={t("booking.cookies.label")}
      className="fixed inset-x-0 bottom-0 z-20 border-t border-[var(--bk-line)] bg-[var(--color-surface)] p-4 text-[var(--color-text)]"
    >
      <div className="mx-auto flex max-w-2xl flex-col gap-3 text-sm sm:flex-row sm:items-center">
        <p className="flex-1">
          {t("booking.cookies.text")}{" "}
          <Link to="/cookies" className="font-medium underline">
            {t("booking.pages.cookies.title")}
          </Link>
        </p>
        <button
          type="button"
          className="min-h-11 rounded-2xl bg-[var(--color-primary)] px-5 font-semibold text-[var(--color-background)] focus-visible:outline-2"
          onClick={() => {
            try {
              globalThis.localStorage?.setItem(KEY, "seen");
            } catch {
              // sin almacenamiento: el aviso vuelve a salir en la próxima visita
            }
            setVisible(false);
          }}
        >
          {t("booking.cookies.ok")}
        </button>
      </div>
    </div>
  );
}

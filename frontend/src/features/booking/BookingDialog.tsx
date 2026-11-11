import { useEffect, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

/** Ventana de la reserva (mejora R9): se abre sobre la portada del negocio y ocupa toda la
 *  pantalla en el celular. Usa `<dialog>` nativo, como el detalle del servicio: el navegador
 *  maneja el foco y la tecla Escape. Al cerrarla se vuelve a la portada. */
export function BookingDialog({
  labelledBy,
  children,
}: {
  labelledBy: string;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dialog = useRef<HTMLDialogElement>(null);

  // Sin `close()` en la limpieza: dispararía `onClose` y la navegación al desmontar (ver
  // ServiceDetail). Quitar el elemento ya la oculta.
  useEffect(() => {
    const element = dialog.current;
    if (element && !element.open) element.showModal();
  }, []);

  // La página de fondo no se desplaza mientras la ventana está abierta.
  useEffect(() => {
    const root = document.documentElement;
    const previous = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = previous;
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-labelledby={labelledBy}
      onClose={() => navigate("/")}
      className="m-0 h-dvh max-h-none flex-col open:flex w-full max-w-none overflow-y-auto bg-[var(--color-background,#f8fafc)] p-0 text-[var(--color-text,#0f172a)] shadow-xl backdrop:bg-black/50 sm:m-auto sm:h-auto sm:max-h-[90dvh] sm:max-w-2xl sm:rounded-2xl"
    >
      <div className="flex justify-end px-2 pt-2">
        <button
          type="button"
          aria-label={t("booking.wizard.closeBooking")}
          onClick={() => dialog.current?.close()}
          className="flex size-10 items-center justify-center rounded-full text-2xl leading-none hover:bg-black/10 focus-visible:outline-2"
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>
      <div className="flex flex-1 flex-col px-4">{children}</div>
    </dialog>
  );
}

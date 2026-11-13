import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "./primitives";

function WarningIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="size-6 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 4 2.8 19.5h18.4z" />
      <path d="M12 10v4.5M12 17.2v.1" />
    </svg>
  );
}

/** Botón de una acción de riesgo (eliminar, quitar, suspender) que siempre pregunta antes en una
 *  ventana propia: título, qué pasa y dos botones. Usa `<dialog>` nativo: el navegador maneja el
 *  foco y la tecla Escape, que equivale a "Cancelar". */
export function ConfirmAction({
  label,
  title,
  message,
  confirmLabel,
  onConfirm,
  disabled = false,
  pending = false,
}: {
  label: string;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  disabled?: boolean;
  pending?: boolean;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button variant="danger" disabled={disabled || pending} onClick={() => setOpen(true)}>
        {label}
      </Button>
      {open && (
        <ConfirmDialog
          title={title}
          message={message}
          confirmLabel={confirmLabel}
          onCancel={() => setOpen(false)}
          onConfirm={() => {
            setOpen(false);
            onConfirm();
          }}
        />
      )}
      {pending && <span className="sr-only">{t("common.saving")}</span>}
    </>
  );
}

function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onCancel,
  onConfirm,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const { t } = useTranslation();
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);

  // Sin `close()` en la limpieza: dispararía `onClose` al desmontar (ver ServiceDetail).
  useEffect(() => {
    const element = dialog.current;
    if (element && !element.open) element.showModal();
    // Lo seguro primero: el foco empieza en "Cancelar".
    cancel.current?.focus();
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-labelledby="confirm-title"
      aria-describedby="confirm-message"
      onClose={onCancel}
      className="confirm-dialog m-auto w-[calc(100%-2rem)] max-w-md rounded-3xl border border-white/80 bg-white/90 p-0 text-[#0b0d0c] backdrop:bg-black/45 backdrop:backdrop-blur-[2px]"
    >
      <div className="flex flex-col gap-4 p-6">
        <div className="flex items-start gap-3">
          <span className="confirm-icon flex size-11 shrink-0 items-center justify-center rounded-2xl">
            <WarningIcon />
          </span>
          <div className="min-w-0">
            <h2 id="confirm-title" className="text-lg font-semibold">
              {title}
            </h2>
            <p id="confirm-message" className="mt-1 text-sm text-[#4a5550]">
              {message}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <button
            ref={cancel}
            type="button"
            onClick={() => dialog.current?.close()}
            className="min-h-11 rounded-2xl bg-black/[0.05] px-5 text-sm font-medium hover:bg-black/[0.09] focus-visible:outline-2"
          >
            {t("common.cancel")}
          </button>
          <Button variant="danger" className="min-h-11 rounded-2xl px-5" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  );
}

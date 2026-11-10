import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { PublicService } from "../../shared/api/types";
import { Button } from "../../shared/ui/primitives";

/** Detalle de un servicio en una ventana (mejora R2): foto grande, descripción completa, duración y
 *  precio, con el botón para agregarlo o quitarlo. Usa `<dialog>` nativo: el navegador maneja el
 *  foco, la tecla Escape y lo anuncia como diálogo a los lectores de pantalla. */
export function ServiceDetail({
  service,
  price,
  selected,
  canAdd,
  onToggle,
  onClose,
}: {
  service: PublicService;
  price: string;
  selected: boolean;
  canAdd: boolean;
  onToggle: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const dialog = useRef<HTMLDialogElement>(null);

  // Sin limpieza: cerrar en el desmontaje dispararía `onClose` (y en desarrollo React monta los
  // efectos dos veces, así que la ventana se cerraría sola). Quitar el elemento ya la oculta.
  useEffect(() => {
    const element = dialog.current;
    if (element && !element.open) element.showModal();
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-labelledby="service-detail-title"
      onClose={onClose}
      // Clic en el fondo oscuro (fuera de la tarjeta) cierra la ventana.
      onClick={(event) => {
        if (event.target === dialog.current) dialog.current?.close();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl p-0 shadow-xl backdrop:bg-black/50"
    >
      <div className="flex flex-col gap-4 bg-[var(--color-surface,#ffffff)] p-5 text-[var(--color-text,#0f172a)]">
        {service.image?.medium && (
          <img
            src={service.image.medium}
            alt=""
            className="aspect-[4/3] w-full rounded-xl object-cover"
          />
        )}
        <div>
          <h2 id="service-detail-title" className="text-xl font-semibold">
            {service.name}
          </h2>
          <p className="mt-1 text-sm opacity-80">
            {price} · {t("catalog.services.minutes", { count: service.duration_min })}
          </p>
        </div>
        {service.description ? (
          <p className="whitespace-pre-line">{service.description}</p>
        ) : (
          <p className="text-sm opacity-70">{t("booking.wizard.noDescription")}</p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button
            className="flex-1"
            variant={selected ? "secondary" : "primary"}
            disabled={!selected && !canAdd}
            onClick={() => {
              onToggle();
              dialog.current?.close();
            }}
          >
            {selected ? t("booking.wizard.removeService") : t("booking.wizard.addService")}
          </Button>
          <Button variant="ghost" onClick={() => dialog.current?.close()}>
            {t("booking.wizard.closeDetail")}
          </Button>
        </div>
      </div>
    </dialog>
  );
}

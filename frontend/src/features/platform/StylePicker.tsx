import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import { PUBLIC_STYLES, type PublicStyle, type TenantDetail } from "../../shared/api/types";
import { Button, Card, Notice } from "../../shared/ui/primitives";

/** Colores de muestra de cada estilo: fondo, metal del botón y acento. Solo para la vista previa. */
const SWATCH: Record<PublicStyle, { ground: string; metal: string; accent: string; ink: string }> =
  {
    emerald: { ground: "#071a14", metal: "#1d6a4c", accent: "#d9b664", ink: "#f2efe6" },
    barbershop: { ground: "#141110", metal: "#8c1c24", accent: "#c9a35a", ink: "#efe6d6" },
    salon: { ground: "#f8ece7", metal: "#c98b7b", accent: "#b9776a", ink: "#3b2a2e" },
  };

/** El Super Admin elige el estilo de la página de reservas del negocio. "Automático" toma el del
 *  tipo de negocio (barbería → Barbería clásica; salón, uñas y spa → Salón). */
export function StylePicker({ tenant }: { tenant: TenantDetail }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [value, setValue] = useState<PublicStyle | "">(tenant.public_style);
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const save = useMutation({
    mutationFn: () =>
      api<TenantDetail>(`/api/v1/tenants/${tenant.id}/`, {
        method: "PATCH",
        body: { public_style: value },
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["tenant", tenant.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
      setMessage({ tone: "success", text: t("common.saved") });
    },
    onError: (error) => setMessage({ tone: "danger", text: describeError(t, error) }),
  });

  const options: (PublicStyle | "")[] = ["", ...PUBLIC_STYLES];
  return (
    <Card className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{t("styles.title")}</h2>
        <p className="text-sm text-slate-600">{t("styles.intro")}</p>
      </div>
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      <div role="radiogroup" aria-label={t("styles.title")} className="grid gap-3 sm:grid-cols-2">
        {options.map((option) => {
          const checked = value === option;
          const swatch = option ? SWATCH[option] : null;
          return (
            <button
              key={option || "auto"}
              type="button"
              role="radio"
              aria-checked={checked}
              onClick={() => {
                setValue(option);
                setMessage(null);
              }}
              className={`style-option flex items-center gap-4 rounded-2xl p-3 text-left ${checked ? "style-option-on" : ""}`}
            >
              <span
                aria-hidden="true"
                className="flex h-16 w-24 shrink-0 flex-col justify-end gap-1 overflow-hidden rounded-xl p-2"
                style={{ background: swatch?.ground ?? "#e2e8f0" }}
              >
                {swatch ? (
                  <>
                    <span className="h-2 w-12 rounded-full" style={{ background: swatch.ink }} />
                    <span className="flex gap-1">
                      <span className="h-3 w-8 rounded-full" style={{ background: swatch.metal }} />
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ background: swatch.accent }}
                      />
                    </span>
                  </>
                ) : (
                  <span className="text-xs font-semibold text-slate-600">A</span>
                )}
              </span>
              <span className="min-w-0">
                <span className="block font-semibold">{t(`styles.${option || "auto"}`)}</span>
                <span className="block text-sm text-slate-600">
                  {t(`styles.${option || "auto"}Hint`)}
                </span>
              </span>
            </button>
          );
        })}
      </div>
      <Button
        disabled={save.isPending || value === tenant.public_style}
        onClick={() => save.mutate()}
      >
        {save.isPending ? t("common.saving") : t("styles.save")}
      </Button>
    </Card>
  );
}

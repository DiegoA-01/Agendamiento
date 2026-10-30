import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api } from "../../shared/api/client";
import { applyServerErrors, describeError } from "../../shared/api/errors";
import { THEME_KEYS, type Theme, type TenantDetail } from "../../shared/api/types";
import { Badge, Button, Card, Notice, TextField } from "../../shared/ui/primitives";
import { MIN_TEXT_CONTRAST, contrastRatio, isHexColor } from "./contrast";
import { themeSchema, type ThemeValues } from "./schemas";

const DEFAULT_THEME: Theme = {
  primary: "#1f2937",
  secondary: "#b45309",
  background: "#ffffff",
  surface: "#f3f4f6",
  text: "#111827",
};

function ContrastLine({ text, surface, name }: { text: string; surface: string; name: string }) {
  const { t } = useTranslation();
  if (!isHexColor(text) || !isHexColor(surface)) return null;
  const ratio = contrastRatio(text, surface);
  const ok = ratio >= MIN_TEXT_CONTRAST;
  return (
    <p className="flex flex-wrap items-center gap-2 text-sm">
      {t("theme.contrastOn", { surface: name, ratio: ratio.toFixed(2) })}
      <Badge tone={ok ? "success" : "danger"}>
        {ok ? t("theme.contrastOk") : t("theme.contrastLow")}
      </Badge>
    </p>
  );
}

export function ThemeTab({ tenant }: { tenant: TenantDetail }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);

  const form = useForm<ThemeValues>({
    resolver: zodResolver(themeSchema),
    values: { ...DEFAULT_THEME, ...tenant.theme },
  });
  const { errors } = form.formState;
  const colors = useWatch({ control: form.control }) as ThemeValues;

  const save = useMutation({
    mutationFn: (values: ThemeValues) =>
      api<Theme>(`/api/v1/tenants/${tenant.id}/theme/`, { method: "PUT", body: values }),
    onSuccess: (theme) => {
      queryClient.setQueryData(["tenant", tenant.id], { ...tenant, theme });
      setMessage({ tone: "success", text: t("common.saved") });
    },
    onError: (error) => {
      applyServerErrors(error, form.setError, THEME_KEYS);
      setMessage({ tone: "danger", text: describeError(t, error) });
    },
  });

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_20rem]">
      <Card>
        <p className="mb-4 text-sm text-slate-600">{t("theme.intro")}</p>
        {message && (
          <div className="mb-4">
            <Notice tone={message.tone}>{message.text}</Notice>
          </div>
        )}
        <form
          onSubmit={form.handleSubmit((values) => save.mutate(values))}
          noValidate
          className="flex flex-col gap-4"
        >
          {THEME_KEYS.map((key) => {
            const label = t(`theme.${key}`);
            const value = colors[key] ?? "";
            return (
              <div key={key} className="grid grid-cols-[1fr_auto] items-end gap-3">
                <TextField
                  label={label}
                  spellCheck={false}
                  autoComplete="off"
                  error={errors[key]?.message}
                  {...form.register(key)}
                />
                <input
                  type="color"
                  aria-label={t("theme.colorPicker", { name: label })}
                  value={isHexColor(value) ? value : "#000000"}
                  onChange={(event) =>
                    form.setValue(key, event.target.value, {
                      shouldValidate: true,
                      shouldDirty: true,
                    })
                  }
                  className="h-10 w-12 cursor-pointer rounded border border-slate-300 bg-white p-1"
                />
              </div>
            );
          })}
          <div className="flex flex-col gap-1">
            <ContrastLine
              text={colors.text}
              surface={colors.background}
              name={t("theme.background")}
            />
            <ContrastLine text={colors.text} surface={colors.surface} name={t("theme.surface")} />
          </div>
          <div>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? t("common.saving") : t("common.save")}
            </Button>
          </div>
        </form>
      </Card>

      <section aria-label={t("theme.previewTitle")}>
        <h2 className="mb-2 text-sm font-semibold text-slate-900">{t("theme.previewTitle")}</h2>
        <div
          className="rounded-xl border border-slate-300 p-4"
          style={{
            background: isHexColor(colors.background) ? colors.background : undefined,
            color: isHexColor(colors.text) ? colors.text : undefined,
          }}
        >
          <p className="text-lg font-semibold">{t("theme.previewHeading")}</p>
          <div
            className="mt-3 rounded-lg p-3 text-sm"
            style={{ background: isHexColor(colors.surface) ? colors.surface : undefined }}
          >
            {t("theme.previewBody")}
          </div>
          <div className="mt-3 flex gap-2">
            <span
              className="rounded-lg px-4 py-2 text-sm font-medium text-white"
              style={{ background: isHexColor(colors.primary) ? colors.primary : undefined }}
            >
              {t("theme.previewButton")}
            </span>
            <span
              className="rounded-lg px-4 py-2 text-sm font-medium text-white"
              style={{ background: isHexColor(colors.secondary) ? colors.secondary : undefined }}
            >
              {t("theme.previewButton")}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}

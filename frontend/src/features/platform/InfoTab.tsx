import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api } from "../../shared/api/client";
import { applyServerErrors, describeError } from "../../shared/api/errors";
import { LANGUAGES, VERTICALS, type TenantDetail } from "../../shared/api/types";
import { Button, Card, Notice, SelectField, TextField } from "../../shared/ui/primitives";
import { usePlans } from "./api";
import { tenantEditSchema, type TenantEditValues } from "./schemas";

const FIELDS = ["name", "plan_id", "vertical", "timezone", "currency", "language"] as const;

export function InfoTab({ tenant }: { tenant: TenantDetail }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const plans = usePlans();
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);

  const form = useForm<TenantEditValues>({
    resolver: zodResolver(tenantEditSchema),
    values: {
      name: tenant.name,
      plan_id: tenant.plan.id,
      vertical: tenant.vertical,
      timezone: tenant.timezone,
      currency: tenant.currency,
      language: tenant.language,
    },
  });
  const { errors } = form.formState;

  const save = useMutation({
    mutationFn: (values: TenantEditValues) =>
      api<TenantDetail>(`/api/v1/tenants/${tenant.id}/`, { method: "PATCH", body: values }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["tenant", tenant.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
      void queryClient.invalidateQueries({ queryKey: ["tenant", tenant.id, "modules"] });
      setMessage({ tone: "success", text: t("common.saved") });
    },
    onError: (error) => {
      setMessage(null);
      if (!applyServerErrors(error, form.setError, FIELDS)) {
        setMessage({ tone: "danger", text: describeError(t, error) });
      }
    },
  });

  return (
    <Card>
      <form
        onSubmit={form.handleSubmit((values) => save.mutate(values))}
        noValidate
        className="grid gap-4 sm:grid-cols-2"
      >
        {message && (
          <div className="sm:col-span-2">
            <Notice tone={message.tone}>{message.text}</Notice>
          </div>
        )}
        <TextField
          label={t("tenants.name")}
          error={errors.name?.message}
          {...form.register("name")}
        />
        <TextField
          label={t("tenants.slug")}
          value={tenant.slug}
          readOnly
          hint={t("tenants.detail.slugReadonly")}
          onChange={() => undefined}
        />
        <SelectField
          label={t("tenants.plan")}
          error={errors.plan_id?.message}
          {...form.register("plan_id")}
        >
          {(plans.data ?? [{ id: tenant.plan.id, name: tenant.plan.name }]).map((plan) => (
            <option key={plan.id} value={plan.id}>
              {plan.name}
            </option>
          ))}
        </SelectField>
        <SelectField label={t("tenants.vertical")} {...form.register("vertical")}>
          {VERTICALS.map((vertical) => (
            <option key={vertical} value={vertical}>
              {t(`verticals.${vertical}`)}
            </option>
          ))}
        </SelectField>
        <TextField
          label={t("tenants.timezone")}
          error={errors.timezone?.message}
          {...form.register("timezone")}
        />
        <TextField
          label={t("tenants.currency")}
          maxLength={3}
          error={errors.currency?.message}
          {...form.register("currency")}
        />
        <SelectField label={t("tenants.language")} {...form.register("language")}>
          {LANGUAGES.map((language) => (
            <option key={language} value={language}>
              {t(`language.${language}`)}
            </option>
          ))}
        </SelectField>
        <div className="sm:col-span-2">
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      </form>
    </Card>
  );
}

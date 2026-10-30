import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api } from "../../shared/api/client";
import { applyServerErrors, describeError } from "../../shared/api/errors";
import { MODULE_KEYS, type Plan } from "../../shared/api/types";
import {
  Badge,
  Button,
  Card,
  CheckboxField,
  EmptyState,
  ErrorBox,
  Loading,
  Notice,
  PageHeader,
  TextField,
} from "../../shared/ui/primitives";
import { usePlans } from "./api";
import { planSchema, type PlanValues } from "./schemas";

const FIELDS = ["name", "modules", "max_professionals", "max_locations"] as const;

function PlanForm({ plan, onDone }: { plan?: Plan; onDone: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);

  const form = useForm<PlanValues>({
    resolver: zodResolver(planSchema),
    defaultValues: {
      name: plan?.name ?? "",
      modules: plan?.modules ?? ["booking"],
      max_professionals: plan?.max_professionals ?? 1,
      max_locations: plan?.max_locations ?? 1,
      apply_to_tenants: false,
    },
  });
  const { errors } = form.formState;

  const save = useMutation({
    mutationFn: (values: PlanValues) => {
      const { apply_to_tenants, ...rest } = values;
      return plan
        ? api<Plan>(`/api/v1/plans/${plan.id}/`, {
            method: "PATCH",
            body: { ...rest, apply_to_tenants },
          })
        : api<Plan>("/api/v1/plans/", { method: "POST", body: rest });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["plans"] });
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
      onDone();
    },
    onError: (error) => {
      setMessage(null);
      if (!applyServerErrors(error, form.setError, FIELDS)) setMessage(describeError(t, error));
    },
  });

  return (
    <form
      onSubmit={form.handleSubmit((values) => save.mutate(values))}
      noValidate
      className="grid gap-4 sm:grid-cols-2"
    >
      {message && (
        <div className="sm:col-span-2">
          <Notice tone="danger">{message}</Notice>
        </div>
      )}
      <div className="sm:col-span-2">
        <TextField
          label={t("plans.name")}
          error={errors.name?.message}
          {...form.register("name")}
        />
      </div>
      <fieldset className="flex flex-col gap-2 sm:col-span-2">
        <legend className="mb-1 text-sm font-medium text-slate-800">{t("plans.modules")}</legend>
        {MODULE_KEYS.map((key) => (
          <CheckboxField
            key={key}
            label={t(`modules.${key}`)}
            value={key}
            {...form.register("modules")}
          />
        ))}
      </fieldset>
      <TextField
        label={t("plans.maxProfessionals")}
        type="number"
        min={1}
        error={errors.max_professionals?.message}
        {...form.register("max_professionals", { valueAsNumber: true })}
      />
      <TextField
        label={t("plans.maxLocations")}
        type="number"
        min={1}
        error={errors.max_locations?.message}
        {...form.register("max_locations", { valueAsNumber: true })}
      />
      {plan && (
        <div className="sm:col-span-2">
          <CheckboxField
            label={t("plans.applyToTenants")}
            hint={t("plans.applyHelp")}
            {...form.register("apply_to_tenants")}
          />
        </div>
      )}
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? t("common.saving") : plan ? t("common.save") : t("plans.create")}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}

function PlanCard({ plan }: { plan: Plan }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);

  const remove = useMutation({
    mutationFn: () => api<void>(`/api/v1/plans/${plan.id}/`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["plans"] }),
  });

  if (editing) {
    return (
      <Card>
        <PlanForm plan={plan} onDone={() => setEditing(false)} />
      </Card>
    );
  }
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-lg font-semibold">{plan.name}</h2>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setEditing(true)}>
            {t("plans.edit")}
          </Button>
          <Button
            variant="danger"
            disabled={remove.isPending}
            onClick={() => {
              if (window.confirm(t("plans.deleteConfirm", { name: plan.name }))) remove.mutate();
            }}
          >
            {t("common.delete")}
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {plan.modules.length === 0 && <Badge>—</Badge>}
        {plan.modules.map((key) => (
          <Badge key={key} tone="info">
            {t(`modules.${key}`)}
          </Badge>
        ))}
      </div>
      <p className="text-sm text-slate-600">
        {t("plans.professionalsShort", { count: plan.max_professionals })} ·{" "}
        {t("plans.locationsShort", { count: plan.max_locations })}
      </p>
      {remove.isError && <Notice tone="danger">{describeError(t, remove.error)}</Notice>}
    </Card>
  );
}

export function PlansPage() {
  const { t } = useTranslation();
  const plans = usePlans();
  const [creating, setCreating] = useState(false);

  return (
    <>
      <PageHeader
        title={t("plans.title")}
        actions={
          !creating && <Button onClick={() => setCreating(true)}>{t("plans.newButton")}</Button>
        }
      />
      {creating && (
        <Card className="mb-5">
          <PlanForm onDone={() => setCreating(false)} />
        </Card>
      )}
      {plans.isPending && <Loading />}
      {plans.isError && (
        <ErrorBox message={describeError(t, plans.error)} onRetry={() => void plans.refetch()} />
      )}
      {plans.isSuccess && plans.data.length === 0 && !creating && (
        <EmptyState>{t("plans.empty")}</EmptyState>
      )}
      {plans.isSuccess && (
        <div className="grid gap-4 md:grid-cols-2">
          {plans.data.map((plan) => (
            <PlanCard key={plan.id} plan={plan} />
          ))}
        </div>
      )}
    </>
  );
}

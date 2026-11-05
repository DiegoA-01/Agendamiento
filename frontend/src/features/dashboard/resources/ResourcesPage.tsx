import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api } from "../../../shared/api/client";
import { applyServerErrors, describeError } from "../../../shared/api/errors";
import type { Workstation } from "../../../shared/api/types";
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
} from "../../../shared/ui/primitives";
import { KEYS, useResources } from "../shared/api";
import { resourceSchema, type ResourceValues } from "../shared/schemas";
import { useCan } from "../shared/useCan";

function ResourceForm({ resource, onDone }: { resource?: Workstation; onDone: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const form = useForm<ResourceValues>({
    resolver: zodResolver(resourceSchema),
    defaultValues: {
      name: resource?.name ?? "",
      kind: resource?.kind ?? "",
      is_active: resource?.is_active ?? true,
    },
  });
  const { errors } = form.formState;
  const save = useMutation({
    mutationFn: (values: ResourceValues) =>
      resource
        ? api<Workstation>(`/api/v1/resources/${resource.id}/`, { method: "PATCH", body: values })
        : api<Workstation>("/api/v1/resources/", { method: "POST", body: values }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.resources });
      onDone();
    },
    onError: (error) => applyServerErrors(error, form.setError, ["name", "kind"]),
  });

  return (
    <form
      onSubmit={form.handleSubmit((values) => save.mutate(values))}
      noValidate
      className="grid gap-4 sm:grid-cols-2"
    >
      {save.isError && !errors.name && !errors.kind && (
        <div className="sm:col-span-2">
          <Notice tone="danger">{describeError(t, save.error)}</Notice>
        </div>
      )}
      <TextField
        label={t("catalog.resources.name")}
        placeholder={t("catalog.resources.namePlaceholder")}
        error={errors.name?.message}
        {...form.register("name")}
      />
      <TextField
        label={t("catalog.resources.kind")}
        placeholder={t("catalog.resources.kindPlaceholder")}
        optional
        error={errors.kind?.message}
        {...form.register("kind")}
      />
      <Controller
        control={form.control}
        name="is_active"
        render={({ field }) => (
          <CheckboxField
            label={t("catalog.resources.active")}
            checked={field.value}
            onChange={(event) => field.onChange(event.target.checked)}
          />
        )}
      />
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? t("common.saving") : t("common.save")}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}

function ResourceRow({ resource, editable }: { resource: Workstation; editable: boolean }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const remove = useMutation({
    mutationFn: () => api<void>(`/api/v1/resources/${resource.id}/`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: KEYS.resources }),
  });

  if (editing) {
    return (
      <li className="border-t border-slate-100 py-4">
        <ResourceForm resource={resource} onDone={() => setEditing(false)} />
      </li>
    );
  }
  return (
    <li className="flex flex-wrap items-center gap-3 border-t border-slate-100 py-3">
      <div className="min-w-0 flex-1">
        <p className="font-medium">
          {resource.name}{" "}
          {!resource.is_active && <Badge tone="warning">{t("catalog.resources.inactive")}</Badge>}
        </p>
        {resource.kind && <p className="text-sm text-slate-600">{resource.kind}</p>}
      </div>
      {editable && (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setEditing(true)}>
            {t("catalog.edit")}
          </Button>
          <Button
            variant="ghost"
            disabled={remove.isPending}
            onClick={() => {
              if (window.confirm(t("catalog.resources.deleteConfirm", { name: resource.name })))
                remove.mutate();
            }}
          >
            {t("common.delete")}
          </Button>
        </div>
      )}
      {remove.isError && (
        <div className="w-full">
          <Notice tone="danger">{describeError(t, remove.error)}</Notice>
        </div>
      )}
    </li>
  );
}

export default function ResourcesPage() {
  const { t } = useTranslation();
  const resources = useResources();
  const editable = useCan("staff_services", "update");
  const [creating, setCreating] = useState(false);

  return (
    <>
      <PageHeader
        title={t("dashboard.nav.resources")}
        description={t("catalog.resources.intro")}
        actions={
          editable &&
          !creating && (
            <Button onClick={() => setCreating(true)}>{t("catalog.resources.new")}</Button>
          )
        }
      />
      {creating && (
        <Card className="mb-5">
          <ResourceForm onDone={() => setCreating(false)} />
        </Card>
      )}
      {resources.isPending && <Loading />}
      {resources.isError && (
        <ErrorBox
          message={describeError(t, resources.error)}
          onRetry={() => void resources.refetch()}
        />
      )}
      {resources.isSuccess && resources.data.length === 0 && !creating && (
        <EmptyState>{t("catalog.resources.empty")}</EmptyState>
      )}
      {resources.isSuccess && resources.data.length > 0 && (
        <Card>
          <ul>
            {resources.data.map((resource) => (
              <ResourceRow key={resource.id} resource={resource} editable={editable} />
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}

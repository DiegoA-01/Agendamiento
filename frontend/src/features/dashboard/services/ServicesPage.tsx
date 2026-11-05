import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api } from "../../../shared/api/client";
import { applyServerErrors, describeError } from "../../../shared/api/errors";
import type { Category, ImageRef, Service } from "../../../shared/api/types";
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
  SelectField,
  TextAreaField,
  TextField,
} from "../../../shared/ui/primitives";
import { useMe } from "../../auth/useMe";
import { KEYS, useCategories, useServices } from "../shared/api";
import { ImageField } from "../shared/ImageField";
import { formatMoney } from "../shared/money";
import {
  categorySchema,
  serviceSchema,
  serviceToValues,
  type CategoryValues,
  type ServiceValues,
} from "../shared/schemas";
import { useCan } from "../shared/useCan";

const SERVICE_FIELDS = [
  "category_id",
  "name",
  "description",
  "duration_min",
  "buffer_min",
  "price",
] as const;

// --- Categorías ---------------------------------------------------------------------------------

function CategoryForm({ category, onDone }: { category?: Category; onDone: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const form = useForm<CategoryValues>({
    resolver: zodResolver(categorySchema),
    defaultValues: { name: category?.name ?? "" },
  });
  const save = useMutation({
    mutationFn: (values: CategoryValues) =>
      category
        ? api<Category>(`/api/v1/categories/${category.id}/`, { method: "PATCH", body: values })
        : api<Category>("/api/v1/categories/", { method: "POST", body: values }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.categories });
      onDone();
    },
    onError: (error) => applyServerErrors(error, form.setError, ["name"]),
  });

  return (
    <form
      onSubmit={form.handleSubmit((values) => save.mutate(values))}
      noValidate
      className="flex flex-wrap items-end gap-2"
    >
      <div className="min-w-48 flex-1">
        <TextField
          label={t("catalog.categories.name")}
          error={form.formState.errors.name?.message}
          autoFocus
          {...form.register("name")}
        />
      </div>
      <Button type="submit" disabled={save.isPending}>
        {save.isPending ? t("common.saving") : t("common.save")}
      </Button>
      <Button variant="ghost" onClick={onDone}>
        {t("common.cancel")}
      </Button>
      {save.isError && !form.formState.errors.name && (
        <div className="w-full">
          <Notice tone="danger">{describeError(t, save.error)}</Notice>
        </div>
      )}
    </form>
  );
}

function CategoryHeader({ category, editable }: { category: Category; editable: boolean }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const remove = useMutation({
    mutationFn: () => api<void>(`/api/v1/categories/${category.id}/`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: KEYS.categories }),
  });

  if (editing) return <CategoryForm category={category} onDone={() => setEditing(false)} />;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{category.name}</h2>
        {editable && (
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setEditing(true)}>
              {t("catalog.categories.rename")}
            </Button>
            <Button
              variant="ghost"
              disabled={remove.isPending}
              onClick={() => {
                if (window.confirm(t("catalog.categories.deleteConfirm", { name: category.name })))
                  remove.mutate();
              }}
            >
              {t("common.delete")}
            </Button>
          </div>
        )}
      </div>
      {remove.isError && <Notice tone="danger">{describeError(t, remove.error)}</Notice>}
    </div>
  );
}

// --- Servicios ----------------------------------------------------------------------------------

function ServiceForm({
  service,
  categories,
  categoryId,
  onDone,
}: {
  service?: Service;
  categories: Category[];
  categoryId?: string;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [image, setImage] = useState<ImageRef | null>(service?.image ?? null);
  const [message, setMessage] = useState<string | null>(null);
  const form = useForm<ServiceValues>({
    resolver: zodResolver(serviceSchema),
    defaultValues: serviceToValues(
      service,
      categoryId ?? (categories.length === 1 ? categories[0].id : ""),
    ),
  });
  const { errors } = form.formState;

  const save = useMutation({
    mutationFn: (values: ServiceValues) => {
      const body = { ...values, image_id: image?.id ?? null };
      return service
        ? api<Service>(`/api/v1/services/${service.id}/`, { method: "PATCH", body })
        : api<Service>("/api/v1/services/", { method: "POST", body });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.services });
      void queryClient.invalidateQueries({ queryKey: KEYS.categories });
      onDone();
    },
    onError: (error) => {
      setMessage(null);
      if (!applyServerErrors(error, form.setError, SERVICE_FIELDS)) {
        setMessage(describeError(t, error));
      }
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
      <TextField
        label={t("catalog.services.name")}
        error={errors.name?.message}
        {...form.register("name")}
      />
      <SelectField
        label={t("catalog.services.category")}
        error={errors.category_id?.message}
        {...form.register("category_id")}
      >
        <option value="">{t("catalog.services.chooseCategory")}</option>
        {categories.map((category) => (
          <option key={category.id} value={category.id}>
            {category.name}
          </option>
        ))}
      </SelectField>
      <TextField
        label={t("catalog.services.price")}
        inputMode="decimal"
        placeholder="30000"
        error={errors.price?.message}
        {...form.register("price")}
      />
      <TextField
        label={t("catalog.services.duration")}
        type="number"
        min={5}
        step={5}
        error={errors.duration_min?.message}
        {...form.register("duration_min", { valueAsNumber: true })}
      />
      <TextField
        label={t("catalog.services.buffer")}
        hint={t("catalog.services.bufferHint")}
        type="number"
        min={0}
        step={5}
        error={errors.buffer_min?.message}
        {...form.register("buffer_min", { valueAsNumber: true })}
      />
      <div className="sm:col-span-2">
        <TextAreaField
          label={t("catalog.services.description")}
          optional
          rows={3}
          {...form.register("description")}
        />
      </div>
      <Controller
        control={form.control}
        name="is_active"
        render={({ field }) => (
          <CheckboxField
            label={t("catalog.services.active")}
            hint={t("catalog.services.activeHint")}
            checked={field.value}
            onChange={(event) => field.onChange(event.target.checked)}
          />
        )}
      />
      <Controller
        control={form.control}
        name="requires_resource"
        render={({ field }) => (
          <CheckboxField
            label={t("catalog.services.requiresResource")}
            hint={t("catalog.services.requiresResourceHint")}
            checked={field.value}
            onChange={(event) => field.onChange(event.target.checked)}
          />
        )}
      />
      <div className="sm:col-span-2">
        <ImageField label={t("catalog.services.image")} value={image} onChange={setImage} />
      </div>
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

function ServiceRow({
  service,
  categories,
  editable,
}: {
  service: Service;
  categories: Category[];
  editable: boolean;
}) {
  const { t, i18n } = useTranslation();
  const currency = useMe().data?.tenant?.currency ?? "COP";
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const remove = useMutation({
    mutationFn: () => api<void>(`/api/v1/services/${service.id}/`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: KEYS.services }),
  });

  if (editing) {
    return (
      <li className="border-t border-slate-100 py-4">
        <ServiceForm service={service} categories={categories} onDone={() => setEditing(false)} />
      </li>
    );
  }
  return (
    <li className="flex flex-wrap items-center gap-3 border-t border-slate-100 py-3">
      {service.image && (
        <img src={service.image.urls.thumb} alt="" className="size-12 rounded-lg object-cover" />
      )}
      <div className="min-w-0 flex-1">
        <p className="font-medium">
          {service.name}{" "}
          {!service.is_active && <Badge tone="warning">{t("catalog.services.inactive")}</Badge>}
        </p>
        <p className="text-sm text-slate-600">
          {formatMoney(service.price, currency, i18n.language)} ·{" "}
          {t("catalog.services.minutes", { count: service.duration_min })}
          {service.requires_resource && ` · ${t("catalog.services.needsResource")}`}
        </p>
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
              if (window.confirm(t("catalog.services.deleteConfirm", { name: service.name })))
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

export default function ServicesPage() {
  const { t } = useTranslation();
  const categories = useCategories();
  const services = useServices();
  const editable = useCan("staff_services", "update");
  const [creating, setCreating] = useState<"category" | "service" | null>(null);

  const loading = categories.isPending || services.isPending;
  const failed = categories.isError ? categories : services.isError ? services : null;

  return (
    <>
      <PageHeader
        title={t("dashboard.nav.services")}
        description={editable ? t("catalog.services.intro") : t("catalog.readOnly")}
        actions={
          editable &&
          !creating && (
            <>
              <Button variant="secondary" onClick={() => setCreating("category")}>
                {t("catalog.categories.new")}
              </Button>
              <Button
                onClick={() => setCreating("service")}
                disabled={!categories.data?.length}
                title={categories.data?.length ? undefined : t("catalog.services.needCategory")}
              >
                {t("catalog.services.new")}
              </Button>
            </>
          )
        }
      />
      {loading && <Loading />}
      {failed && (
        <ErrorBox message={describeError(t, failed.error)} onRetry={() => void failed.refetch()} />
      )}
      {categories.isSuccess && services.isSuccess && (
        <div className="flex flex-col gap-5">
          {creating === "category" && (
            <Card>
              <CategoryForm onDone={() => setCreating(null)} />
            </Card>
          )}
          {creating === "service" && (
            <Card>
              <ServiceForm categories={categories.data} onDone={() => setCreating(null)} />
            </Card>
          )}
          {categories.data.length === 0 && !creating && (
            <EmptyState>
              {editable ? t("catalog.categories.emptyEditable") : t("catalog.services.empty")}
            </EmptyState>
          )}
          {categories.data.map((category) => {
            const inCategory = services.data.filter((s) => s.category_id === category.id);
            return (
              <Card key={category.id}>
                <CategoryHeader category={category} editable={editable} />
                {inCategory.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-600">
                    {t("catalog.services.emptyCategory")}
                  </p>
                ) : (
                  <ul className="mt-3">
                    {inCategory.map((service) => (
                      <ServiceRow
                        key={service.id}
                        service={service}
                        categories={categories.data}
                        editable={editable}
                      />
                    ))}
                  </ul>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

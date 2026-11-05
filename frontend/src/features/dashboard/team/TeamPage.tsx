import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Controller, useFieldArray, useForm, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api } from "../../../shared/api/client";
import { applyServerErrors, describeError } from "../../../shared/api/errors";
import type {
  ImageRef,
  OfferedService,
  Professional,
  Service,
  Specialty,
} from "../../../shared/api/types";
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
  TextAreaField,
  TextField,
} from "../../../shared/ui/primitives";
import { useMe } from "../../auth/useMe";
import { KEYS, useOffers, useProfessionals, useServices, useSpecialties } from "../shared/api";
import { ImageField } from "../shared/ImageField";
import { formatMoney } from "../../../shared/money";
import {
  offersPayload,
  offersSchema,
  offersToValues,
  professionalSchema,
  professionalToValues,
  type OffersValues,
  type ProfessionalValues,
} from "../shared/schemas";
import { useCan } from "../shared/useCan";

const PROFESSIONAL_FIELDS = ["display_name", "bio", "default_commission_pct"] as const;

// --- Ficha --------------------------------------------------------------------------------------

function NewSpecialty() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: () =>
      api<Specialty>("/api/v1/specialties/", { method: "POST", body: { name: name.trim() } }),
    onSuccess: () => {
      setName("");
      void queryClient.invalidateQueries({ queryKey: KEYS.specialties });
    },
  });
  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="min-w-40 flex-1">
        <TextField
          label={t("catalog.team.newSpecialty")}
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => {
            // Está dentro del formulario de la ficha: Enter agrega la especialidad, no guarda.
            if (event.key === "Enter") {
              event.preventDefault();
              if (name.trim()) create.mutate();
            }
          }}
        />
      </div>
      <Button
        variant="secondary"
        disabled={!name.trim() || create.isPending}
        onClick={() => create.mutate()}
      >
        {t("catalog.team.addSpecialty")}
      </Button>
    </div>
  );
}

function ProfessionalForm({
  professional,
  onDone,
}: {
  professional?: Professional;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const specialties = useSpecialties();
  const [photo, setPhoto] = useState<ImageRef | null>(professional?.photo ?? null);
  const [message, setMessage] = useState<string | null>(null);
  const form = useForm<ProfessionalValues>({
    resolver: zodResolver(professionalSchema),
    defaultValues: professionalToValues(professional),
  });
  const { errors } = form.formState;

  const save = useMutation({
    mutationFn: (values: ProfessionalValues) => {
      const body = { ...values, photo_id: photo?.id ?? null };
      return professional
        ? api<Professional>(`/api/v1/professionals/${professional.id}/`, {
            method: "PATCH",
            body,
          })
        : api<Professional>("/api/v1/professionals/", { method: "POST", body });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.professionals });
      onDone();
    },
    onError: (error) => {
      setMessage(null);
      if (!applyServerErrors(error, form.setError, PROFESSIONAL_FIELDS)) {
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
        label={t("catalog.team.name")}
        error={errors.display_name?.message}
        {...form.register("display_name")}
      />
      <TextField
        label={t("catalog.team.commission")}
        hint={t("catalog.team.commissionHint")}
        inputMode="decimal"
        error={errors.default_commission_pct?.message}
        {...form.register("default_commission_pct")}
      />
      <div className="sm:col-span-2">
        <TextAreaField label={t("catalog.team.bio")} optional rows={3} {...form.register("bio")} />
      </div>
      <Controller
        control={form.control}
        name="is_active"
        render={({ field }) => (
          <CheckboxField
            label={t("catalog.team.active")}
            hint={t("catalog.team.activeHint")}
            checked={field.value}
            onChange={(event) => field.onChange(event.target.checked)}
          />
        )}
      />
      <Controller
        control={form.control}
        name="accepts_online_booking"
        render={({ field }) => (
          <CheckboxField
            label={t("catalog.team.online")}
            hint={t("catalog.team.onlineHint")}
            checked={field.value}
            onChange={(event) => field.onChange(event.target.checked)}
          />
        )}
      />
      <fieldset className="flex flex-col gap-2 sm:col-span-2">
        <legend className="mb-1 text-sm font-medium text-slate-800">
          {t("catalog.team.specialties")}
        </legend>
        {specialties.data?.length === 0 && (
          <p className="text-sm text-slate-600">{t("catalog.team.noSpecialties")}</p>
        )}
        <div className="grid gap-2 sm:grid-cols-2">
          {specialties.data?.map((specialty) => (
            <CheckboxField
              key={specialty.id}
              label={specialty.name}
              value={specialty.id}
              {...form.register("specialty_ids")}
            />
          ))}
        </div>
        <NewSpecialty />
      </fieldset>
      <div className="sm:col-span-2">
        <ImageField label={t("catalog.team.photo")} value={photo} onChange={setPhoto} />
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

// --- Servicios que ofrece -----------------------------------------------------------------------

function OffersEditor({
  professional,
  services,
  offers,
  onDone,
}: {
  professional: Professional;
  services: Service[];
  offers: OfferedService[];
  onDone: () => void;
}) {
  const { t, i18n } = useTranslation();
  const currency = useMe().data?.tenant?.currency ?? "COP";
  const queryClient = useQueryClient();
  const form = useForm<OffersValues>({
    resolver: zodResolver(offersSchema),
    defaultValues: offersToValues(services, offers),
  });
  const { fields } = useFieldArray({ control: form.control, name: "rows" });
  const rows = useWatch({ control: form.control, name: "rows" });
  const save = useMutation({
    mutationFn: (values: OffersValues) =>
      api<{ services: OfferedService[] }>(`/api/v1/professionals/${professional.id}/services/`, {
        method: "PUT",
        body: offersPayload(values),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(KEYS.offers(professional.id), data);
      onDone();
    },
  });
  const rowErrors = form.formState.errors.rows;

  return (
    <form
      onSubmit={form.handleSubmit((values) => save.mutate(values))}
      noValidate
      className="flex flex-col gap-3"
    >
      <p className="text-sm text-slate-600">{t("catalog.team.offersHint")}</p>
      {save.isError && <Notice tone="danger">{describeError(t, save.error)}</Notice>}
      <ul className="flex flex-col gap-3">
        {fields.map((field, index) => {
          const service = services[index];
          const offered = rows[index]?.offered;
          const errors = rowErrors?.[index];
          return (
            <li key={field.id} className="rounded-lg border border-slate-200 p-3">
              <CheckboxField
                label={`${service.name} · ${formatMoney(service.price, currency, i18n.language)} · ${t("catalog.services.minutes", { count: service.duration_min })}`}
                {...form.register(`rows.${index}.offered`)}
              />
              {offered && (
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  <TextField
                    label={t("catalog.team.priceOverride")}
                    inputMode="decimal"
                    placeholder={service.price}
                    optional
                    error={errors?.price_override?.message}
                    {...form.register(`rows.${index}.price_override`)}
                  />
                  <TextField
                    label={t("catalog.team.durationOverride")}
                    inputMode="numeric"
                    placeholder={String(service.duration_min)}
                    optional
                    error={errors?.duration_override_min?.message}
                    {...form.register(`rows.${index}.duration_override_min`)}
                  />
                  <TextField
                    label={t("catalog.team.commissionOverride")}
                    inputMode="decimal"
                    placeholder={professional.default_commission_pct}
                    optional
                    error={errors?.commission_pct_override?.message}
                    {...form.register(`rows.${index}.commission_pct_override`)}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ul>
      <div className="flex gap-2">
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

function OffersSection({
  professional,
  editable,
}: {
  professional: Professional;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const offers = useOffers(professional.id);
  const services = useServices();
  const [editing, setEditing] = useState(false);

  if (offers.isPending || services.isPending) return <Loading />;
  if (offers.isError || services.isError) {
    return <Notice tone="danger">{describeError(t, offers.error ?? services.error)}</Notice>;
  }
  if (editing) {
    return (
      <OffersEditor
        professional={professional}
        services={services.data}
        offers={offers.data.services}
        onDone={() => setEditing(false)}
      />
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{t("catalog.team.offers")}</h3>
        {editable && services.data.length > 0 && (
          <Button variant="secondary" onClick={() => setEditing(true)}>
            {t("catalog.team.editOffers")}
          </Button>
        )}
      </div>
      {offers.data.services.length === 0 ? (
        <p className="text-sm text-slate-600">
          {services.data.length === 0
            ? t("catalog.team.noServicesYet")
            : t("catalog.team.noOffers")}
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {offers.data.services.map((offer) => (
            <Badge key={offer.service_id} tone="info">
              {offer.service_name}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Página -------------------------------------------------------------------------------------

function ProfessionalCard({
  professional,
  specialties,
  editable,
}: {
  professional: Professional;
  specialties: Specialty[];
  editable: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const remove = useMutation({
    mutationFn: () => api<void>(`/api/v1/professionals/${professional.id}/`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: KEYS.professionals }),
  });
  const names = specialties
    .filter((specialty) => professional.specialty_ids.includes(specialty.id))
    .map((specialty) => specialty.name);

  if (editing) {
    return (
      <Card>
        <ProfessionalForm professional={professional} onDone={() => setEditing(false)} />
      </Card>
    );
  }
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start gap-3">
        {professional.photo ? (
          <img
            src={professional.photo.urls.thumb}
            alt=""
            className="size-16 rounded-full object-cover"
          />
        ) : (
          <div
            aria-hidden="true"
            className="flex size-16 items-center justify-center rounded-full bg-slate-200 text-xl font-semibold text-slate-700"
          >
            {professional.display_name.charAt(0).toUpperCase()}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold">{professional.display_name}</h2>
          <div className="mt-1 flex flex-wrap gap-2">
            {!professional.is_active && <Badge tone="warning">{t("catalog.team.inactive")}</Badge>}
            {!professional.accepts_online_booking && <Badge>{t("catalog.team.offline")}</Badge>}
            <Badge>
              {t("catalog.team.commissionShort", {
                pct: Number(professional.default_commission_pct),
              })}
            </Badge>
          </div>
          {names.length > 0 && <p className="mt-2 text-sm text-slate-600">{names.join(" · ")}</p>}
          {professional.bio && <p className="mt-2 text-sm">{professional.bio}</p>}
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
                if (
                  window.confirm(
                    t("catalog.team.deleteConfirm", { name: professional.display_name }),
                  )
                )
                  remove.mutate();
              }}
            >
              {t("common.delete")}
            </Button>
          </div>
        )}
      </div>
      {remove.isError && <Notice tone="danger">{describeError(t, remove.error)}</Notice>}
      <OffersSection professional={professional} editable={editable} />
    </Card>
  );
}

export default function TeamPage() {
  const { t } = useTranslation();
  const professionals = useProfessionals();
  const specialties = useSpecialties();
  const editable = useCan("staff_services", "update");
  const [creating, setCreating] = useState(false);

  return (
    <>
      <PageHeader
        title={t("dashboard.nav.team")}
        description={editable ? t("catalog.team.intro") : t("catalog.readOnly")}
        actions={
          editable &&
          !creating && <Button onClick={() => setCreating(true)}>{t("catalog.team.new")}</Button>
        }
      />
      {creating && (
        <Card className="mb-5">
          <ProfessionalForm onDone={() => setCreating(false)} />
        </Card>
      )}
      {professionals.isPending && <Loading />}
      {professionals.isError && (
        <ErrorBox
          message={describeError(t, professionals.error)}
          onRetry={() => void professionals.refetch()}
        />
      )}
      {professionals.isSuccess && professionals.data.length === 0 && !creating && (
        <EmptyState>{t("catalog.team.empty")}</EmptyState>
      )}
      {professionals.isSuccess && (
        <div className="flex flex-col gap-4">
          {professionals.data.map((professional) => (
            <ProfessionalCard
              key={professional.id}
              professional={professional}
              specialties={specialties.data ?? []}
              editable={editable}
            />
          ))}
        </div>
      )}
    </>
  );
}

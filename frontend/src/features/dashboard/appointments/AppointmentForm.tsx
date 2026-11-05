import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../../shared/api/client";
import { applyServerErrors, describeError } from "../../../shared/api/errors";
import type { Appointment } from "../../../shared/api/types";
import {
  Button,
  CheckboxField,
  EmptyState,
  ErrorBox,
  Loading,
  Notice,
  SelectField,
  TextField,
} from "../../../shared/ui/primitives";
import { useMe } from "../../auth/useMe";
import { formatDateTime, todayIn } from "../../booking/wizard";
import { useProfessionals, useServices } from "../shared/api";
import { useCustomers, useDebounced, useRefreshAppointments } from "./api";
import { appointmentPayload, appointmentSchema, type AppointmentValues } from "./schemas";
import { SlotPicker } from "./SlotPicker";

export function AppointmentForm({ onDone }: { onDone: () => void }) {
  const { t, i18n } = useTranslation();
  const zone = useMe().data?.tenant?.timezone ?? "America/Bogota";
  const services = useServices();
  const professionals = useProfessionals();
  const refresh = useRefreshAppointments();
  const [search, setSearch] = useState("");
  const form = useForm<AppointmentValues>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: {
      service_ids: [],
      professional_id: "",
      date: todayIn(zone),
      start_at: "",
      customer_mode: "existing",
      customer_id: "",
      full_name: "",
      phone: "",
      email: "",
      marketing_consent: false,
    },
  });
  const values = useWatch({ control: form.control });
  const debouncedSearch = useDebounced(search);
  const customers = useCustomers(debouncedSearch, values.customer_mode === "existing");
  const errors = form.formState.errors;
  const save = useMutation({
    mutationFn: (input: AppointmentValues) =>
      api<Appointment>("/api/v1/appointments/", {
        method: "POST",
        body: appointmentPayload(input),
      }),
    onSuccess: () => {
      refresh();
      onDone();
    },
    onError: (error) => {
      applyServerErrors(error, form.setError, [
        "service_ids",
        "professional_id",
        "start_at",
        "customer_id",
        "full_name",
        "phone",
        "email",
      ]);
      if (error instanceof ApiError && error.code === "slot_taken") {
        form.setValue("start_at", "");
        refresh();
      }
    },
  });
  const suggestions =
    save.error instanceof ApiError && save.error.code === "slot_taken"
      ? (save.error.fields.suggestions ?? [])
      : [];
  const clearSlot = () => {
    form.setValue("start_at", "");
    save.reset();
  };
  if (services.isPending || professionals.isPending) return <Loading />;
  const failed = services.isError ? services : professionals.isError ? professionals : null;
  if (failed)
    return (
      <ErrorBox message={describeError(t, failed.error)} onRetry={() => void failed.refetch()} />
    );
  return (
    <form
      className="grid min-w-0 gap-4"
      noValidate
      onSubmit={form.handleSubmit((input) => save.mutate(input))}
    >
      <h2 className="text-lg font-semibold">{t("agenda.newAppointment")}</h2>
      <fieldset className="grid gap-2">
        <legend className="mb-2 font-medium">{t("agenda.services")}</legend>
        {services.data
          ?.filter((s) => s.is_active)
          .map((s) => (
            <CheckboxField
              key={s.id}
              label={s.name}
              value={s.id}
              {...form.register("service_ids", { onChange: clearSlot })}
            />
          ))}
        {errors.service_ids && <Notice tone="danger">{t("common.required")}</Notice>}
      </fieldset>
      <SelectField
        label={t("agenda.professional")}
        {...form.register("professional_id", { onChange: clearSlot })}
      >
        <option value="">{t("agenda.anyone")}</option>
        {professionals.data
          ?.filter((p) => p.is_active)
          .map((p) => (
            <option key={p.id} value={p.id}>
              {p.display_name}
            </option>
          ))}
      </SelectField>
      <TextField
        type="date"
        label={t("agenda.date")}
        error={errors.date?.message}
        {...form.register("date", { onChange: clearSlot })}
      />
      <SlotPicker
        serviceIds={values.service_ids ?? []}
        professionalId={values.professional_id ?? ""}
        date={values.date ?? ""}
        value={values.start_at ?? ""}
        onChange={(start) => form.setValue("start_at", start, { shouldValidate: true })}
      />
      {errors.start_at && <Notice tone="danger">{t("common.required")}</Notice>}
      {values.start_at && (
        <p className="text-sm font-medium" role="status">
          {t("agenda.selectedTime", { time: formatDateTime(values.start_at, i18n.language, zone) })}
        </p>
      )}
      <SelectField label={t("agenda.customer")} {...form.register("customer_mode")}>
        <option value="existing">{t("agenda.existingCustomer")}</option>
        <option value="new">{t("agenda.newCustomer")}</option>
      </SelectField>
      {values.customer_mode === "existing" ? (
        <>
          <TextField
            label={t("common.search")}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              form.setValue("customer_id", "");
            }}
          />
          {customers.isPending && <Loading />}
          {customers.isError && (
            <ErrorBox
              message={describeError(t, customers.error)}
              onRetry={() => void customers.refetch()}
            />
          )}
          {customers.isSuccess && !customers.data.pages[0].results.length && (
            <EmptyState>{t("agenda.emptyCustomers")}</EmptyState>
          )}
          <SelectField
            label={t("agenda.customer")}
            disabled={search !== debouncedSearch || customers.isFetching}
            error={errors.customer_id?.message}
            {...form.register("customer_id")}
          >
            <option value="">{t("agenda.chooseCustomer")}</option>
            {customers.data?.pages
              .flatMap((p) => p.results)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name} · {c.phone}
                </option>
              ))}
          </SelectField>
          {customers.hasNextPage && (
            <Button
              variant="secondary"
              disabled={customers.isFetchingNextPage}
              onClick={() => void customers.fetchNextPage()}
            >
              {t("common.loadMore")}
            </Button>
          )}
        </>
      ) : (
        <>
          <TextField
            label={t("agenda.fullName")}
            error={errors.full_name?.message}
            {...form.register("full_name")}
          />
          <TextField
            label={t("agenda.phone")}
            type="tel"
            error={errors.phone?.message}
            {...form.register("phone")}
          />
          <TextField
            label={t("agenda.email")}
            type="email"
            optional
            error={errors.email?.message}
            {...form.register("email")}
          />
          <CheckboxField label={t("agenda.marketing")} {...form.register("marketing_consent")} />
        </>
      )}
      {save.isError && <Notice tone="danger">{describeError(t, save.error)}</Notice>}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((start) => (
            <Button
              key={start}
              variant="secondary"
              aria-pressed={values.start_at === start}
              onClick={() => {
                form.setValue("date", todayIn(zone, new Date(start)));
                form.setValue("start_at", start, { shouldValidate: true });
              }}
            >
              {formatDateTime(start, i18n.language, zone)}
            </Button>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={save.isPending}>
          {t(save.isPending ? "common.saving" : "common.save")}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}

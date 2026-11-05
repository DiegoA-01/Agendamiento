import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../../shared/api/client";
import { applyServerErrors, describeError } from "../../../shared/api/errors";
import type { CustomerRecord } from "../../../shared/api/types";
import {
  Button,
  CheckboxField,
  Notice,
  TextAreaField,
  TextField,
} from "../../../shared/ui/primitives";
import { KEYS } from "../shared/api";
import { customerSchema, type CustomerValues } from "../appointments/schemas";

export function CustomerForm({
  customer,
  onDone,
}: {
  customer?: CustomerRecord;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const form = useForm<CustomerValues>({
    resolver: zodResolver(customerSchema),
    defaultValues: {
      full_name: customer?.full_name ?? "",
      phone: customer?.phone ?? "",
      email: customer?.email ?? "",
      birthday: customer?.birthday ?? "",
      notes: customer?.notes ?? "",
      marketing_consent: customer?.marketing_consent ?? false,
      data_consent: false,
    },
  });
  const errors = form.formState.errors;
  const save = useMutation({
    mutationFn: (values: CustomerValues) => {
      const body = {
        full_name: values.full_name,
        phone: values.phone,
        email: values.email,
        birthday: values.birthday || null,
        notes: values.notes,
        marketing_consent: values.marketing_consent,
        ...(!customer ? { data_consent: true } : {}),
      };
      return api<CustomerRecord>(
        customer ? `/api/v1/customers/${customer.id}/` : "/api/v1/customers/",
        { method: customer ? "PATCH" : "POST", body },
      );
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: KEYS.customers });
      void client.invalidateQueries({ queryKey: KEYS.appointments });
      onDone();
    },
    onError: (error) => {
      applyServerErrors(error, form.setError, [
        "full_name",
        "phone",
        "email",
        "birthday",
        "notes",
        "marketing_consent",
        "data_consent",
      ]);
      if (error instanceof ApiError && error.code === "customer_exists")
        form.setError("phone", { type: "server", message: t("errors.customer_exists") });
    },
  });
  return (
    <form
      className="grid gap-4 sm:grid-cols-2"
      noValidate
      onSubmit={form.handleSubmit((values) => {
        if (!customer && !values.data_consent) {
          form.setError("data_consent", { type: "validate", message: "required" });
          return;
        }
        save.mutate(values);
      })}
    >
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
      <TextField
        label={t("agenda.birthday")}
        type="date"
        optional
        error={errors.birthday?.message}
        {...form.register("birthday")}
      />
      <div className="sm:col-span-2">
        <TextAreaField
          label={t("agenda.notes")}
          optional
          error={errors.notes?.message}
          {...form.register("notes")}
        />
      </div>
      <CheckboxField label={t("agenda.marketing")} {...form.register("marketing_consent")} />
      {!customer && (
        <div className="space-y-2 sm:col-span-2">
          <CheckboxField label={t("agenda.dataConsent")} {...form.register("data_consent")} />
          {errors.data_consent && <Notice tone="danger">{t("common.required")}</Notice>}
        </div>
      )}
      {save.isError && (
        <div className="sm:col-span-2">
          <Notice tone="danger">{describeError(t, save.error)}</Notice>
        </div>
      )}
      <div className="flex gap-2 sm:col-span-2">
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

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../../shared/api/client";
import { applyServerErrors, describeError } from "../../shared/api/errors";
import { LANGUAGES, VERTICALS, type TenantCreated } from "../../shared/api/types";
import { baseDomainFrom, tenantUrl } from "../../shared/format";
import {
  Button,
  Card,
  CopyButton,
  Loading,
  Notice,
  PageHeader,
  SelectField,
  TextField,
} from "../../shared/ui/primitives";
import { usePlans } from "./api";
import { tenantCreateSchema, type TenantCreateValues } from "./schemas";

const FIELDS = [
  "name",
  "slug",
  "plan_id",
  "vertical",
  "timezone",
  "currency",
  "language",
  "owner_name",
  "owner_email",
] as const;

export function TenantCreatePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const plans = usePlans();
  const [created, setCreated] = useState<TenantCreated | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const form = useForm<TenantCreateValues>({
    resolver: zodResolver(tenantCreateSchema),
    defaultValues: {
      name: "",
      slug: "",
      plan_id: "",
      vertical: "barbershop",
      timezone: "America/Bogota",
      currency: "COP",
      language: "es",
      owner_name: "",
      owner_email: "",
    },
  });
  const { errors } = form.formState;
  const slug = useWatch({ control: form.control, name: "slug" });

  const create = useMutation({
    mutationFn: (values: TenantCreateValues) =>
      api<TenantCreated>("/api/v1/tenants/", { method: "POST", body: values }),
    onSuccess: (result) => {
      setCreated(result);
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
    },
    onError: (error) => {
      setMessage(null);
      if (!applyServerErrors(error, form.setError, FIELDS)) setMessage(describeError(t, error));
    },
  });

  if (created) {
    return (
      <>
        <PageHeader title={t("tenants.createdTitle")} />
        <Card className="flex flex-col gap-4">
          <p>{t("tenants.createdIntro", { name: created.tenant.name })}</p>
          <dl className="grid gap-3 text-sm sm:grid-cols-[10rem_1fr]">
            <dt className="font-medium">{t("tenants.createdAddress")}</dt>
            <dd className="font-mono break-all">
              {tenantUrl(created.tenant.slug, window.location)}
            </dd>
            <dt className="font-medium">{t("tenants.createdEmail")}</dt>
            <dd className="font-mono break-all">{created.owner.email}</dd>
            <dt className="font-medium">{t("tenants.tempPassword")}</dt>
            <dd className="flex flex-wrap items-center gap-3">
              <code className="rounded bg-slate-100 px-3 py-1.5 font-mono text-base break-all">
                {created.temporary_password}
              </code>
              <CopyButton value={created.temporary_password} />
            </dd>
          </dl>
          <Notice tone="warning">{t("tenants.tempPasswordWarning")}</Notice>
          <div className="flex flex-wrap gap-2">
            <a
              href={tenantUrl(created.tenant.slug, window.location)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-10 items-center rounded-lg border border-slate-300 px-4 text-sm font-medium hover:bg-slate-50"
            >
              {t("tenants.openSite")}
            </a>
            <Link
              to={`/empresas/${created.tenant.id}`}
              className="inline-flex min-h-10 items-center rounded-lg bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-700"
            >
              {t("tenants.goToDetail")}
            </Link>
            <Button
              variant="ghost"
              onClick={() => {
                setCreated(null);
                form.reset();
              }}
            >
              {t("tenants.createAnother")}
            </Button>
          </div>
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader title={t("tenants.createTitle")} />
      {plans.isPending && <Loading />}
      {plans.isSuccess && (
        <form
          onSubmit={form.handleSubmit((values) => create.mutate(values))}
          noValidate
          className="flex max-w-2xl flex-col gap-5"
        >
          {message && <Notice tone="danger">{message}</Notice>}
          {plans.data.length === 0 && (
            <Notice tone="warning">
              {t("tenants.noPlans")}{" "}
              <Link to="/planes" className="underline">
                {t("nav.plans")}
              </Link>
            </Notice>
          )}
          <Card className="grid gap-4 sm:grid-cols-2">
            <TextField
              label={t("tenants.name")}
              autoComplete="off"
              error={errors.name?.message}
              {...form.register("name")}
            />
            <TextField
              label={t("tenants.slug")}
              autoComplete="off"
              spellCheck={false}
              hint={t("tenants.slugHelp", {
                slug: slug || "…",
                domain: baseDomainFrom(window.location.host),
              })}
              error={errors.slug?.message}
              {...form.register("slug")}
            />
            <SelectField
              label={t("tenants.plan")}
              error={errors.plan_id?.message}
              {...form.register("plan_id")}
            >
              <option value="">{t("tenants.planPlaceholder")}</option>
              {plans.data.map((plan) => (
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
          </Card>

          <Card className="grid gap-4 sm:grid-cols-2">
            <h2 className="text-sm font-semibold text-slate-900 sm:col-span-2">
              {t("tenants.ownerSection")}
            </h2>
            <TextField
              label={t("tenants.ownerName")}
              autoComplete="off"
              error={errors.owner_name?.message}
              {...form.register("owner_name")}
            />
            <TextField
              label={t("tenants.ownerEmail")}
              type="email"
              autoComplete="off"
              error={errors.owner_email?.message}
              {...form.register("owner_email")}
            />
          </Card>

          <div>
            <Button type="submit" disabled={create.isPending || plans.data.length === 0}>
              {create.isPending ? t("tenants.submitting") : t("tenants.submit")}
            </Button>
          </div>
        </form>
      )}
    </>
  );
}

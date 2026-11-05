import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api } from "../../../shared/api/client";
import { applyServerErrors, describeError } from "../../../shared/api/errors";
import {
  SOCIAL_NETWORKS,
  type BusinessLocation,
  type Company,
  type ImageRef,
} from "../../../shared/api/types";
import {
  Button,
  Card,
  ErrorBox,
  Loading,
  Notice,
  PageHeader,
  TextAreaField,
  TextField,
} from "../../../shared/ui/primitives";
import { KEYS, useCompany, useLocations } from "../shared/api";
import { ImageField } from "../shared/ImageField";
import {
  companyPayload,
  companySchema,
  companyToValues,
  type CompanyValues,
} from "../shared/schemas";
import { useCan } from "../shared/useCan";

type Message = { tone: "success" | "danger"; text: string } | null;

const SERVER_FIELDS = [
  "trade_name",
  "legal_name",
  "tax_id",
  "address",
  "city",
  "phone",
  "email",
  "terms_html",
  "privacy_html",
  "cookies_html",
] as const;
const LEGAL_FIELDS = ["terms_html", "privacy_html", "cookies_html"] as const;

function LogoCard({ company, editable }: { company: Company; editable: boolean }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: (logo: ImageRef | null) =>
      api<Company>("/api/v1/company/", { method: "PATCH", body: { logo_id: logo?.id ?? null } }),
    onSuccess: (updated) => queryClient.setQueryData(KEYS.company, updated),
  });
  return (
    <Card>
      <ImageField
        label={t("catalog.company.logo")}
        value={company.logo}
        onChange={(logo) => save.mutate(logo)}
        disabled={!editable || save.isPending}
      />
      {save.isError && <Notice tone="danger">{describeError(t, save.error)}</Notice>}
    </Card>
  );
}

function CompanyForm({ company, editable }: { company: Company; editable: boolean }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<Message>(null);
  const form = useForm<CompanyValues>({
    resolver: zodResolver(companySchema),
    values: companyToValues(company),
  });
  const { errors } = form.formState;

  const save = useMutation({
    mutationFn: (values: CompanyValues) =>
      api<Company>("/api/v1/company/", { method: "PATCH", body: companyPayload(values) }),
    onSuccess: (updated) => {
      queryClient.setQueryData(KEYS.company, updated);
      // El HTML legal vuelve limpio del servidor: el formulario muestra lo que quedó guardado.
      form.reset(companyToValues(updated));
      setMessage({ tone: "success", text: t("common.saved") });
    },
    onError: (error) => {
      setMessage(null);
      if (!applyServerErrors(error, form.setError, SERVER_FIELDS)) {
        setMessage({ tone: "danger", text: describeError(t, error) });
      }
    },
  });

  return (
    <form onSubmit={form.handleSubmit((values) => save.mutate(values))} noValidate>
      <fieldset disabled={!editable} className="flex flex-col gap-5">
        {message && <Notice tone={message.tone}>{message.text}</Notice>}
        <Card className="grid gap-4 sm:grid-cols-2">
          <h2 className="text-lg font-semibold sm:col-span-2">{t("catalog.company.data")}</h2>
          <TextField
            label={t("catalog.company.tradeName")}
            error={errors.trade_name?.message}
            {...form.register("trade_name")}
          />
          <TextField
            label={t("catalog.company.legalName")}
            optional
            error={errors.legal_name?.message}
            {...form.register("legal_name")}
          />
          <TextField
            label={t("catalog.company.taxId")}
            optional
            error={errors.tax_id?.message}
            {...form.register("tax_id")}
          />
          <TextField
            label={t("catalog.company.phone")}
            type="tel"
            optional
            error={errors.phone?.message}
            {...form.register("phone")}
          />
          <TextField
            label={t("catalog.company.email")}
            type="email"
            optional
            error={errors.email?.message}
            {...form.register("email")}
          />
          <TextField
            label={t("catalog.company.city")}
            optional
            error={errors.city?.message}
            {...form.register("city")}
          />
          <div className="sm:col-span-2">
            <TextField
              label={t("catalog.company.address")}
              optional
              error={errors.address?.message}
              {...form.register("address")}
            />
          </div>
        </Card>

        <Card className="grid gap-4 sm:grid-cols-2">
          <h2 className="text-lg font-semibold sm:col-span-2">{t("catalog.company.social")}</h2>
          {SOCIAL_NETWORKS.map((network) => (
            <TextField
              key={network}
              label={t(`catalog.company.networks.${network}`)}
              type="url"
              placeholder="https://"
              optional
              error={errors.social?.[network]?.message}
              {...form.register(`social.${network}`)}
            />
          ))}
        </Card>

        <Card className="flex flex-col gap-4">
          <div>
            <h2 className="text-lg font-semibold">{t("catalog.company.legal")}</h2>
            <p className="mt-1 text-sm text-slate-600">{t("catalog.company.legalHint")}</p>
          </div>
          {LEGAL_FIELDS.map((field) => (
            <TextAreaField
              key={field}
              label={t(`catalog.company.${field}`)}
              rows={6}
              optional
              error={errors[field]?.message}
              {...form.register(field)}
            />
          ))}
        </Card>

        {editable && (
          <div>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? t("common.saving") : t("common.save")}
            </Button>
          </div>
        )}
      </fieldset>
    </form>
  );
}

/** El MVP usa una sola sede (la spec deja la UI multisede fuera de alcance): aquí se edita la
 *  principal. La API ya admite más para cuando el plan lo permita. */
function MainLocationCard({ editable }: { editable: boolean }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const locations = useLocations();
  const main = locations.data?.find((location) => location.is_default);
  const [message, setMessage] = useState<Message>(null);
  const form = useForm<{ name: string; address: string }>({
    values: { name: main?.name ?? "", address: main?.address ?? "" },
  });

  const save = useMutation({
    mutationFn: (values: { name: string; address: string }) =>
      api<BusinessLocation>(`/api/v1/locations/${main?.id}/`, { method: "PATCH", body: values }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.locations });
      setMessage({ tone: "success", text: t("common.saved") });
    },
    onError: (error) => setMessage({ tone: "danger", text: describeError(t, error) }),
  });

  if (locations.isPending) return <Loading />;
  if (locations.isError || !main) {
    return (
      <ErrorBox
        message={describeError(t, locations.error)}
        onRetry={() => void locations.refetch()}
      />
    );
  }
  return (
    <Card>
      <form onSubmit={form.handleSubmit((values) => save.mutate(values))} noValidate>
        <fieldset disabled={!editable} className="grid gap-4 sm:grid-cols-2">
          <h2 className="text-lg font-semibold sm:col-span-2">{t("catalog.company.location")}</h2>
          {message && (
            <div className="sm:col-span-2">
              <Notice tone={message.tone}>{message.text}</Notice>
            </div>
          )}
          <TextField
            label={t("catalog.company.locationName")}
            required
            {...form.register("name", { required: true })}
          />
          <TextField label={t("catalog.company.address")} optional {...form.register("address")} />
          {editable && (
            <div>
              <Button type="submit" variant="secondary" disabled={save.isPending}>
                {save.isPending ? t("common.saving") : t("common.save")}
              </Button>
            </div>
          )}
        </fieldset>
      </form>
    </Card>
  );
}

export default function CompanyPage() {
  const { t } = useTranslation();
  const company = useCompany();
  const editable = useCan("company", "update");

  return (
    <>
      <PageHeader
        title={t("dashboard.nav.company")}
        description={editable ? t("catalog.company.intro") : t("catalog.readOnly")}
      />
      {company.isPending && <Loading />}
      {company.isError && (
        <ErrorBox
          message={describeError(t, company.error)}
          onRetry={() => void company.refetch()}
        />
      )}
      {company.isSuccess && (
        <div className="flex flex-col gap-5">
          <LogoCard company={company.data} editable={editable} />
          <CompanyForm company={company.data} editable={editable} />
          <MainLocationCard editable={editable} />
        </div>
      )}
    </>
  );
}

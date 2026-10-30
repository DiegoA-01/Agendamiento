import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { api } from "../../shared/api/client";
import { applyServerErrors, describeError } from "../../shared/api/errors";
import type { Domain, DomainVerification, TenantDetail } from "../../shared/api/types";
import {
  Badge,
  Button,
  Card,
  CopyButton,
  EmptyState,
  ErrorBox,
  Loading,
  Notice,
  TextField,
} from "../../shared/ui/primitives";
import { useTenantDomains } from "./api";
import { domainSchema, type DomainValues } from "./schemas";

function DnsRecord({
  title,
  help,
  rows,
}: {
  title: string;
  help: string;
  rows: [string, string][];
}) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold">{title}</h4>
      <p className="text-sm text-slate-600">{help}</p>
      <dl className="grid gap-2 text-sm sm:grid-cols-[7rem_1fr]">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="font-medium">{label}</dt>
            <dd className="flex flex-wrap items-center gap-2">
              <code className="rounded bg-slate-100 px-2 py-1 font-mono break-all">{value}</code>
              <CopyButton value={value} />
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function DomainRow({ tenantId, domain }: { tenantId: string; domain: Domain }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [result, setResult] = useState<DomainVerification | null>(null);
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["tenant", tenantId, "domains"] });

  const verify = useMutation({
    mutationFn: () =>
      api<DomainVerification>(`/api/v1/tenants/${tenantId}/domains/${domain.id}/verify/`, {
        method: "POST",
      }),
    onSuccess: (data) => {
      setResult(data);
      void invalidate();
    },
  });
  const remove = useMutation({
    mutationFn: () =>
      api<void>(`/api/v1/tenants/${tenantId}/domains/${domain.id}/`, { method: "DELETE" }),
    onSuccess: () => void invalidate(),
  });

  const custom = domain.kind === "custom";
  return (
    <li className="flex flex-col gap-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-sm font-medium break-all">{domain.host}</span>
          <Badge>{custom ? t("domains.kindCustom") : t("domains.kindSubdomain")}</Badge>
          <Badge tone={domain.verified ? "success" : "warning"}>
            {domain.verified ? t("domains.verified") : t("domains.pending")}
          </Badge>
        </div>
        {custom && (
          <div className="flex gap-2">
            {!domain.verified && (
              <Button onClick={() => verify.mutate()} disabled={verify.isPending}>
                {verify.isPending ? t("domains.verifying") : t("domains.verify")}
              </Button>
            )}
            <Button variant="danger" onClick={() => remove.mutate()} disabled={remove.isPending}>
              {t("domains.remove")}
            </Button>
          </div>
        )}
      </div>

      {verify.isError && <Notice tone="danger">{describeError(t, verify.error)}</Notice>}
      {remove.isError && <Notice tone="danger">{describeError(t, remove.error)}</Notice>}
      {result && (
        <div className="flex flex-col gap-2">
          {result.verified ? (
            <Notice tone="success">{t("domains.verifyDone")}</Notice>
          ) : (
            <Notice tone="warning">{t("domains.verifyTxtMissing")}</Notice>
          )}
          <Notice tone={result.cname_ok ? "success" : "info"}>
            {result.cname_ok ? t("domains.cnameFound") : t("domains.cnameMissing")}
          </Notice>
        </div>
      )}

      {custom && !domain.verified && (
        <div className="flex flex-col gap-4 rounded-lg bg-slate-50 p-4">
          <div>
            <h3 className="text-sm font-semibold">
              {t("domains.stepsTitle", { host: domain.host })}
            </h3>
            <p className="text-sm text-slate-600">{t("domains.stepsIntro")}</p>
          </div>
          <DnsRecord
            title={t("domains.txtTitle")}
            help={t("domains.txtHelp")}
            rows={[
              [t("domains.name"), domain.instructions.txt.name],
              [t("domains.value"), domain.instructions.txt.value],
            ]}
          />
          <DnsRecord
            title={t("domains.cnameTitle")}
            help={t("domains.cnameHelp")}
            rows={[
              [t("domains.name"), domain.instructions.cname.name],
              [t("domains.target"), domain.instructions.cname.target],
            ]}
          />
        </div>
      )}
    </li>
  );
}

export function DomainsTab({ tenant }: { tenant: TenantDetail }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const domains = useTenantDomains(tenant.id);
  const [message, setMessage] = useState<string | null>(null);

  const form = useForm<DomainValues>({
    resolver: zodResolver(domainSchema),
    defaultValues: { host: "" },
  });

  const add = useMutation({
    mutationFn: (values: DomainValues) =>
      api<Domain>(`/api/v1/tenants/${tenant.id}/domains/`, { method: "POST", body: values }),
    onSuccess: () => {
      form.reset();
      setMessage(null);
      void queryClient.invalidateQueries({ queryKey: ["tenant", tenant.id, "domains"] });
    },
    onError: (error) => {
      setMessage(null);
      if (!applyServerErrors(error, form.setError, ["host"])) setMessage(describeError(t, error));
    },
  });

  const customCount = domains.data?.filter((domain) => domain.kind === "custom").length ?? 0;

  return (
    <div className="flex flex-col gap-5">
      <p className="max-w-prose text-sm text-slate-600">{t("domains.intro")}</p>
      <Card>
        <form
          onSubmit={form.handleSubmit((values) => add.mutate(values))}
          noValidate
          className="flex flex-wrap items-start gap-3"
        >
          <div className="min-w-64 flex-1">
            <TextField
              label={t("domains.hostLabel")}
              placeholder={t("domains.hostPlaceholder")}
              autoComplete="off"
              spellCheck={false}
              error={form.formState.errors.host?.message}
              {...form.register("host")}
            />
          </div>
          <Button type="submit" className="mt-6" disabled={add.isPending}>
            {t("domains.add")}
          </Button>
        </form>
        {message && (
          <div className="mt-3">
            <Notice tone="danger">{message}</Notice>
          </div>
        )}
      </Card>

      {domains.isPending && <Loading />}
      {domains.isError && (
        <ErrorBox
          message={describeError(t, domains.error)}
          onRetry={() => void domains.refetch()}
        />
      )}
      {domains.isSuccess && (
        <Card>
          <ul className="divide-y divide-slate-100">
            {domains.data.map((domain) => (
              <DomainRow key={domain.id} tenantId={tenant.id} domain={domain} />
            ))}
          </ul>
          {customCount === 0 && <EmptyState>{t("domains.empty")}</EmptyState>}
        </Card>
      )}
    </div>
  );
}

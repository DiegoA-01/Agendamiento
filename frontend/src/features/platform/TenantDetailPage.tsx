import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import type { TenantDetail } from "../../shared/api/types";
import { tenantUrl } from "../../shared/format";
import {
  Badge,
  Button,
  Card,
  ErrorBox,
  Loading,
  Notice,
  PageHeader,
  TextField,
} from "../../shared/ui/primitives";
import { useTenant } from "./api";
import { DomainsTab } from "./DomainsTab";
import { InfoTab } from "./InfoTab";
import { ModulesTab } from "./ModulesTab";
import { ThemeTab } from "./ThemeTab";

const TABS = ["info", "theme", "modules", "domains"] as const;
type Tab = (typeof TABS)[number];

function StatusAndDanger({ tenant }: { tenant: TenantDetail }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [confirmSlug, setConfirmSlug] = useState("");

  const suspended = tenant.status === "suspended";
  const toggle = useMutation({
    mutationFn: () =>
      api<TenantDetail>(`/api/v1/tenants/${tenant.id}/${suspended ? "activate" : "suspend"}/`, {
        method: "POST",
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["tenant", tenant.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
    },
  });
  const remove = useMutation({
    mutationFn: () => api<void>(`/api/v1/tenants/${tenant.id}/`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["tenant", tenant.id] });
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
      navigate("/empresas", { replace: true });
    },
  });

  return (
    <Card className="mt-8 border-red-200">
      <h2 className="text-sm font-semibold text-red-900">{t("tenants.detail.dangerZone")}</h2>
      {(toggle.isError || remove.isError) && (
        <div className="mt-3">
          <Notice tone="danger">{describeError(t, toggle.error ?? remove.error)}</Notice>
        </div>
      )}
      <div className="mt-4 flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-prose text-sm text-slate-600">{t("tenants.detail.suspendHelp")}</p>
          <Button
            variant={suspended ? "primary" : "danger"}
            onClick={() => toggle.mutate()}
            disabled={toggle.isPending}
          >
            {suspended ? t("tenants.detail.activate") : t("tenants.detail.suspend")}
          </Button>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-64 flex-1">
            <TextField
              label={t("tenants.detail.delete")}
              hint={t("tenants.detail.deleteHelp", { slug: tenant.slug })}
              value={confirmSlug}
              onChange={(event) => setConfirmSlug(event.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <Button
            variant="danger"
            onClick={() => remove.mutate()}
            disabled={remove.isPending || confirmSlug.trim() !== tenant.slug}
          >
            {t("tenants.detail.deleteConfirm")}
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function TenantDetailPage() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const tenant = useTenant(id);
  const [tab, setTab] = useState<Tab>("info");

  if (tenant.isPending) return <Loading />;
  if (tenant.isError) {
    const notFound = tenant.error instanceof ApiError && tenant.error.status === 404;
    return (
      <>
        <Link to="/empresas" className="text-sm underline">
          {t("common.back")}
        </Link>
        <div className="mt-4">
          <ErrorBox
            message={describeError(t, tenant.error)}
            onRetry={notFound ? undefined : () => void tenant.refetch()}
          />
        </div>
      </>
    );
  }

  const data = tenant.data;

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = TABS.indexOf(tab);
    if (event.key === "ArrowRight") setTab(TABS[(index + 1) % TABS.length]);
    else if (event.key === "ArrowLeft") setTab(TABS[(index + TABS.length - 1) % TABS.length]);
    else return;
    event.preventDefault();
    window.requestAnimationFrame(() =>
      document.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')?.focus(),
    );
  }

  return (
    <>
      <Link to="/empresas" className="text-sm text-slate-700 underline">
        ← {t("tenants.title")}
      </Link>
      <div className="mt-3">
        <PageHeader
          title={data.name}
          description={tenantUrl(data.slug, window.location)}
          actions={
            <Badge tone={data.status === "active" ? "success" : "warning"}>
              {t(`tenants.status.${data.status}`)}
            </Badge>
          }
        />
      </div>

      <div
        role="tablist"
        aria-label={t("tenants.detail.tabs")}
        onKeyDown={onKeyDown}
        className="mb-5 flex flex-wrap gap-1 border-b border-slate-200"
      >
        {TABS.map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            id={`tab-${name}`}
            aria-selected={tab === name}
            aria-controls={`panel-${name}`}
            tabIndex={tab === name ? 0 : -1}
            onClick={() => setTab(name)}
            className={`-mb-px rounded-t-lg border-b-2 px-4 py-2 text-sm font-medium ${
              tab === name
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            {t(`tenants.detail.${name}`)}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "info" && <InfoTab tenant={data} />}
        {tab === "theme" && <ThemeTab tenant={data} />}
        {tab === "modules" && <ModulesTab tenant={data} />}
        {tab === "domains" && <DomainsTab tenant={data} />}
      </div>

      <StatusAndDanger tenant={data} />
    </>
  );
}

import { useDeferredValue, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { describeError } from "../../shared/api/errors";
import { formatDate } from "../../shared/format";
import {
  Badge,
  Button,
  EmptyState,
  ErrorBox,
  Loading,
  PageHeader,
  SelectField,
  TextField,
} from "../../shared/ui/primitives";
import { useTenantList } from "./api";

export function TenantsPage() {
  const { t, i18n } = useTranslation();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const query = useTenantList({ q: deferredSearch, status });

  const tenants = query.data?.pages.flatMap((page) => page.results) ?? [];
  const filtered = deferredSearch !== "" || status !== "";

  return (
    <>
      <PageHeader
        title={t("tenants.title")}
        actions={
          <Link
            to="/empresas/nueva"
            className="inline-flex min-h-10 items-center rounded-lg bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-700"
          >
            {t("tenants.newButton")}
          </Link>
        }
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_12rem]">
        <TextField
          label={t("tenants.searchLabel")}
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <SelectField
          label={t("tenants.statusLabel")}
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">{t("common.all")}</option>
          <option value="active">{t("tenants.status.active")}</option>
          <option value="suspended">{t("tenants.status.suspended")}</option>
        </SelectField>
      </div>

      {query.isPending && <Loading />}
      {query.isError && (
        <ErrorBox message={describeError(t, query.error)} onRetry={() => void query.refetch()} />
      )}
      {query.isSuccess && tenants.length === 0 && (
        <EmptyState>{filtered ? t("tenants.emptyFiltered") : t("tenants.empty")}</EmptyState>
      )}
      {tenants.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-700">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("tenants.colName")}
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("tenants.colSubdomain")}
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("tenants.colPlan")}
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("tenants.colStatus")}
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("tenants.colCreated")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tenants.map((tenant) => (
                <tr key={tenant.id}>
                  <th scope="row" className="px-4 py-3 font-medium">
                    <Link to={`/empresas/${tenant.id}`} className="text-slate-900 underline">
                      {tenant.name}
                    </Link>
                  </th>
                  <td className="px-4 py-3 font-mono text-slate-700">{tenant.slug}</td>
                  <td className="px-4 py-3">{tenant.plan.name}</td>
                  <td className="px-4 py-3">
                    <Badge tone={tenant.status === "active" ? "success" : "warning"}>
                      {t(`tenants.status.${tenant.status}`)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatDate(tenant.created_at, i18n.language)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {query.hasNextPage && (
        <div className="mt-4 text-center">
          <Button
            variant="secondary"
            onClick={() => void query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
          >
            {query.isFetchingNextPage ? t("common.loading") : t("common.loadMore")}
          </Button>
        </div>
      )}
    </>
  );
}

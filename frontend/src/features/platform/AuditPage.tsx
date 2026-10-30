import { useState } from "react";
import { useTranslation } from "react-i18next";
import { describeError } from "../../shared/api/errors";
import { formatDateTime } from "../../shared/format";
import {
  Button,
  EmptyState,
  ErrorBox,
  Loading,
  PageHeader,
  SelectField,
} from "../../shared/ui/primitives";
import { AUDIT_ACTIONS, useAuditList } from "./api";

export function AuditPage() {
  const { t, i18n } = useTranslation();
  const [action, setAction] = useState("");
  const query = useAuditList({ action });
  const entries = query.data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <>
      <PageHeader title={t("audit.title")} description={t("audit.intro")} />
      <div className="mb-4 max-w-xs">
        <SelectField
          label={t("audit.actionLabel")}
          value={action}
          onChange={(event) => setAction(event.target.value)}
        >
          <option value="">{t("common.all")}</option>
          {AUDIT_ACTIONS.map((name) => (
            <option key={name} value={name}>
              {t(`audit.actions.${name}`)}
            </option>
          ))}
        </SelectField>
      </div>

      {query.isPending && <Loading />}
      {query.isError && (
        <ErrorBox message={describeError(t, query.error)} onRetry={() => void query.refetch()} />
      )}
      {query.isSuccess && entries.length === 0 && <EmptyState>{t("audit.empty")}</EmptyState>}
      {entries.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full min-w-[44rem] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-700">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("audit.colWhen")}
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("audit.colWho")}
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("audit.colAction")}
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  {t("audit.colTenant")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.map((entry) => (
                <tr key={entry.id} className="align-top">
                  <td className="px-4 py-3 whitespace-nowrap text-slate-600">
                    {formatDateTime(entry.created_at, i18n.language)}
                  </td>
                  <td className="px-4 py-3">{entry.actor_email ?? "—"}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium">
                      {t(`audit.actions.${entry.action}`, { defaultValue: entry.action })}
                    </p>
                    {(entry.before !== null || entry.after !== null) && (
                      <details className="mt-1 text-xs text-slate-600">
                        <summary className="cursor-pointer">{t("audit.details")}</summary>
                        <div className="mt-2 grid gap-2">
                          {entry.before !== null && (
                            <div>
                              <strong>{t("audit.before")}</strong>
                              <pre className="overflow-x-auto rounded bg-slate-50 p-2">
                                {JSON.stringify(entry.before, null, 2)}
                              </pre>
                            </div>
                          )}
                          {entry.after !== null && (
                            <div>
                              <strong>{t("audit.after")}</strong>
                              <pre className="overflow-x-auto rounded bg-slate-50 p-2">
                                {JSON.stringify(entry.after, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </details>
                    )}
                  </td>
                  <td className="px-4 py-3">{entry.tenant_name ?? "—"}</td>
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

import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { describeError } from "../../shared/api/errors";
import { formatDate } from "../../shared/format";
import { Badge, Card, EmptyState, ErrorBox, Loading, PageHeader } from "../../shared/ui/primitives";
import { usePlatformSummary } from "./api";
import { share } from "./summary";

function Breakdown({
  title,
  rows,
  total,
}: {
  title: string;
  rows: { key: string; label: string; count: number }[];
  total: number;
}) {
  const { i18n } = useTranslation();
  return (
    <Card className="min-w-0">
      <h2 className="mb-3 font-semibold text-slate-900">{title}</h2>
      <ul className="space-y-3">
        {rows.map((row) => {
          const percent = share(row.count, total);
          return (
            <li key={row.key}>
              <div className="flex justify-between gap-3 text-sm">
                <span className="min-w-0 truncate">{row.label}</span>
                <span className="text-slate-700 tabular-nums">
                  {row.count.toLocaleString(i18n.language)} · {percent}%
                </span>
              </div>
              <div className="mt-1 h-2 rounded-full bg-slate-100" aria-hidden="true">
                <div className="h-2 rounded-full bg-slate-700" style={{ width: `${percent}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

/** Estado de la plataforma para el Super Admin (S6): cuántos negocios hay y cómo están. */
export function SummaryPage() {
  const { t, i18n } = useTranslation();
  const summary = usePlatformSummary();

  if (summary.isPending) return <Loading />;
  if (summary.isError) {
    return (
      <ErrorBox message={describeError(t, summary.error)} onRetry={() => void summary.refetch()} />
    );
  }
  const data = summary.data;
  const number = (value: number) => value.toLocaleString(i18n.language);
  const cards: [string, number][] = [
    [t("summary.total"), data.total],
    [t("summary.active"), data.active],
    [t("summary.suspended"), data.suspended],
    [t("summary.newRecent", { days: data.window_days }), data.new_recent],
  ];

  return (
    <>
      <PageHeader title={t("summary.title")} description={t("summary.description")} />
      <dl className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map(([label, value]) => (
          <Card key={label} className="min-w-0 p-4">
            <dt className="text-sm text-slate-600">{label}</dt>
            <dd className="mt-1 text-2xl font-semibold tabular-nums">{number(value)}</dd>
          </Card>
        ))}
      </dl>

      {data.total === 0 ? (
        <EmptyState>
          {t("summary.empty")}{" "}
          <Link to="/empresas/nueva" className="underline">
            {t("tenants.newButton")}
          </Link>
        </EmptyState>
      ) : (
        <>
          <div className="mb-6 grid gap-3 md:grid-cols-2">
            <Breakdown
              title={t("summary.byPlan")}
              total={data.total}
              rows={data.by_plan.map((row) => ({
                key: row.plan_id,
                label: row.name,
                count: row.count,
              }))}
            />
            <Breakdown
              title={t("summary.byVertical")}
              total={data.total}
              rows={data.by_vertical.map((row) => ({
                key: row.vertical,
                label: t(`verticals.${row.vertical}`),
                count: row.count,
              }))}
            />
          </div>

          <Card className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold text-slate-900">{t("summary.latest")}</h2>
              <Link to="/empresas" className="text-sm underline">
                {t("summary.seeAll")}
              </Link>
            </div>
            <ul className="divide-y divide-slate-100">
              {data.latest.map((tenant) => (
                <li key={tenant.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2">
                  <Link
                    to={`/empresas/${tenant.id}`}
                    className="min-w-0 flex-1 truncate font-medium text-slate-900 underline"
                  >
                    {tenant.name}
                  </Link>
                  <span className="text-sm text-slate-600">{tenant.plan.name}</span>
                  <Badge tone={tenant.status === "active" ? "success" : "warning"}>
                    {t(`tenants.status.${tenant.status}`)}
                  </Badge>
                  <span className="text-sm text-slate-600 tabular-nums">
                    {formatDate(tenant.created_at, i18n.language)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </>
  );
}

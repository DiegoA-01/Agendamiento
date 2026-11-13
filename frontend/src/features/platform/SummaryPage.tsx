import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { describeError } from "../../shared/api/errors";
import { formatDate } from "../../shared/format";
import { ErrorBox, Loading } from "../../shared/ui/primitives";
import { useMe } from "../auth/useMe";
import { usePlatformSummary } from "./api";
import { share } from "./summary";

const GLASS = "glass rounded-[22px] border";

function greetingKey(hour: number) {
  if (hour < 12) return "summary.greetingMorning";
  if (hour < 19) return "summary.greetingAfternoon";
  return "summary.greetingEvening";
}

/** Estado de la plataforma para el Super Admin (S6): cuántos negocios hay y cómo están. */
export function SummaryPage() {
  const { t, i18n } = useTranslation();
  const summary = usePlatformSummary();
  const me = useMe().data;

  if (summary.isPending) return <Loading />;
  if (summary.isError) {
    return (
      <ErrorBox message={describeError(t, summary.error)} onRetry={() => void summary.refetch()} />
    );
  }
  const data = summary.data;
  const number = (value: number) => value.toLocaleString(i18n.language);
  const firstName = me?.user.full_name.trim().split(/\s+/)[0] ?? "";
  const now = new Date();
  const month = new Intl.DateTimeFormat(i18n.language, { month: "long", year: "numeric" }).format(
    now,
  );
  const since = new Date(now.getTime() - data.window_days * 86_400_000);
  const maxPlan = Math.max(1, ...data.by_plan.map((row) => row.count));

  const kpis = [
    {
      label: t("summary.total"),
      value: data.total,
      note: t("summary.totalNote", { count: data.new_recent, days: data.window_days }),
    },
    {
      label: t("summary.active"),
      value: data.active,
      note: t("summary.activeNote", { percent: share(data.active, data.total) }),
    },
    {
      label: t("summary.suspended"),
      value: data.suspended,
      note: data.suspended > 0 ? t("summary.suspendedNote") : t("summary.suspendedNone"),
      alert: data.suspended > 0,
    },
    {
      label: t("summary.newRecent", { days: data.window_days }),
      value: data.new_recent,
      note: t("summary.newNote", { date: formatDate(since.toISOString(), i18n.language) }),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-3xl font-bold tracking-tight">
            {firstName
              ? t(`${greetingKey(now.getHours())}Name`, { name: firstName })
              : t(greetingKey(now.getHours()))}
          </h1>
          <p className="mt-1 text-[var(--pf-muted)] first-letter:uppercase">
            {t("summary.subtitle", { month })}
          </p>
        </div>
        <Link
          to="/empresas/nueva"
          className="metal inline-flex min-h-12 items-center gap-2 rounded-2xl px-5 font-semibold focus-visible:outline-2"
        >
          <span aria-hidden="true" className="text-xl leading-none">
            +
          </span>
          {t("tenants.newButton")}
        </Link>
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className={`${GLASS} flex min-w-0 flex-col gap-1 p-5`}>
            <dt className="text-[var(--pf-muted)]">{kpi.label}</dt>
            <dd className="text-4xl font-bold tracking-tight tabular-nums">{number(kpi.value)}</dd>
            <dd
              className={`text-sm ${kpi.alert ? "font-medium text-red-700" : "text-[var(--pf-muted)]"}`}
            >
              {kpi.note}
            </dd>
          </div>
        ))}
      </dl>

      {data.total === 0 ? (
        <div className={`${GLASS} p-8 text-center`}>
          <p className="text-[var(--pf-muted)]">{t("summary.empty")}</p>
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <section className={`${GLASS} flex flex-col gap-4 p-6`} aria-labelledby="by-plan">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="by-plan" className="text-lg font-semibold">
                {t("summary.byPlan")}
              </h2>
              <Link
                to="/planes"
                className="rounded-xl bg-white/70 px-3 py-1.5 text-sm font-medium ring-1 ring-black/10 hover:bg-white"
              >
                {t("summary.seePlans")}
              </Link>
            </div>
            <div
              className="flex h-60 items-end gap-3 border-b border-black/10 pb-0 sm:gap-5"
              role="list"
            >
              {data.by_plan.map((row) => {
                const top = row.count === maxPlan;
                return (
                  <div
                    key={row.plan_id}
                    role="listitem"
                    className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2"
                  >
                    <span className="text-sm font-semibold tabular-nums">{number(row.count)}</span>
                    <span
                      aria-hidden="true"
                      className={`w-full max-w-24 rounded-t-2xl ${top ? "metal" : "bg-black/[0.07]"}`}
                      style={{ height: `${Math.max(6, (row.count / maxPlan) * 100)}%` }}
                    />
                    <span className="sr-only">{row.name}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex gap-3 sm:gap-5" aria-hidden="true">
              {data.by_plan.map((row) => (
                <span
                  key={row.plan_id}
                  className="min-w-0 flex-1 truncate text-center text-sm text-[var(--pf-muted)]"
                >
                  {row.name}
                </span>
              ))}
            </div>
          </section>

          <section className={`${GLASS} flex flex-col gap-5 p-6`} aria-labelledby="by-vertical">
            <h2 id="by-vertical" className="text-lg font-semibold">
              {t("summary.byVertical")}
            </h2>
            <ul className="flex flex-col gap-5">
              {data.by_vertical.map((row) => {
                const percent = share(row.count, data.total);
                return (
                  <li key={row.vertical} className="flex flex-col gap-2">
                    <div className="flex justify-between gap-3">
                      <span>{t(`verticals.${row.vertical}`)}</span>
                      <span className="font-semibold tabular-nums">
                        {number(row.count)} · {percent}%
                      </span>
                    </div>
                    <div className="h-2.5 rounded-full bg-black/[0.07]" aria-hidden="true">
                      <div className="metal h-2.5 rounded-full" style={{ width: `${percent}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>

          <section
            className={`${GLASS} flex flex-col gap-3 p-6 xl:col-span-2`}
            aria-labelledby="latest"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="latest" className="text-lg font-semibold">
                {t("summary.latest")}
              </h2>
              <Link to="/empresas" className="text-sm font-medium underline underline-offset-4">
                {t("summary.seeAll")}
              </Link>
            </div>
            <ul className="flex flex-col">
              {data.latest.map((tenant) => (
                <li key={tenant.id}>
                  <Link
                    to={`/empresas/${tenant.id}`}
                    className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-2xl px-3 py-3 hover:bg-white/60"
                  >
                    <span className="min-w-0 flex-1 truncate font-medium">{tenant.name}</span>
                    <span className="text-sm text-[var(--pf-muted)]">{tenant.plan.name}</span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        tenant.status === "active"
                          ? "bg-[var(--pf-green-soft)] text-[var(--pf-green-ink)]"
                          : "bg-amber-100 text-amber-900"
                      }`}
                    >
                      {t(`tenants.status.${tenant.status}`)}
                    </span>
                    <span className="w-28 text-right text-sm text-[var(--pf-muted)] tabular-nums">
                      {formatDate(tenant.created_at, i18n.language)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}

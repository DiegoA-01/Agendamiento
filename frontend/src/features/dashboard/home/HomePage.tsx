import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { describeError } from "../../../shared/api/errors";
import { ErrorBox, Loading } from "../../../shared/ui/primitives";
import { useMe } from "../../auth/useMe";
import { useBookingsReport, useSalesReport } from "../reports/api";
import { monthRange, previousMonthRange, todayIn } from "../reports/range";
import { fillMonths, lastMonths, percentChange } from "./months";

const GLASS = "glass rounded-[22px] border";
const MONTHS = 6;

function greetingKey(hour: number) {
  if (hour < 12) return "dashboard.home.greetingMorning";
  if (hour < 19) return "dashboard.home.greetingAfternoon";
  return "dashboard.home.greetingEvening";
}

/** Inicio del panel del negocio: cómo va hoy y este mes, con datos de los reportes (M9). */
export default function HomePage() {
  const { t, i18n } = useTranslation();
  const me = useMe().data;
  const zone = me?.tenant?.timezone ?? "America/Bogota";
  const currency = me?.tenant?.currency ?? "COP";
  const today = todayIn(zone);
  const month = monthRange(today);
  const previous = previousMonthRange(today);
  const months = lastMonths(today, MONTHS);

  const todayBookings = useBookingsReport({ from: today, to: today });
  const monthSales = useSalesReport(month, "service");
  const previousSales = useSalesReport(previous, "day");
  const monthBookings = useBookingsReport(month);
  const history = useSalesReport({ from: `${months[0]}-01`, to: today }, "month");

  const queries = [todayBookings, monthSales, previousSales, monthBookings, history];
  const failed = queries.find((query) => query.isError);
  if (failed?.error) {
    return (
      <ErrorBox
        message={describeError(t, failed.error)}
        onRetry={() => queries.forEach((query) => void query.refetch())}
      />
    );
  }
  if (queries.some((query) => query.isPending)) return <Loading />;

  // Cifras redondas con el símbolo ("$ 160.000"), como en un tablero: los decimales están en Reportes.
  const money = (value: string | number) =>
    // En español con pesos va el formato colombiano: "$ 160.000" (no "160.000 $").
    new Intl.NumberFormat(i18n.language === "es" && currency === "COP" ? "es-CO" : i18n.language, {
      style: "currency",
      currency,
      currencyDisplay: "narrowSymbol",
      maximumFractionDigits: 0,
    }).format(Number(value));
  const number = (value: number) => value.toLocaleString(i18n.language);
  const compact = (value: number) =>
    new Intl.NumberFormat(i18n.language, { notation: "compact", maximumFractionDigits: 1 }).format(
      value,
    );
  const day = todayBookings.data!.totals;
  const sales = monthSales.data!.totals;
  const bookings = monthBookings.data!.totals;
  const change = percentChange(Number(sales.sales), Number(previousSales.data!.totals.sales));
  const chart = fillMonths(months, history.data!.rows);
  const maxSales = Math.max(1, ...chart.map((row) => row.sales));
  const topServices = [...monthSales.data!.rows]
    .sort((a, b) => Number(b.sales) - Number(a.sales))
    .slice(0, 5);
  const maxService = Math.max(1, ...topServices.map((row) => Number(row.sales)));
  const firstName = me?.user.full_name.trim().split(/\s+/)[0] ?? "";
  const monthName = (key: string, style: "short" | "long") =>
    new Intl.DateTimeFormat(i18n.language, {
      month: style,
      ...(style === "long" ? { year: "numeric" } : {}),
      timeZone: "UTC",
    }).format(new Date(`${key}-15T12:00:00Z`));
  const webShare = bookings.total > 0 ? Math.round((bookings.web / bookings.total) * 100) : 0;
  const active = day.total - day.cancelled - day.no_show;

  const kpis = [
    {
      label: t("dashboard.home.salesMonth"),
      value: money(sales.sales),
      note:
        change === null
          ? t("dashboard.home.noPrevious")
          : t("dashboard.home.vsPrevious", {
              change: `${change > 0 ? "+" : ""}${change.toLocaleString(i18n.language)} %`,
              month: monthName(previous.from.slice(0, 7), "long").split(" ")[0],
            }),
      tone: change === null ? "muted" : change >= 0 ? "good" : "bad",
    },
    {
      label: t("dashboard.home.today"),
      value: number(active),
      note: t("dashboard.home.todayNote", { completed: day.completed, cancelled: day.cancelled }),
      tone: "muted",
    },
    {
      label: t("dashboard.home.averageTicket"),
      value: money(sales.average_ticket),
      note: t("dashboard.home.completedCount", { count: sales.appointments }),
      tone: "muted",
    },
    {
      label: t("dashboard.home.webBookings"),
      value: number(bookings.web),
      note: t("dashboard.home.webShare", { percent: webShare, total: bookings.total }),
      tone: "muted",
    },
  ] as const;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1>
            {firstName
              ? t(`${greetingKey(new Date().getHours())}Name`, { name: firstName })
              : t(greetingKey(new Date().getHours()))}
          </h1>
          <p className="mt-1 text-[var(--pf-muted)] first-letter:uppercase">
            {t("dashboard.home.subtitle", {
              month: monthName(today.slice(0, 7), "long"),
              business: me?.tenant?.name ?? "",
            })}
          </p>
        </div>
        <Link
          to="/agenda?nueva=1"
          className="metal inline-flex min-h-12 items-center gap-2 rounded-2xl px-5 font-semibold focus-visible:outline-2"
        >
          <span aria-hidden="true" className="text-xl leading-none">
            +
          </span>
          {t("agenda.newAppointment")}
        </Link>
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className={`${GLASS} flex min-w-0 flex-col gap-1 p-5`}>
            <dt className="text-[var(--pf-muted)]">{kpi.label}</dt>
            <dd className="truncate text-3xl font-bold tracking-tight tabular-nums sm:text-4xl">
              {kpi.value}
            </dd>
            <dd
              className={`text-sm ${
                kpi.tone === "good"
                  ? "font-medium text-emerald-700"
                  : kpi.tone === "bad"
                    ? "font-medium text-[var(--pf-green-ink)]"
                    : "text-[var(--pf-muted)]"
              }`}
            >
              {kpi.note}
            </dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <section className={`${GLASS} flex flex-col gap-4 p-6`} aria-labelledby="sales-by-month">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="sales-by-month" className="text-lg font-semibold">
              {t("dashboard.home.salesByMonth")}{" "}
              <span className="text-sm font-normal text-[var(--pf-muted)]">
                {t("dashboard.home.salesByMonthNote")}
              </span>
            </h2>
            <Link
              to="/reportes"
              className="rounded-xl bg-white/70 px-3 py-1.5 text-sm font-medium ring-1 ring-black/10 hover:bg-white"
            >
              {t("dashboard.home.seeReports")}
            </Link>
          </div>
          <ol className="flex h-60 items-end gap-2 border-b border-black/10 sm:gap-4">
            {chart.map((row, index) => {
              const current = index === chart.length - 1;
              return (
                <li
                  key={row.month}
                  className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2"
                >
                  <span className="text-xs font-semibold tabular-nums sm:text-sm">
                    {compact(row.sales)}
                  </span>
                  <span
                    aria-hidden="true"
                    className={`w-full max-w-20 rounded-t-2xl ${current ? "metal" : "bg-black/[0.07]"}`}
                    style={{ height: `${Math.max(3, (row.sales / maxSales) * 100)}%` }}
                  />
                  <span className="sr-only">{monthName(row.month, "long")}</span>
                </li>
              );
            })}
          </ol>
          <div className="flex gap-2 sm:gap-4" aria-hidden="true">
            {chart.map((row) => (
              <span
                key={row.month}
                className="min-w-0 flex-1 text-center text-sm text-[var(--pf-muted)] first-letter:uppercase"
              >
                {monthName(row.month, "short").replace(".", "")}
              </span>
            ))}
          </div>
          <p className="text-sm text-[var(--pf-muted)]">
            {t("dashboard.home.currencyNote", { currency })}
          </p>
        </section>

        <section className={`${GLASS} flex flex-col gap-5 p-6`} aria-labelledby="by-service">
          <h2 id="by-service" className="text-lg font-semibold">
            {t("dashboard.home.byService")}
          </h2>
          {topServices.length === 0 ? (
            <p className="text-[var(--pf-muted)]">{t("dashboard.home.noSales")}</p>
          ) : (
            <ul className="flex flex-col gap-5">
              {topServices.map((row) => (
                <li key={row.key} className="flex flex-col gap-2">
                  <div className="flex justify-between gap-3">
                    <span className="min-w-0 truncate">{row.label}</span>
                    <span className="font-semibold tabular-nums">{money(row.sales)}</span>
                  </div>
                  <div className="h-2.5 rounded-full bg-black/[0.07]" aria-hidden="true">
                    <div
                      className="metal h-2.5 rounded-full"
                      style={{ width: `${(Number(row.sales) / maxService) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

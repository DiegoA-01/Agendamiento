import { type FormEvent, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../../../shared/api/client";
import { describeError } from "../../../shared/api/errors";
import { formatMoney } from "../../../shared/money";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBox,
  Loading,
  Notice,
  PageHeader,
  SelectField,
  TextField,
} from "../../../shared/ui/primitives";
import { useMe } from "../../auth/useMe";
import { useProfessionals } from "../shared/api";
import { useCan } from "../shared/useCan";
import {
  type BookingRow,
  type CommissionEntry,
  type ReportFilters,
  type SalesGroup,
  SALES_GROUPS,
  exportUrl,
  useAdjustCommission,
  useBookingsReport,
  useCommissions,
  useSalesReport,
} from "./api";
import {
  type DateRange,
  isValidRange,
  lastSevenDays,
  monthRange,
  previousMonthRange,
  todayIn,
} from "./range";

type Tab = "sales" | "bookings" | "commissions";

/** `/reportes` (spec §11 y §13): ventas, reservas y comisiones del negocio. Un profesional ve
 *  solo lo suyo: el backend filtra, aquí solo se esconde el filtro por profesional. */
export default function ReportsPage() {
  const { t } = useTranslation();
  const me = useMe().data;
  const timeZone = me?.tenant?.timezone ?? "America/Bogota";
  const today = todayIn(timeZone);
  const seesEveryone = me?.permissions.commissions?.scope === "all";
  const tabs: Tab[] = [
    ...(me?.modules.includes("reports") ? (["sales", "bookings"] as const) : []),
    ...(me?.modules.includes("commissions") ? (["commissions"] as const) : []),
  ];
  const [tab, setTab] = useState<Tab | null>(null);
  const active = tab && tabs.includes(tab) ? tab : tabs[0];
  const [range, setRange] = useState<DateRange>(() => monthRange(today));
  const [professionalId, setProfessionalId] = useState("");
  const valid = isValidRange(range);
  const filters: ReportFilters = { ...range, professional_id: professionalId || undefined };

  if (!me?.permissions.commissions?.actions.includes("view")) {
    return <Notice tone="danger">{t("errors.permission_denied")}</Notice>;
  }
  return (
    <div className="min-w-0 space-y-5">
      <PageHeader title={t("dashboard.nav.reports")} description={t("reports.intro")} />
      <div role="tablist" aria-label={t("reports.tabsLabel")} className="flex flex-wrap gap-2">
        {tabs.map((key) => (
          <button
            key={key}
            role="tab"
            type="button"
            aria-selected={active === key}
            onClick={() => setTab(key)}
            className={`rounded-full px-4 py-2 text-sm font-medium focus-visible:outline-2 ${
              active === key ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-800"
            }`}
          >
            {t(`reports.tabs.${key}`)}
          </button>
        ))}
      </div>
      <Filters
        range={range}
        onRange={setRange}
        today={today}
        professionalId={professionalId}
        onProfessional={setProfessionalId}
        showProfessional={seesEveryone}
      />
      {!valid && <Notice tone="warning">{t("reports.invalidRange")}</Notice>}
      {active === "sales" && <SalesTab filters={filters} enabled={valid} />}
      {active === "bookings" && <BookingsTab filters={filters} enabled={valid} />}
      {active === "commissions" && <CommissionsTab filters={filters} enabled={valid} />}
    </div>
  );
}

// --- Filtros ------------------------------------------------------------------------------------

function Filters({
  range,
  onRange,
  today,
  professionalId,
  onProfessional,
  showProfessional,
}: {
  range: DateRange;
  onRange: (range: DateRange) => void;
  today: string;
  professionalId: string;
  onProfessional: (id: string) => void;
  showProfessional: boolean;
}) {
  const { t } = useTranslation();
  const professionals = useProfessionals();
  const presets: [string, DateRange][] = [
    ["thisMonth", monthRange(today)],
    ["lastMonth", previousMonthRange(today)],
    ["lastSevenDays", lastSevenDays(today)],
  ];
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {presets.map(([key, preset]) => (
          <Button
            key={key}
            variant={preset.from === range.from && preset.to === range.to ? "primary" : "secondary"}
            onClick={() => onRange(preset)}
          >
            {t(`reports.presets.${key}`)}
          </Button>
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <TextField
          type="date"
          label={t("reports.from")}
          value={range.from}
          max={range.to}
          onChange={(e) => onRange({ ...range, from: e.target.value })}
        />
        <TextField
          type="date"
          label={t("reports.to")}
          value={range.to}
          min={range.from}
          onChange={(e) => onRange({ ...range, to: e.target.value })}
        />
        {showProfessional && (
          <SelectField
            label={t("reports.professional")}
            value={professionalId}
            onChange={(e) => onProfessional(e.target.value)}
          >
            <option value="">{t("reports.allProfessionals")}</option>
            {(professionals.data ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.display_name}
              </option>
            ))}
          </SelectField>
        )}
      </div>
    </Card>
  );
}

// --- Piezas comunes -----------------------------------------------------------------------------

function useFormat() {
  const { i18n } = useTranslation();
  const currency = useMe().data?.tenant?.currency ?? "COP";
  const locale = i18n.language;
  return {
    money: (value: string) => formatMoney(value, currency, locale),
    percent: (value: string) =>
      `${Number(value).toLocaleString(locale, { maximumFractionDigits: 2 })} %`,
    number: (value: number) => value.toLocaleString(locale),
    date: (iso: string, options: Intl.DateTimeFormatOptions) =>
      new Intl.DateTimeFormat(locale, { ...options, timeZone: "UTC" }).format(
        new Date(`${iso.length === 7 ? `${iso}-01` : iso}T12:00:00Z`),
      ),
  };
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="min-w-0 p-4">
      <p className="text-sm text-slate-600">{label}</p>
      <p className="mt-1 text-xl font-semibold break-words tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  );
}

function DownloadLink({ href }: { href: string }) {
  const { t } = useTranslation();
  return (
    <a
      href={href}
      download
      className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50 focus-visible:outline-2"
    >
      {t("reports.downloadCsv")}
    </a>
  );
}

function Table({
  caption,
  head,
  children,
  hideCaption,
}: {
  caption: string;
  head: string[];
  children: ReactNode;
  /** Si la primera columna ya dice lo mismo, el título queda solo para lectores de pantalla. */
  hideCaption?: boolean;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full min-w-[36rem] text-left text-sm">
        <caption className={hideCaption ? "sr-only" : "px-4 pt-3 text-left font-semibold"}>
          {caption}
        </caption>
        <thead className="text-slate-600">
          <tr>
            {head.map((label, index) => (
              <th
                key={label}
                scope="col"
                className={`px-4 py-2 font-medium whitespace-nowrap ${index ? "text-right" : ""}`}
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 tabular-nums">{children}</tbody>
      </table>
    </div>
  );
}

function Cell({ children, first }: { children: ReactNode; first?: boolean }) {
  return first ? (
    <th scope="row" className="min-w-36 px-4 py-2 font-medium">
      {children}
    </th>
  ) : (
    <td className="px-4 py-2 text-right whitespace-nowrap">{children}</td>
  );
}

function QueryState({
  query,
}: {
  query: { isPending: boolean; isError: boolean; error: unknown; refetch: () => unknown };
}) {
  const { t } = useTranslation();
  if (query.isPending) return <Loading />;
  if (query.isError)
    return (
      <ErrorBox message={describeError(t, query.error)} onRetry={() => void query.refetch()} />
    );
  return null;
}

// --- Ventas -------------------------------------------------------------------------------------

function SalesTab({ filters, enabled }: { filters: ReportFilters; enabled: boolean }) {
  const { t } = useTranslation();
  const format = useFormat();
  const [groupBy, setGroupBy] = useState<SalesGroup>("day");
  const report = useSalesReport(filters, groupBy, enabled);
  const label = (key: string, text: string) => {
    if (groupBy === "day")
      return format.date(key, { weekday: "short", day: "numeric", month: "short" });
    if (groupBy === "week")
      return t("reports.weekOf", { date: format.date(key, { day: "numeric", month: "short" }) });
    if (groupBy === "month") return format.date(key, { month: "long", year: "numeric" });
    return text;
  };
  return (
    <section className="space-y-4" aria-label={t("reports.tabs.sales")}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <SelectField
          label={t("reports.groupBy")}
          value={groupBy}
          onChange={(e) => setGroupBy(e.target.value as SalesGroup)}
        >
          {SALES_GROUPS.map((group) => (
            <option key={group} value={group}>
              {t(`reports.groups.${group}`)}
            </option>
          ))}
        </SelectField>
        {enabled && (
          <DownloadLink href={exportUrl("reports/sales/", filters, { group_by: groupBy })} />
        )}
      </div>
      {enabled && <QueryState query={report} />}
      {report.isSuccess && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-5">
            <Stat label={t("reports.sales")} value={format.money(report.data.totals.sales)} />
            <Stat
              label={t("reports.commissions")}
              value={format.money(report.data.totals.commissions)}
            />
            <Stat label={t("reports.business")} value={format.money(report.data.totals.business)} />
            <Stat
              label={t("reports.appointments")}
              value={format.number(report.data.totals.appointments)}
            />
            <Stat
              label={t("reports.averageTicket")}
              value={format.money(report.data.totals.average_ticket)}
            />
          </div>
          {report.data.rows.length === 0 ? (
            <EmptyState>{t("reports.noSales")}</EmptyState>
          ) : (
            <Table
              hideCaption
              caption={t("reports.salesBy", { group: t(`reports.groups.${groupBy}`) })}
              head={[
                t(`reports.groups.${groupBy}`),
                t("reports.sales"),
                t("reports.commissions"),
                t("reports.business"),
                t("reports.appointments"),
                t("reports.averageTicket"),
              ]}
            >
              {report.data.rows.map((row) => (
                <tr key={row.key}>
                  <Cell first>{label(row.key, row.label)}</Cell>
                  <Cell>{format.money(row.sales)}</Cell>
                  <Cell>{format.money(row.commissions)}</Cell>
                  <Cell>{format.money(row.business)}</Cell>
                  <Cell>{format.number(row.appointments)}</Cell>
                  <Cell>{format.money(row.average_ticket)}</Cell>
                </tr>
              ))}
            </Table>
          )}
          <p className="text-xs text-slate-500">{t("reports.salesNote")}</p>
        </>
      )}
    </section>
  );
}

// --- Reservas -----------------------------------------------------------------------------------

function BookingsTab({ filters, enabled }: { filters: ReportFilters; enabled: boolean }) {
  const { t } = useTranslation();
  const format = useFormat();
  const report = useBookingsReport(filters, enabled);
  const head = (first: string) => [
    first,
    t("reports.total"),
    t("reports.completed"),
    t("reports.cancelled"),
    t("reports.noShow"),
    t("reports.cancellationRate"),
    t("reports.noShowRate"),
  ];
  const rows = (items: BookingRow[], name: (row: BookingRow) => string) =>
    items.map((row) => (
      <tr key={row.key}>
        <Cell first>{name(row)}</Cell>
        <Cell>{format.number(row.total)}</Cell>
        <Cell>{format.number(row.completed)}</Cell>
        <Cell>{format.number(row.cancelled)}</Cell>
        <Cell>{format.number(row.no_show)}</Cell>
        <Cell>{format.percent(row.cancellation_rate)}</Cell>
        <Cell>{format.percent(row.no_show_rate)}</Cell>
      </tr>
    ));
  return (
    <section className="space-y-4" aria-label={t("reports.tabs.bookings")}>
      <div className="flex justify-end">
        {enabled && <DownloadLink href={exportUrl("reports/bookings/", filters)} />}
      </div>
      {enabled && <QueryState query={report} />}
      {report.isSuccess && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat
              label={t("reports.bookings")}
              value={format.number(report.data.totals.total)}
              hint={t("reports.webHint", { count: report.data.totals.web })}
            />
            <Stat
              label={t("reports.completed")}
              value={format.number(report.data.totals.completed)}
            />
            <Stat
              label={t("reports.cancellationRate")}
              value={format.percent(report.data.totals.cancellation_rate)}
            />
            <Stat
              label={t("reports.noShowRate")}
              value={format.percent(report.data.totals.no_show_rate)}
            />
          </div>
          {report.data.totals.total === 0 ? (
            <EmptyState>{t("reports.noBookings")}</EmptyState>
          ) : (
            <div className="space-y-4">
              <Table caption={t("reports.byMonth")} head={head(t("reports.groups.month"))}>
                {rows(report.data.by_month, (row) =>
                  format.date(row.key, { month: "long", year: "numeric" }),
                )}
              </Table>
              <Table caption={t("reports.byService")} head={head(t("reports.groups.service"))}>
                {rows(report.data.by_service, (row) => row.label)}
              </Table>
              <Table
                caption={t("reports.byProfessional")}
                head={head(t("reports.groups.professional"))}
              >
                {rows(report.data.by_professional, (row) => row.label)}
              </Table>
            </div>
          )}
          <p className="text-xs text-slate-500">{t("reports.bookingsNote")}</p>
        </>
      )}
    </section>
  );
}

// --- Comisiones ---------------------------------------------------------------------------------

function CommissionsTab({ filters, enabled }: { filters: ReportFilters; enabled: boolean }) {
  const { t, i18n } = useTranslation();
  const format = useFormat();
  const timeZone = useMe().data?.tenant?.timezone ?? "America/Bogota";
  const canAdjust = useCan("commissions", "adjust");
  const entries = useCommissions(filters, enabled);
  const [adjusting, setAdjusting] = useState<CommissionEntry | null>(null);
  const list = entries.data?.pages.flatMap((page) => page.results) ?? [];
  const when = (iso: string) =>
    new Intl.DateTimeFormat(i18n.language, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone,
    }).format(new Date(iso));
  return (
    <section className="space-y-4" aria-label={t("reports.tabs.commissions")}>
      <div className="flex justify-end">
        {enabled && <DownloadLink href={exportUrl("commissions/", filters)} />}
      </div>
      {adjusting && <AdjustForm entry={adjusting} onDone={() => setAdjusting(null)} />}
      {enabled && <QueryState query={entries} />}
      {entries.isSuccess && list.length === 0 && (
        <EmptyState>{t("reports.noCommissions")}</EmptyState>
      )}
      {list.length > 0 && (
        <Table
          hideCaption
          caption={t("reports.tabs.commissions")}
          head={[
            t("reports.appointmentDate"),
            t("reports.groups.professional"),
            t("reports.groups.service"),
            t("reports.base"),
            t("reports.pct"),
            t("reports.commission"),
            t("reports.business"),
            ...(canAdjust ? [t("reports.actions")] : []),
          ]}
        >
          {list.map((entry) => (
            <tr key={entry.id} className={entry.kind === "adjustment" ? "bg-amber-50/60" : ""}>
              <Cell first>
                <span className="block">{when(entry.appointment_start_at)}</span>
                {entry.kind === "adjustment" && (
                  <span className="mt-1 flex flex-wrap items-center gap-1 text-xs font-normal">
                    <Badge tone="warning">{t("reports.adjustment")}</Badge>
                    {entry.reason}
                  </span>
                )}
              </Cell>
              <Cell>{entry.professional_name}</Cell>
              <Cell>{entry.service_name}</Cell>
              <Cell>{format.money(entry.base_amount)}</Cell>
              <Cell>{format.percent(entry.pct)}</Cell>
              <Cell>{format.money(entry.commission_amount)}</Cell>
              <Cell>{format.money(entry.business_amount)}</Cell>
              {canAdjust && (
                <Cell>
                  {entry.kind === "entry" && (
                    <Button variant="ghost" onClick={() => setAdjusting(entry)}>
                      {t("reports.adjust")}
                    </Button>
                  )}
                </Cell>
              )}
            </tr>
          ))}
        </Table>
      )}
      {entries.hasNextPage && (
        <Button
          variant="secondary"
          disabled={entries.isFetchingNextPage}
          onClick={() => void entries.fetchNextPage()}
        >
          {t("reports.loadMore")}
        </Button>
      )}
    </section>
  );
}

function AdjustForm({ entry, onDone }: { entry: CommissionEntry; onDone: () => void }) {
  const { t } = useTranslation();
  const format = useFormat();
  const adjust = useAdjustCommission();
  const [base, setBase] = useState(entry.base_amount);
  const [commission, setCommission] = useState(entry.commission_amount);
  const [reason, setReason] = useState("");
  const fields = adjust.error instanceof ApiError ? adjust.error.fields : {};
  const submit = (event: FormEvent) => {
    event.preventDefault();
    adjust.mutate(
      { id: entry.id, base_amount: base, commission_amount: commission, reason },
      { onSuccess: onDone },
    );
  };
  return (
    <Card>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">{t("reports.adjustTitle")}</h2>
          <p className="text-sm text-slate-600">
            {t("reports.adjustIntro", {
              professional: entry.professional_name,
              service: entry.service_name,
              commission: format.money(entry.commission_amount),
            })}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField
            label={t("reports.correctBase")}
            inputMode="decimal"
            value={base}
            error={fields.base_amount?.[0]}
            onChange={(e) => setBase(e.target.value)}
            required
          />
          <TextField
            label={t("reports.correctCommission")}
            inputMode="decimal"
            value={commission}
            error={fields.commission_amount?.[0]}
            onChange={(e) => setCommission(e.target.value)}
            required
          />
        </div>
        <TextField
          label={t("reports.reason")}
          value={reason}
          maxLength={250}
          error={fields.reason?.[0]}
          onChange={(e) => setReason(e.target.value)}
          required
        />
        <p className="text-xs text-slate-500">{t("reports.adjustNote")}</p>
        {adjust.isError && <Notice tone="danger">{describeError(t, adjust.error)}</Notice>}
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={adjust.isPending}>
            {t("reports.saveAdjustment")}
          </Button>
          <Button variant="ghost" onClick={onDone}>
            {t("common.cancel")}
          </Button>
        </div>
      </form>
    </Card>
  );
}

import { useTranslation } from "react-i18next";
import { Button, EmptyState, ErrorBox, Loading } from "../../../shared/ui/primitives";
import { describeError } from "../../../shared/api/errors";
import { formatTime } from "../../booking/wizard";
import { useMe } from "../../auth/useMe";
import { useSlots } from "./api";

export function SlotPicker({
  serviceIds,
  professionalId,
  date,
  value,
  onChange,
}: {
  serviceIds: string[];
  professionalId: string;
  date: string;
  value: string;
  onChange: (start: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const zone = useMe().data?.tenant?.timezone ?? "America/Bogota";
  const slots = useSlots(serviceIds, professionalId, date);
  return (
    <fieldset className="min-w-0 space-y-2">
      <legend className="text-sm font-medium">{t("agenda.time")}</legend>
      {!serviceIds.length || !date ? (
        <p>{t("agenda.chooseServicesDate")}</p>
      ) : (
        <>
          {slots.isPending && <Loading />}
          {slots.isError && (
            <ErrorBox
              message={describeError(t, slots.error)}
              onRetry={() => void slots.refetch()}
            />
          )}
          {slots.isSuccess && !slots.data.length && <EmptyState>{t("agenda.noSlots")}</EmptyState>}
          <div className="flex flex-wrap gap-2">
            {slots.data?.map((slot) => (
              <Button
                key={slot.start}
                variant={value === slot.start ? "primary" : "secondary"}
                aria-pressed={value === slot.start}
                onClick={() => onChange(slot.start)}
              >
                {formatTime(slot.start, i18n.language, zone)}
              </Button>
            ))}
          </div>
        </>
      )}
    </fieldset>
  );
}

import { useMutation } from "@tanstack/react-query";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { uploadFile } from "../../../shared/api/client";
import { describeError } from "../../../shared/api/errors";
import type { ImageRef, MediaFile } from "../../../shared/api/types";
import { Button, Notice } from "../../../shared/ui/primitives";

const ACCEPT = "image/jpeg,image/png,image/webp";

/** Sube una imagen a `media/` (el servidor la convierte a WebP) y entrega su referencia. El
 *  formulario que lo usa guarda solo el id. */
export function ImageField({
  label,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  value: ImageRef | null;
  onChange: (image: ImageRef | null) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const id = useId();
  const upload = useMutation({
    mutationFn: (file: File) => uploadFile<MediaFile>("/api/v1/media/", file),
    onSuccess: (media) => onChange({ id: media.id, urls: media.urls }),
  });

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium text-slate-800">{label}</span>
      <div className="flex flex-wrap items-center gap-3">
        {value ? (
          <img
            src={value.urls.thumb}
            alt=""
            className="size-20 rounded-lg border border-slate-200 object-cover"
          />
        ) : (
          <div className="flex size-20 items-center justify-center rounded-lg border border-dashed border-slate-300 text-xs text-slate-500">
            {t("catalog.image.none")}
          </div>
        )}
        {!disabled && (
          <div className="flex flex-wrap gap-2">
            <label
              htmlFor={id}
              className="inline-flex min-h-10 cursor-pointer items-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-900 hover:bg-slate-50 focus-within:outline-2"
            >
              {upload.isPending ? t("catalog.image.uploading") : t("catalog.image.choose")}
              <input
                id={id}
                type="file"
                accept={ACCEPT}
                className="sr-only"
                disabled={upload.isPending}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) upload.mutate(file);
                  event.target.value = "";
                }}
              />
            </label>
            {value && (
              <Button variant="ghost" onClick={() => onChange(null)}>
                {t("catalog.image.remove")}
              </Button>
            )}
          </div>
        )}
      </div>
      <p className="text-xs text-slate-600">{t("catalog.image.hint")}</p>
      {upload.isError && <Notice tone="danger">{describeError(t, upload.error)}</Notice>}
    </div>
  );
}

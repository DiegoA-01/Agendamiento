/** Texto del archivo .txt con los códigos de recuperación del 2FA (pormejorar §2). */
export function recoveryCodesText(
  codes: string[],
  { title, note, email, issuedAt }: { title: string; note: string; email: string; issuedAt: Date },
): string {
  const date = issuedAt.toISOString().slice(0, 10);
  return [
    title,
    email,
    date,
    "",
    ...codes.map((code, i) => `${i + 1}. ${code}`),
    "",
    note,
    "",
  ].join("\n");
}

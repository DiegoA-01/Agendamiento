/** Contraste WCAG para la vista previa del tema. El servidor es quien manda: aquí solo se avisa
 *  antes de guardar. Debe dar los mismos valores que `apps/tenancy/theme.py`. */

export const MIN_TEXT_CONTRAST = 4.5;

const HEX = /^#[0-9a-fA-F]{6}$/;

export const isHexColor = (value: string): boolean => HEX.test(value);

function luminance(color: string): number {
  const [red, green, blue] = [1, 3, 5].map((index) => {
    const value = parseInt(color.slice(index, index + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

export function contrastRatio(first: string, second: string): number {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

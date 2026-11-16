import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

/** Zona que se desplaza sin barra de desplazamiento visible (barras laterales de los paneles).
 *  Cuando hay más contenido arriba o abajo, el borde se desvanece y abajo aparece una flecha de
 *  vidrio que baja el menú al tocarla. Con el teclado no hace falta: el foco desplaza solo. */
export function ScrollArea({
  className,
  tone,
  children,
}: {
  className: string;
  tone: "dark" | "light";
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ top: false, bottom: false });

  function measure() {
    const el = ref.current;
    if (!el) return;
    const top = el.scrollTop > 2;
    const bottom = el.scrollTop + el.clientHeight < el.scrollHeight - 2;
    setEdges((prev) => (prev.top === top && prev.bottom === bottom ? prev : { top, bottom }));
  }

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    // El primer aviso llega al empezar a observar, así que también hace la medida inicial.
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    for (const child of Array.from(el.children)) observer.observe(child);
    return () => observer.disconnect();
  }, []);

  function scrollDown() {
    const el = ref.current;
    el?.scrollBy({ top: el.clientHeight * 0.6, behavior: "smooth" });
  }

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={ref}
        onScroll={measure}
        data-fade-top={edges.top || undefined}
        data-fade-bottom={edges.bottom || undefined}
        className={`scroll-fade h-full overflow-y-auto overscroll-contain ${className}`}
      >
        {children}
      </div>
      <button
        type="button"
        tabIndex={-1}
        aria-hidden="true"
        title={t("nav.more")}
        onClick={scrollDown}
        className={`scroll-more ${tone === "dark" ? "scroll-more-dark" : "scroll-more-light"} ${
          edges.bottom ? "" : "pointer-events-none opacity-0"
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          className="size-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m6 9.5 6 6 6-6" />
        </svg>
      </button>
    </div>
  );
}

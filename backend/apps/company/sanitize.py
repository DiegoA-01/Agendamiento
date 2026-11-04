"""Limpieza del HTML de los textos legales (términos, privacidad, cookies).

El propietario los escribe en el panel y se muestran en las páginas públicas del negocio: sin
limpiar, un `<script>` o un `onclick` correría en el navegador de cada cliente que reserva. Se
deja pasar solo formato básico (lista blanca) y se escapa todo lo demás. Usa la librería estándar:
no hace falta una dependencia nueva para este conjunto pequeño de etiquetas.
"""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li", "h2", "h3", "h4", "blockquote", "a",
}  # fmt: skip
VOID_TAGS = {"br"}
# Su contenido tampoco se muestra: no es texto para el lector.
DROP_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "template", "noscript"}
SAFE_URL_SCHEMES = {"http", "https", "mailto", "tel"}
MAX_LENGTH = 100_000


def _safe_href(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    scheme = urlsplit(value).scheme.lower()
    return value if scheme in SAFE_URL_SCHEMES else None


class _Cleaner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[str] = []
        self.dropping = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT_TAGS:
            self.dropping += 1
            return
        if self.dropping or tag not in ALLOWED_TAGS:
            return
        if tag == "a":
            href = _safe_href(dict(attrs).get("href"))
            if href is None:
                self.out.append("<a>")
            else:
                self.out.append(f'<a href="{escape(href)}" rel="noopener noreferrer nofollow">')
        else:
            self.out.append(f"<{tag}>")
        if tag not in VOID_TAGS:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS and self.open and self.open[-1] == tag:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT_TAGS:
            self.dropping = max(0, self.dropping - 1)
            return
        if self.dropping or tag not in self.open:
            return
        # Cierra también lo que quedó abierto dentro: el resultado siempre está bien anidado.
        while self.open:
            current = self.open.pop()
            self.out.append(f"</{current}>")
            if current == tag:
                break

    def handle_data(self, data):
        if not self.dropping:
            self.out.append(escape(data, quote=False))

    def result(self) -> str:
        self.close()
        while self.open:
            self.out.append(f"</{self.open.pop()}>")
        return "".join(self.out).strip()


def clean_html(value: str) -> str:
    cleaner = _Cleaner()
    cleaner.feed(value[:MAX_LENGTH])
    return cleaner.result()

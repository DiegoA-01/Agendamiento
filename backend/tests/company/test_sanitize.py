import pytest

from apps.company.sanitize import clean_html


@pytest.mark.parametrize(
    "dirty, clean",
    [
        ("<p>Hola <strong>mundo</strong></p>", None),
        ("<p onclick='robar()'>Texto</p>", "<p>Texto</p>"),
        ("<script>alert(1)</script><p>Ok</p>", "<p>Ok</p>"),
        ("<style>p{}</style>Texto", "Texto"),
        ("<img src=x onerror=alert(1)>Foto", "Foto"),
        ("<iframe src='https://malo'></iframe>Fin", "Fin"),
        ('<a href="javascript:alert(1)">clic</a>', "<a>clic</a>"),
        (
            '<a href="https://ejemplo.com" target="_blank">sitio</a>',
            '<a href="https://ejemplo.com" rel="noopener noreferrer nofollow">sitio</a>',
        ),
        (
            '<a href="mailto:hola@ejemplo.com">correo</a>',
            '<a href="mailto:hola@ejemplo.com" rel="noopener noreferrer nofollow">correo</a>',
        ),
        ("1 < 2 & 3 > 2", "1 &lt; 2 &amp; 3 &gt; 2"),
        ("<p>sin cerrar <em>énfasis", "<p>sin cerrar <em>énfasis</em></p>"),
        ("Línea<br>otra<br/>fin", "Línea<br>otra<br>fin"),
        ("<!-- comentario --><h2>Título</h2>", "<h2>Título</h2>"),
        ("<div><span>texto</span></div>", "texto"),
    ],
)
def test_only_basic_formatting_survives(dirty, clean):
    expected = dirty if clean is None else clean
    assert clean_html(dirty) == expected


def test_escaped_entities_are_not_turned_into_tags():
    assert clean_html("&lt;script&gt;alert(1)&lt;/script&gt;") == (
        "&lt;script&gt;alert(1)&lt;/script&gt;"
    )

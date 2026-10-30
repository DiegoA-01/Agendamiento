# Reglas para el agente

- Idioma de UI: español (default) e inglés; todo texto visible pasa por i18n desde el primer commit. Código, nombres de modelos y endpoints en inglés.
- Nunca escribir una consulta de negocio sin filtrar por tenant. Todo modelo de negocio hereda de `TenantOwnedModel`.
- Fechas en UTC en base de datos; conversión a la zona horaria del tenant solo en serialización y UI.
- Dinero como `DecimalField(max_digits=12, decimal_places=2)`; moneda por tenant (default COP). Nunca float.
- Cada módulo es una app Django independiente; una app no importa modelos de otra salvo por su `services.py` público.
- Toda lógica de negocio en `services.py`, no en vistas ni serializers.
- Cada tarea termina con tests pasando (`pytest`) y migraciones incluidas.
- No agregar dependencias fuera de la lista de la sección 2 sin pedirlo.
- No implementar nada de la sección 12 (fuera de alcance).

Antes de cualquier tarea, lee `docs/SPEC-FASE-1-MVP.md`.

Somos dos personas trabajando en paralelo, cada una con su Claude. Antes de cualquier tarea, lee también `docs/REPARTO.md`. Pregunta en qué frente (A o B) se trabaja si no te lo dijeron. No toques apps ni migraciones del otro frente sin pedirlo.

# Agenda — SaaS de agendamiento para barberías y salones

Fase 1 (MVP). Especificación en [`docs/SPEC-FASE-1-MVP.md`](docs/SPEC-FASE-1-MVP.md); reglas para el agente en [`CLAUDE.md`](CLAUDE.md).

## Arranque

```bash
cp .env.example .env
docker compose up --build
```

- App (vía Caddy): http://localhost:8080
- Healthcheck: http://localhost:8080/healthz/
- Esquema OpenAPI: http://localhost:8080/api/schema/

Si vienes de una versión anterior (antes de M1), recrea el volumen de la base para crear el rol de la aplicación: `docker compose down -v`.

## Multi-tenancy

Cada negocio (tenant) se resuelve por su host (`<slug>.<BASE_DOMAIN>`). En local `BASE_DOMAIN=localhost`, así que `http://elfilo.localhost:8080` y `http://admin.localhost:8080` funcionan sin tocar el archivo `hosts` en la mayoría de navegadores. La app se conecta a PostgreSQL con un rol sin superusuario para que RLS se aplique.

## Tests y calidad

```bash
docker compose run --rm api pytest
docker compose run --rm api ruff check .
docker compose run --rm api ruff format --check .
docker compose run --rm api mypy .
```

Frontend (en `frontend/`): `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, `npm run build`.

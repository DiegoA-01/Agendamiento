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

## Tests y calidad

```bash
docker compose run --rm api pytest
docker compose run --rm api ruff check .
docker compose run --rm api ruff format --check .
docker compose run --rm api mypy .
```

Frontend (en `frontend/`): `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, `npm run build`.

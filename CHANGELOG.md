# Changelog

## M0 — Base del repo

- Estructura `backend/` (Django 5 + DRF + drf-spectacular + Celery) y `frontend/` (React + Vite + TS + Tailwind).
- Settings `base`, `dev`, `prod`; logs JSON estructurados; i18n es/en en backend (`LocaleMiddleware`).
- Healthcheck `GET /healthz/` (verifica PostgreSQL y Redis) y esquema OpenAPI en `/api/schema/`.
- Frontend con i18next (es/en), TanStack Query, react-router, Tailwind y página inicial que consulta el healthcheck.
- Docker Compose: `api`, `worker`, `beat`, `web`, `postgres` (con `btree_gist`), `redis`, `caddy`.
- CI en GitHub Actions: ruff, mypy, pytest (backend); eslint, prettier, vitest, build (frontend).
- Sin migraciones propias: aún no hay modelos de negocio (empiezan en M1).

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

## Primer Super Admin

Pide la contraseña por consola (mínimo 10 caracteres). Con el 2FA exigido, en su primer login deberá activarlo con una app como Google Authenticator.

> **El 2FA está APAGADO en desarrollo para facilitar las pruebas** (`REQUIRE_TWO_FACTOR=0` en `.env`): el Super Admin entra solo con la contraseña. Producción **no arranca** con él apagado. **Hay que reactivarlo antes de entregar**: pon `REQUIRE_TWO_FACTOR=1` (o borra la línea) en `.env` y reinicia con `docker compose up -d api`. Ver `pormejorar.md` §33.

```bash
docker compose exec api python manage.py create_superadmin --email tu@correo.com
```

Los correos de recuperación de contraseña salen por consola en desarrollo (`docker compose logs api`).

Si el Super Admin pierde su celular, desde el servidor se le quita el 2FA para que lo active de nuevo:

```bash
docker compose exec api python manage.py reset_2fa --email tu@correo.com
```

## Panel del Super Admin

Entra a http://admin.localhost:8080 (en local, los navegadores resuelven `*.localhost` solos). Desde ahí:

1. **Planes:** crea al menos uno (módulos y límites).
2. **Empresas → Nueva empresa:** crea el negocio. Se genera su subdominio (`<slug>.localhost:8080`) y una contraseña temporal para el propietario, que se muestra una sola vez.
3. El propietario entra en su subdominio, cambia la contraseña y ve su panel.

Cada empresa tiene secciones de datos, tema (con control de contraste), módulos y dominios propios (se verifican con un registro DNS `TXT`). La sección **Auditoría** registra lo que hace el Super Admin.

## Tests y calidad

```bash
docker compose run --rm api pytest
docker compose run --rm api ruff check .
docker compose run --rm api ruff format --check .
docker compose run --rm api mypy .
```

Frontend (en `frontend/`): `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, `npm run build`.

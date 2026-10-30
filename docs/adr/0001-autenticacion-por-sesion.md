# ADR 0001 — Autenticación por sesión con cookie HttpOnly + CSRF

Estado: aceptada (M2). Fecha: 2026-10-30.

## Contexto

La spec (§9) pide elegir entre sesión con cookie HttpOnly + CSRF o JWT corto + refresh en cookie, y documentar la elección. El dashboard y el panel del Super Admin son aplicaciones web propias, servidas bajo el mismo dominio que la API (Caddy enruta ambos).

## Decisión

Sesión de Django (cookie `sessionid`, HttpOnly, SameSite=Lax, Secure en producción) + token CSRF.

- El frontend llama `GET /api/v1/auth/csrf/` una vez, lee la cookie `csrftoken` y envía su valor en el header `X-CSRFToken` en cada POST/PATCH/PUT/DELETE. También el login, para evitar "login CSRF".
- Las cookies son por host: la sesión de `elfilo.<dominio>` no viaja a `aura.<dominio>` ni a `admin.<dominio>`. Además `TenantSessionGuardMiddleware` descarta una sesión usada en un host que no es de su usuario.
- Cambiar la contraseña invalida todas las sesiones del usuario (el hash de sesión depende de la contraseña). Borrar (lógico) o desactivar a un usuario también.
- Sin sesión la API responde 401; con sesión sin permiso, 403.

## Por qué no JWT

- Sin dependencias nuevas (la spec limita la lista de paquetes).
- Revocar una sesión es inmediato; un JWT vive hasta que vence.
- El token nunca es legible desde JavaScript, así que un XSS no puede robarlo.

## Consecuencias

- Las apps móviles o integraciones de terceros (fuera de alcance en la Fase 1) necesitarían otro mecanismo, por ejemplo tokens de API.
- Sesiones en PostgreSQL (`django_session`). Si la carga lo exige, se pasan a Redis (`cached_db`).
- Pendiente de M10: límite de intentos de login y de recuperación de contraseña.

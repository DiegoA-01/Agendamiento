-- Rol de la aplicación: NO superusuario y SIN BYPASSRLS, para que RLS se aplique de verdad
-- (PostgreSQL ignora RLS para superusuarios). Es dueño de la base y de sus tablas; las políticas
-- usan FORCE ROW LEVEL SECURITY para que también apliquen al dueño.
-- Variables psql: app_user, app_password.

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L CREATEDB', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'app_user')
\gexec

SELECT format('ALTER DATABASE %I OWNER TO %I', current_database(), :'app_user')
\gexec

-- Necesaria para la restricción de exclusión anti doble reserva (M5).
CREATE EXTENSION IF NOT EXISTS btree_gist;

"""Argon2id para contraseñas nuevas; los hashes viejos siguen sirviendo y se actualizan solos.

Los tests usan un hasher MD5 rápido (ver settings de test); aquí se restaura la configuración real.
"""

import pytest
from django.contrib.auth.hashers import Argon2PasswordHasher, make_password
from rest_framework.test import APIClient

from config.settings import base
from tests.accounts.factories import PASSWORD, UserFactory
from tests.tenancy.factories import TenantFactory

from .helpers import host, login

pytestmark = pytest.mark.django_db


@pytest.fixture
def real_hashers(settings):
    settings.PASSWORD_HASHERS = base.PASSWORD_HASHERS


@pytest.fixture
def camila(real_hashers):
    return UserFactory(tenant=TenantFactory(slug="elfilo"), email="camila@x.com")


def test_production_config_prefers_argon2id_and_keeps_pbkdf2_for_old_hashes():
    assert base.PASSWORD_HASHERS == [
        "config.hashers.Argon2idHasher",
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    ]


def test_new_passwords_use_argon2id_with_the_owasp_minimum_profile(camila):
    assert camila.password.startswith("argon2$argon2id$v=19$m=19456,t=2,p=1$")
    assert camila.check_password(PASSWORD)
    assert not camila.check_password("otra-clave")


def test_each_hash_has_its_own_salt(real_hashers):
    assert make_password(PASSWORD) != make_password(PASSWORD)


def test_old_pbkdf2_hash_still_logs_in_and_is_upgraded(camila):
    camila.password = make_password(PASSWORD, hasher="pbkdf2_sha256")
    camila.save()
    assert camila.password.startswith("pbkdf2_sha256$")

    assert login(APIClient(), camila, host("elfilo")).status_code == 200

    camila.refresh_from_db()
    assert camila.password.startswith("argon2$argon2id$")
    assert login(APIClient(), camila, host("elfilo")).status_code == 200


def test_argon2_hash_with_older_parameters_is_upgraded(camila):
    """Django por defecto usa ~100 MB (m=102400): al entrar pasa al perfil de 19 MiB."""
    camila.password = Argon2PasswordHasher().encode(PASSWORD, "saltsaltsalt")
    camila.save()
    assert "m=102400" in camila.password

    assert login(APIClient(), camila, host("elfilo")).status_code == 200

    camila.refresh_from_db()
    assert "m=19456,t=2,p=1" in camila.password


def test_wrong_password_does_not_upgrade_the_hash(camila):
    old = make_password(PASSWORD, hasher="pbkdf2_sha256")
    camila.password = old
    camila.save()
    assert login(APIClient(), camila, host("elfilo"), password="mala-clave-123").status_code == 401
    camila.refresh_from_db()
    assert camila.password == old

import pytest

from apps.accounts import totp

# RFC 6238, apéndice B: secreto ASCII "12345678901234567890" en base32, SHA-1. El RFC da 8 dígitos;
# con 6 dígitos son los últimos 6.
RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
RFC_VECTORS = [
    (59, "287082"),
    (1111111109, "081804"),
    (1111111111, "050471"),
    (1234567890, "005924"),
    (2000000000, "279037"),
]


@pytest.mark.parametrize(("moment", "expected"), RFC_VECTORS)
def test_matches_rfc_6238_vectors(moment, expected):
    assert totp.code_at(RFC_SECRET, moment) == expected


def test_verify_accepts_current_and_adjacent_steps_only():
    now = 1_000_000_000
    for offset in (-30, 0, 30):
        assert totp.verify(RFC_SECRET, totp.code_at(RFC_SECRET, now + offset), now=now) is not None
    assert totp.verify(RFC_SECRET, totp.code_at(RFC_SECRET, now + 90), now=now) is None
    assert totp.verify(RFC_SECRET, totp.code_at(RFC_SECRET, now - 90), now=now) is None


def test_verify_rejects_replay_of_a_used_step():
    now = 1_000_000_000
    code = totp.code_at(RFC_SECRET, now)
    step = totp.verify(RFC_SECRET, code, now=now)
    assert step == now // 30
    assert totp.verify(RFC_SECRET, code, now=now, last_step=step) is None
    # Un código de un paso posterior sí sirve.
    assert totp.verify(RFC_SECRET, totp.code_at(RFC_SECRET, now + 30), now=now, last_step=step)


@pytest.mark.parametrize("bad", ["", "12345", "1234567", "abcdef", "12 34", "２８７０８２"])
def test_verify_rejects_malformed_codes(bad):
    assert totp.verify(RFC_SECRET, bad, now=59) is None


def test_verify_ignores_spaces_in_the_code():
    assert totp.verify(RFC_SECRET, "287 082", now=59) is not None


def test_generate_secret_is_random_valid_base32():
    first, second = totp.generate_secret(), totp.generate_secret()
    assert first != second
    assert len(first) == 32
    assert totp.code_at(first, 59).isdigit()


def test_provisioning_uri_has_what_authenticator_apps_need():
    uri = totp.provisioning_uri("ABC234", "ana@x.com", "Agenda")
    assert uri.startswith("otpauth://totp/Agenda:ana%40x.com?")
    assert "secret=ABC234" in uri and "issuer=Agenda" in uri

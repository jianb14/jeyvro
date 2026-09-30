"""Test-session fixtures.

One thing lives here, and it changes what the suite *costs*, never what it
proves: the password hasher.

The gate drives the real auth API — `POST /api/v1/auth/register`, `/login`,
password reset — so every test that needs a signed-in user pays Django's
default PBKDF2 hasher (1.2M iterations, ~0.7s of pure CPU on this machine, on
top of the matching verify at login). No test asserts anything about the KDF:
a password still goes through `set_password` and is still only accepted by
`check_password`, which is the contract worth testing. Swapping the algorithm
for the duration of the run is the trade Django's own test documentation
recommends, and it takes the full suite from ~20 minutes to a couple of them.

Production never sees this file, and nothing here weakens an app-level rule —
this is a hashing *cost* knob, not a validation one.

The second knob is throttling (§20.1). Rate limits are a runtime control with a
wall clock, and the suite drives the real auth API hundreds of times — leaving
them on would make gate results depend on how fast the machine is and on
whether a previous test happened to spend a bucket. So the whole suite runs
unthrottled, and `tests/test_security_hardening.py` turns throttling back on
with its own rates to prove the control actually refuses. Same trade, same
reason: this changes what the suite *costs*, never what it *proves*.
"""
import pytest


@pytest.fixture(autouse=True)
def _fast_password_hashing(settings):
    """MD5 in tests only — fast to write, fast to verify, same contract."""
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@pytest.fixture(autouse=True)
def _no_throttling_in_tests(monkeypatch):
    """Rate limiting off for the suite; proven on purpose in its own test file.

    DRF binds `DEFAULT_THROTTLE_CLASSES` onto `APIView.throttle_classes` at
    import time, so this patches the attribute the views actually read rather
    than the settings dict — deterministic, and restored after every test.
    """
    from rest_framework.views import APIView

    monkeypatch.setattr(APIView, 'throttle_classes', [])

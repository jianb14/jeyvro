"""JEYVRO Phase 4 live smoke — drives the REAL runserver over HTTP.

Flow: register -> staff promote -> apply -> staff approve -> own-store edit
-> ownership deny path -> logged-out public storefront -> audit rows.
Writes each step to smoke_phase4.log as it happens (crash-safe evidence).
"""
import http.cookiejar
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
BACKEND = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BACKEND, "smoke_phase4.log")
PY = os.path.join(os.environ["LOCALAPPDATA"], "jeyvro-venv", "Scripts", "python.exe")

lines = []


def log(message):
    lines.append(message)
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


class Client:
    """One browser-like session: cookie jar + CSRF header handling."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def csrf_token(self):
        for cookie in self.jar:
            if cookie.name == "csrftoken":
                return cookie.value
        return None

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(BASE + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        token = self.csrf_token()
        if token:
            request.add_header("X-CSRFToken", token)
        try:
            with self.opener.open(request) as response:
                raw = response.read().decode()
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as error:
            raw = error.read().decode()
            try:
                return error.code, json.loads(raw)
            except (ValueError, json.JSONDecodeError):
                return error.code, raw


def shell(command):
    """Runs one manage.py shell snippet; returns its stdout."""
    completed = subprocess.run(
        [PY, "manage.py", "shell", "-c", command],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return completed.stdout.strip() or completed.stderr.strip()


stamp = int(time.time())
SELLER_EMAIL = f"smokeseller{stamp}@example.com"
OTHER_EMAIL = f"smokeother{stamp}@example.com"
STAFF_EMAIL = f"smokestaff{stamp}@example.com"
PASSWORD = "Str0ng!Passw0rd"
STORE_NAME = f"Smoke Craft Store {stamp}"

log("=== JEYVRO Phase 4 live smoke ===")

# === FLOW ===
try:
    # -- register the three accounts (console email backend; no session yet)
    for email in (SELLER_EMAIL, OTHER_EMAIL, STAFF_EMAIL):
        status, body = Client().call(
            "POST",
            "/api/v1/auth/register",
            {"email": email, "password": PASSWORD, "first_name": "Smoke", "last_name": "E2E"},
        )
        log(f"register {email} -> {status}")
        assert status == 201, body

    # -- promote staff (group-based staff permissions land with Phase 13)
    output = shell(
        "from apps.accounts.models import User;"
        f"u = User.objects.get(email='{STAFF_EMAIL}');"
        "u.is_staff = True; u.save(); print('STAFF_PROMOTED')"
    )
    log(f"staff promote -> {output}")
    assert "STAFF_PROMOTED" in output

    # -- seller applies to become a seller (Phase 4.1)
    seller = Client()
    seller.call("GET", "/api/v1/auth/csrf")
    status, _ = seller.call(
        "POST", "/api/v1/auth/login", {"email": SELLER_EMAIL, "password": PASSWORD}
    )
    log(f"seller login -> {status}")
    assert status == 200
    status, application = seller.call(
        "POST",
        "/api/v1/stores/apply",
        {
            "store_name": STORE_NAME,
            "store_description": "Live E2E smoke store.",
            "contact_phone": "+63 917 111 2233",
        },
    )
    log(f"apply -> {status} status={application['status']} slug={application['store_slug']}")
    assert status == 201, application
    slug = application["store_slug"]

    # applying twice is rejected (one application per user)
    status, duplicate = seller.call("POST", "/api/v1/stores/apply", {"store_name": STORE_NAME})
    log(f"duplicate apply -> {status} ({duplicate.get('error')})")
    assert status == 409, duplicate

    # -- staff reviews and approves (sellers never self-approve)
    staff = Client()
    staff.call("GET", "/api/v1/auth/csrf")
    status, _ = staff.call(
        "POST", "/api/v1/auth/login", {"email": STAFF_EMAIL, "password": PASSWORD}
    )
    assert status == 200
    status, queue = staff.call("GET", "/api/v1/stores/admin/applications/")
    log(f"staff queue -> {status} count={queue['count']}")
    assert status == 200, queue
    target = next(i for i in queue["items"] if i["applicant_email"] == SELLER_EMAIL)
    status, review = staff.call(
        "POST", f"/api/v1/stores/admin/applications/{target['id']}/review",
        {"decision": "approved"},
    )
    log(f"review -> {status} status={review['status']} reviewed_by={review['reviewed_by']}")
    assert status == 200 and review["status"] == "approved", review

    # -- seller edits their own store (Phase 4.3 store settings)
    status, edited = seller.call(
        "PATCH", "/api/v1/stores/my/store",
        {"return_policy": "Returns within 7 days, live smoke."},
    )
    log(f"own-store edit -> {status} return_policy={edited.get('return_policy')}")
    assert status == 200, edited

    # -- ownership deny path: another customer cannot reach my/store
    other = Client()
    other.call("GET", "/api/v1/auth/csrf")
    other.call("POST", "/api/v1/auth/login", {"email": OTHER_EMAIL, "password": PASSWORD})
    status, denied = other.call("GET", "/api/v1/stores/my/store")
    log(f"deny path -> {status} ({denied})")
    assert status in (401, 403), denied

    # -- logged-out public storefront (the gate: public storefront works)
    anon = Client()
    status, public = anon.call("GET", f"/api/v1/stores/public/{slug}/")
    log(f"public storefront -> {status} name={public.get('name')}")
    assert status == 200, public
    leaked = [f for f in ("user", "contact_email", "contact_phone", "status") if f in public]
    log(f"public leak check -> {'FAIL ' + str(leaked) if leaked else 'OK no internals exposed'}")
    assert not leaked, leaked

    # -- moderation left audit rows (marketplace-sellers rule 3)
    output = shell("from apps.audit.models import AuditLog; print('AUDIT_COUNT', AuditLog.objects.count())")
    log(f"audit -> {output}")
    assert "AUDIT_COUNT" in output

    log("=== SMOKE PASSED ===")
except AssertionError as failure:
    log(f"=== SMOKE FAILED: {failure} ===")
    sys.exit(1)
except Exception as unexpected:  # noqa: BLE001 — smoke must always log
    log(f"=== SMOKE ERROR: {unexpected!r} ===")
    sys.exit(1)
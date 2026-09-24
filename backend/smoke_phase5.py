"""JEYVRO Phase 5 live smoke — drives the REAL runserver over HTTP.

Flow: seeded catalog browse (list/search/filter/sort/detail/categories)
-> seller creates product+variant -> submit -> staff publish (audit)
-> product publicly visible. Writes each step to smoke_phase5.log.
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
LOG_PATH = os.path.join(BACKEND, "smoke_phase5.log")
PY = os.path.join(os.environ["LOCALAPPDATA"], "jeyvro-venv", "Scripts", "python.exe")

lines = []


def log(message):
    lines.append(message)
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


class Client:
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
    completed = subprocess.run(
        [PY, "manage.py", "shell", "-c", command],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return completed.stdout.strip() or completed.stderr.strip()


stamp = int(time.time())
SELLER_EMAIL = f"p5seller{stamp}@example.com"
STAFF_EMAIL = f"p5staff{stamp}@example.com"
PASSWORD = "Str0ng!Passw0rd"
TITLE = f"Smoke Rattan Chair {stamp}"

log("=== JEYVRO Phase 5 live smoke ===")

# === FLOW ===
try:
    # -- public catalog over the real server (seeded data)
    status, catalog = Client().call("GET", "/api/v1/catalog/products/")
    log(f"catalog list -> {status} count={catalog['count']}")
    assert status == 200 and catalog["count"] >= 8, catalog

    status, searched = Client().call("GET", "/api/v1/catalog/products/?q=bamboo")
    titles = [i["title"] for i in searched["items"]]
    log(f"search q=bamboo -> {status} {titles}")
    assert status == 200 and any("Bamboo" in t for t in titles), titles

    status, sorted_items = Client().call(
        "GET", "/api/v1/catalog/products/?sort=price"
    )
    prices = [i["price"] for i in sorted_items["items"]]
    log(f"sort=price -> {status} ascending={prices == sorted(prices)}")
    assert prices == sorted(prices), prices

    first_slug = catalog["items"][0]["slug"]
    status, detail = Client().call(
        "GET", f"/api/v1/catalog/products/{first_slug}/"
    )
    log(f"detail {first_slug} -> {status} price={detail['price']} stock={detail['stock']}")
    assert status == 200 and detail["slug"] == first_slug

    status, categories = Client().call("GET", "/api/v1/catalog/categories/")
    log(f"categories -> {status} count={categories['count']}")
    assert status == 200 and categories["count"] >= 3, categories

    # -- seller setup through the real API (Phase 4 flow)
    anon = Client()
    status, _ = anon.call(
        "POST", "/api/v1/auth/register",
        {"email": SELLER_EMAIL, "password": PASSWORD,
         "first_name": "P5", "last_name": "Smoke"},
    )
    assert status == 201
    status, _ = anon.call(
        "POST", "/api/v1/auth/login", {"email": SELLER_EMAIL, "password": PASSWORD}
    )
    assert status == 200
    status, application = anon.call(
        "POST", "/api/v1/stores/apply",
        {"store_name": f"P5 Smoke Store {stamp}",
         "store_description": "Phase 5 smoke.", "contact_phone": ""},
    )
    assert status == 201, application
    log(f"store application -> {status} slug={application['store_slug']}")

    # -- staff approves the seller application
    staff = Client()
    staff.call("GET", "/api/v1/auth/csrf")
    staff.call("POST", "/api/v1/auth/register",
               {"email": STAFF_EMAIL, "password": PASSWORD,
                "first_name": "P5", "last_name": "Staff"})
    output = shell(
        "from apps.accounts.models import User;"
        f"u = User.objects.get(email='{STAFF_EMAIL}');"
        "u.is_staff = True; u.save(); print('STAFF_OK')"
    )
    assert "STAFF_OK" in output
    staff.call("POST", "/api/v1/auth/login", {"email": STAFF_EMAIL, "password": PASSWORD})
    status, queue = staff.call("GET", "/api/v1/stores/admin/applications/")
    target = next(i for i in queue["items"] if i["applicant_email"] == SELLER_EMAIL)
    status, review = staff.call(
        "POST", f"/api/v1/stores/admin/applications/{target['id']}/review",
        {"decision": "approved"},
    )
    log(f"store approved -> {status} store_status={review['store_status']}")
    assert status == 200 and review["store_status"] == "active", review

# === FLOW PART 2 ===
    # -- seller re-logs in (the review switched sessions), creates product+variant
    seller = Client()
    seller.call("GET", "/api/v1/auth/csrf")
    status, _ = seller.call(
        "POST", "/api/v1/auth/login", {"email": SELLER_EMAIL, "password": PASSWORD}
    )
    assert status == 200

    status, product = seller.call(
        "POST", "/api/v1/catalog/my/products/",
        {"title": TITLE, "base_price": "1299.00",
         "description": "Live smoke rattan chair.", "compare_at_price": "1599.00"},
    )
    log(f"product created -> {status} status={product.get('status')}")
    assert status == 201 and product["status"] == "draft", product

    status, variant = seller.call(
        "POST", f"/api/v1/catalog/my/products/{product['id']}/variants/",
        {"price": "1299.00", "name": "Natural", "initial_stock": 7},
    )
    log(f"variant created -> {status} sku={variant.get('sku')} on_hand={variant['inventory']['on_hand']}")
    assert status == 201 and variant["inventory"]["on_hand"] == 7, variant

    # draft is NOT public yet
    status, _detail = seller.call("GET", f"/api/v1/catalog/products/{product['slug']}/")
    log(f"draft public detail (expect 404) -> {status}")
    assert status == 404

    # stock adjust: +5 restock, then -2 adjustment
    status, adjusted = seller.call(
        "POST", "/api/v1/catalog/my/stock",
        {"variant_id": variant["id"], "delta": 5, "note": "restock smoke"},
    )
    assert status == 200 and adjusted["inventory"]["on_hand"] == 12, adjusted
    status, adjusted = seller.call(
        "POST", "/api/v1/catalog/my/stock",
        {"variant_id": variant["id"], "delta": -2},
    )
    log(f"stock 7 -> +5 -> -2 = {adjusted['inventory']['on_hand']}")
    assert status == 200 and adjusted["inventory"]["on_hand"] == 10, adjusted

    status, submitted = seller.call(
        "POST", f"/api/v1/catalog/my/products/{product['id']}/submit/"
    )
    log(f"submit -> {status} status={submitted.get('status')}")
    assert status == 200 and submitted["status"] == "pending_review", submitted

    # -- staff publishes (audit-logged)
    status, published = staff.call(
        "POST", f"/api/v1/catalog/admin/products/{product['id']}/review",
        {"decision": "published"},
    )
    log(f"staff publish -> {status} status={published.get('status')}")
    assert status == 200 and published["status"] == "published", published

    # -- the product is now publicly visible with server-resolved values
    anon2 = Client()
    status, public = anon2.call("GET", f"/api/v1/catalog/products/{product['slug']}/")
    log(f"public detail -> {status} price={public.get('price')} discount={public.get('discount')} stock={public.get('stock')}")
    assert status == 200, public
    assert float(public["price"]) == 1299.00, public["price"]
    assert public["discount"] == 19, public["discount"]  # (1599-1299)/1599
    assert public["stock"] == 10, public["stock"]

    output = shell(
        "from apps.audit.models import AuditLog;"
        "print('AUDIT', [a for a in AuditLog.objects.values_list('action', flat=True) if 'product' in a][-3:])"
    )
    log(f"audit -> {output}")
    assert "product_review_published" in output

    log("=== SMOKE PASSED ===")
except AssertionError as failure:
    log(f"=== SMOKE FAILED: {failure} ===")
    sys.exit(1)
except Exception as unexpected:  # noqa: BLE001 — smoke must always log
    log(f"=== SMOKE ERROR: {unexpected!r} ===")
    sys.exit(1)
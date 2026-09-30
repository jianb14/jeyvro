"""
Django settings for the JEYVRO backend.

Environment-driven per PROJECT_CONTEXT §10.5: secrets live in backend/.env
(never committed); `.env.example` documents every variable. Never hardcode
secrets here (C7).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env in development; production provides real env vars.
load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [
    host.strip()
    for host in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    # Third-party
    'rest_framework',
    'corsheaders',
    # JEYVRO apps
    'apps.common',
    'apps.accounts',
    'apps.core',
    'apps.audit',
    'apps.stores',
    'apps.catalog',
    'apps.cart',
    'apps.orders',
    'apps.payments',
    'apps.platform',
    'apps.reviews',
    'apps.messaging',
    'apps.moderation',
    'apps.notifications',
    'apps.promotions',
    'apps.resolutions',
    'apps.reporting',
    'apps.search',
]

MIDDLEWARE = [
    # CORS must run before CommonMiddleware (django-cors-headers docs)
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Custom user model — email-as-username (Phase 3, PROJECT_CONTEXT §4).
AUTH_USER_MODEL = 'accounts.User'

# Email — console backend in development (emails print to the runserver log;
# no mail server needed). Production SMTP config lands with deployment.
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = 'JEYVRO <no-reply@jeyvro.local>'

# Database — PostgreSQL is the primary database (PROJECT_CONTEXT C5/C6).
# Money/quantities will use DecimalField (backend-core rule 3).

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', 'jeyvro'),
        'USER': env('DB_USER', 'postgres'),
        'PASSWORD': env('DB_PASSWORD', ''),
        'HOST': env('DB_HOST', '127.0.0.1'),
        'PORT': env('DB_PORT', '5432'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'  # PH market (PROJECT_CONTEXT C6)
USE_I18N = True
USE_TZ = True

# Static + media (Phase 5: product images upload to local media/ in dev;
# production moves to object storage + CDN, PROJECT_CONTEXT §17).
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Upload safety net (per-file validation also runs in services — §10.1).
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

# Payments (Phase 9) — COD ships now; the online-gateway seam is configured
# by environment when PayMongo/GCash/Maya land (§17). Sandbox mode enables
# the generic adapter's fake checkout so the webhook flow is testable.
PAYMENTS_PAYMENT_EXPIRY_HOURS = int(env('PAYMENTS_PAYMENT_EXPIRY_HOURS', '24'))
PAYMENTS_GATEWAY_WEBHOOK_SECRET = env('PAYMENTS_GATEWAY_WEBHOOK_SECRET', '')
PAYMENTS_GATEWAY_CHECKOUT_URL = env('PAYMENTS_GATEWAY_CHECKOUT_URL', '')
PAYMENTS_GATEWAY_SANDBOX = env('PAYMENTS_GATEWAY_SANDBOX', 'False').lower() in {
    '1',
    'true',
    'yes',
}

# Returns (Phase 17) — how long after delivery a customer may file a return
# (§17.1). Deploy-time policy like the payment window above; the resolution
# policy module reads it, and the deadline is snapshotted onto each case.
RETURNS_WINDOW_DAYS = int(env('RETURNS_WINDOW_DAYS', '7'))

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
#
# §20.1: **deny by default** (security skill rule 6). A view that forgets to
# declare its permissions is now *private*, not public — the public surfaces
# (auth, catalog, storefront, search, tracking, the health probe) opt out
# explicitly, and `tests/test_security_hardening.py` fails the gate if a new
# view forgets to speak for itself.

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Session auth only, pinned: DRF's default list also enables HTTP Basic,
    # which this API never intends — a session cookie plus CSRF is the whole
    # story, and Basic would let credentials ride in a header instead (§10.1).
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    # {count, items} envelope on every list endpoint (§8)
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.CountItemsPagination',
    'PAGE_SIZE': 20,
    # {error, detail?, field_errors?} envelope on every DRF-handled error
    'EXCEPTION_HANDLER': 'apps.common.exceptions.jeyvro_exception_handler',

    # §20.1 rate limiting. A blunt default (every endpoint) plus a few tight
    # scopes on the endpoints worth abusing; rates are deploy-time config.
    # The test suite lifts this wholesale (tests/conftest.py) and proves the
    # behaviour explicitly with its own rates, so no gate depends on a clock.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        # Views that set `throttle_scope` (login, register, checkout, message)
        # draw from their own bucket here; a view without one is a no-op.
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # DRF rate strings are `count/period` (`s`, `m`, `h`, `d`) — a bare
        # number is not a rate at all, and it 500s every request the moment
        # `parse_rate` meets it. `test_security_hardening.py` proves the shape.
        'anon': env('THROTTLE_ANON_PER_MINUTE', '120/min'),
        'user': env('THROTTLE_USER_PER_MINUTE', '600/min'),
        # Scopes — declared per view via `throttle_scope`.
        'auth': env('THROTTLE_AUTH_PER_MINUTE', '10/min'),
        'register': env('THROTTLE_REGISTER_PER_HOUR', '10/hour'),
        'checkout': env('THROTTLE_CHECKOUT_PER_MINUTE', '20/min'),
        'message': env('THROTTLE_MESSAGE_PER_MINUTE', '30/min'),
        # §20.2 — starting threads is the flood surface the `message` scope
        # misses: 30 sends/min is a burst *inside* one thread, while opening a
        # thread per store is 1 request each and was never counted anywhere.
        'conversation': env('THROTTLE_CONVERSATION_PER_HOUR', '20/hour'),
    },
    'SCOPED_THROTTLES': {
        'auth': 'rest_framework.throttling.ScopedRateThrottle',
        'register': 'rest_framework.throttling.ScopedRateThrottle',
        'checkout': 'rest_framework.throttling.ScopedRateThrottle',
        'message': 'rest_framework.throttling.ScopedRateThrottle',
        'conversation': 'rest_framework.throttling.ScopedRateThrottle',
    },
}

# CORS — dev allowlist for the Vite dev server. Never widen to '*' in
# production (backend-api / security skills).

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in env(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if origin.strip()
]

# Session auth travels with `credentials: 'include'`, so an allowlisted origin
# must also be *told* it may send credentials — django-cors-headers defaults
# this to False, which would silently break every cross-origin session request
# in production while the allowlist still looked correct (§10.4).
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_ALLOW_METHODS = [
    'delete', 'get', 'options', 'patch', 'post', 'put',
]

# CSRF — the SPA posts with X-CSRFToken from the csrf cookie; the Vite dev
# origin is trusted so session-authenticated cross-origin requests validate.
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env(
        'CSRF_TRUSTED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if origin.strip()
]

# Session cookies — SameSite=Lax keeps session-auth safe for the SPA on the
# same site; Secure is enforced in production settings (Phase 23).

SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Logging foundation — console logs in dev; production config lands with
# the deployment phase. Request correlation (X-Request-ID) is deferred.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': env('DJANGO_LOG_LEVEL', 'INFO'),
    },
}


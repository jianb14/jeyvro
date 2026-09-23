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
    # Third-party
    'rest_framework',
    'corsheaders',
    # JEYVRO apps
    'apps.common',
    'apps.accounts',
    'apps.core',
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

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
# Foundation defaults: the health probe is public by design. Every domain
# viewset added in later phases must declare its own permission class
# explicitly (backend-api rule 6 — nothing ships public by accident).

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    # {count, items} envelope on every list endpoint (§8)
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.CountItemsPagination',
    'PAGE_SIZE': 20,
    # {error, detail?, field_errors?} envelope on every DRF-handled error
    'EXCEPTION_HANDLER': 'apps.common.exceptions.jeyvro_exception_handler',
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


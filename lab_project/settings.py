"""
Django settings for lab_project project.
"""

import os
import dj_database_url
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# CORE SETTINGS
# ==============================================================================

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-only-change-in-prod')

# DEBUG is True locally (from .env), False on Render (where DEBUG=False)
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

def _env_csv(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


# Render gives you a hostname like your-app.onrender.com.
# We keep ALLOWED_HOSTS configurable via env var and auto-include Render hostname.
ALLOWED_HOSTS = _env_csv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = _env_csv('CSRF_TRUSTED_ORIGINS')
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f'https://{RENDER_EXTERNAL_HOSTNAME}'
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)


# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'labapp',
]

# Cloudinary is optional. Keep local file storage by default and enable
# Cloudinary only when explicitly requested via environment variable.
ENABLE_CLOUDINARY = os.environ.get('ENABLE_CLOUDINARY', 'False') == 'True'
if ENABLE_CLOUDINARY:
    INSTALLED_APPS += [
        'cloudinary',
        'cloudinary_storage',
    ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # Serves static files on Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lab_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lab_project.wsgi.application'


# ==============================================================================
# DATABASE — Neon PostgreSQL via DATABASE_URL env var
# Your .env / Render env var:
#   DATABASE_URL=postgresql://neondb_owner:...@ep-aged-rain-...neon.tech/neondb?sslmode=require&channel_binding=require
# ==============================================================================

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=False,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==============================================================================
# INTERNATIONALISATION
# ==============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# ==============================================================================
# STATIC FILES
# WhiteNoise serves /static/ directly from Render — no S3 needed for static assets.
# Run `python manage.py collectstatic` (done automatically in build.sh).
# ==============================================================================

STATIC_URL = '/static/'

# Where Django looks for static files during development
STATICFILES_DIRS = [BASE_DIR / 'static']

# Where collectstatic puts everything for production (Render reads from here)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise compression without strict manifest requirement.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

if ENABLE_CLOUDINARY:
    STORAGES["default"] = {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    }

# Serve static files from STATICFILES_DIRS when collectstatic is missing.
WHITENOISE_USE_FINDERS = True


# ==============================================================================
# MEDIA FILES
# Render's disk is ephemeral — uploads survive restarts but NOT redeploys.
# For persistent uploads, swap DEFAULT_FILE_STORAGE to Cloudinary (see README).
# ==============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ==============================================================================
# EMAIL — Gmail SMTP
# Move the password to an environment variable (never hardcode it).
# Add  EMAIL_HOST_PASSWORD=<your-app-password>  to .env and Render env vars.
# ==============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'lms23022006@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ==============================================================================
# SECURITY — extra headers turned ON when DEBUG=False (i.e. on Render)
# ==============================================================================

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ==============================================================================
# DEFAULT PRIMARY KEY
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

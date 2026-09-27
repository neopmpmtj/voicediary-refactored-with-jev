from decouple import Csv, config

from .base import *  # noqa: F403

DEBUG = True

SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-dev-only-not-for-production",
)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv(), default="localhost,127.0.0.1")

GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET", default="")
GOOGLE_OAUTH_REDIRECT_URI = config(
    "GOOGLE_OAUTH_REDIRECT_URI",
    default="http://localhost:8000/accounts/google/callback/",
)

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

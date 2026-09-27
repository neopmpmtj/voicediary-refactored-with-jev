---
name: Dev prod settings
overview: "Split Django settings the way the sample does: shared base, plus dev, prod, and test modules, selected by DJANGO_SETTINGS_MODULE for local work, production, and CI."
todos:
  - id: split-settings
    content: Replace config/settings.py with base, dev, prod, and test modules
    status: completed
  - id: wire-selectors
    content: Point manage.py, wsgi, asgi, pytest.ini, and .env.example at the split modules
    status: completed
isProject: false
---

# Dev / prod / test settings split

Keep the project package as [`config/`](config/). Do not rename it to `conf/`. Match the sample layout under [`sample-old-version-delete-when-finished-using/src/utter_it/settings/`](sample-old-version-delete-when-finished-using/src/utter_it/settings/): `base.py`, `dev.py`, `prod.py`, `test.py`.

## Layout

Replace the single [`config/settings.py`](config/settings.py) with a package:

```text
config/settings/
  __init__.py
  base.py
  dev.py
  prod.py
  test.py
```

Move current contents of `settings.py` into `base.py`: apps, middleware, SQLite, auth user, login URLs, media, upload limits. Leave `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, and TLS cookie flags out of base; those belong in the env-specific files.

## Per environment (same rules as the sample)

[`dev.py`](sample-old-version-delete-when-finished-using/src/utter_it/settings/dev.py):

- `from .base import *`
- `DEBUG = True`
- `SECRET_KEY` and `ALLOWED_HOSTS` from env, with local defaults
- Google OAuth from env, redirect default `http://localhost:8000/accounts/google/callback/`
- SSL redirect and secure cookies off

[`prod.py`](sample-old-version-delete-when-finished-using/src/utter_it/settings/prod.py):

- `DEBUG = False`
- `SECRET_KEY` and `ALLOWED_HOSTS` required (no insecure defaults)
- Google OAuth required
- Secure cookies, HSTS, `SECURE_SSL_REDIRECT`, `USE_X_FORWARDED_HOST`, `SECURE_PROXY_SSL_HEADER`

[`test.py`](sample-old-version-delete-when-finished-using/src/utter_it/settings/test.py):

- `from .dev import *`
- Thin overlay for CI. No Celery yet, so no `CELERY_TASK_ALWAYS_EAGER`. Keep the file so pytest and `manage.py test` have a dedicated module.

## How the process picks a file

Same pattern as sample [`manage.py`](sample-old-version-delete-when-finished-using/manage.py) and [`wsgi.py`](sample-old-version-delete-when-finished-using/src/utter_it/wsgi.py):

- [`manage.py`](manage.py): if `test` is in `sys.argv`, force `config.settings.test`. Otherwise `setdefault` from `DJANGO_SETTINGS_MODULE`, default `config.settings.dev`.
- [`config/wsgi.py`](config/wsgi.py) and [`config/asgi.py`](config/asgi.py): `setdefault` from env, default `config.settings.dev`.

[`pytest.ini`](pytest.ini): `DJANGO_SETTINGS_MODULE = config.settings.test`.

## Env files

[`.env.example`](.env.example): `DJANGO_SETTINGS_MODULE=config.settings.dev`.

[`.env`](.env): same value for local work (it currently points at `config.settings`). Production deploy sets `config.settings.prod`.

Do not copy secrets. Do not switch the database to Postgres in this change.

## Verify

`.venv/bin/python -c "import django; django.setup()"` with `DJANGO_SETTINGS_MODULE=config.settings.dev`, `manage.py check`, and `.venv/bin/pytest -q`.

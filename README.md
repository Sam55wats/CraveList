# CraveList

CraveList is a Django REST Framework backend for an AI-powered restaurant discovery app.

## Local Backend

```bash
cd apps
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py seed_restaurants
./.venv/bin/python manage.py runserver
```

Useful local URLs:

- `http://127.0.0.1:8000/api/health/`
- `http://127.0.0.1:8000/api/docs/`
- `http://127.0.0.1:8000/api/restaurants/`
- `http://127.0.0.1:8000/api/external-restaurants/search/?q=taco`
- `http://127.0.0.1:8765/outputs/cravelist-test-webapp/index.html`
- `http://127.0.0.1:8765/outputs/backend-finish-rundown/index.html`

The test web app is a temporary product-style browser page for testing the
backend before the real React frontend exists. The rundown page explains what
was implemented.

## Backend Checks

```bash
cd apps
./.venv/bin/python manage.py test accounts restaurants
./.venv/bin/python manage.py check
```

## Environment Variables

- `DJANGO_SECRET_KEY`: overrides the local development secret key.
- `DJANGO_DEBUG`: set to `false` outside local development.
- `DJANGO_ALLOWED_HOSTS`: comma-separated hostnames for deployed environments.

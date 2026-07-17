# Air Conditioning Services ERP Demo

This is a standalone demo copy of the AC service ERP. It is safe for client presentations and uses fictional demo data only.

## Project Path

`/Users/yuvraj/Documents/AC WEBAPP/puriaccooling-demo`

## Demo Accounts

CEO / Owner demo:

- Username: `demo_ceo`
- Password: `Demo@12345`

Manager demo:

- Username: `demo_manager`
- Password: `Demo@12345`

## Setup From This Folder

```bash
cd "/Users/yuvraj/Documents/AC WEBAPP/puriaccooling-demo"
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py reset_demo_data
python manage.py runserver 127.0.0.1:8000
```

Open:

- Public demo page: `http://127.0.0.1:8000/`
- Login page: `http://127.0.0.1:8000/login/`
- Dashboard after login: `http://127.0.0.1:8000/dashboard/`

## Demo Reset Command

Use this whenever the demo needs to be restored to the same predictable records:

```bash
source venv/bin/activate
python manage.py reset_demo_data
```

The reset command is guarded to run only when Django `BASE_DIR` and the database path are inside `puriaccooling-demo`.

## Environment Variables

Copy `.env.example` if you want local overrides. The app also runs with demo-safe defaults.

Main variables:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DEMO_COMPANY_NAME`
- `DEMO_APP_NAME`
- `DEMO_COMPANY_TAGLINE`
- `DEMO_PUBLIC_DOMAIN`
- `DEMO_CONTACT_EMAIL`
- `DEMO_CONTACT_PHONE`
- `DEMO_LOGO_TEXT`
- `DEMO_BRAND_YEAR`

## Railway Deployment

Use this repository as a demo deployment only. Add a PostgreSQL database in Railway and link it to the web service so Railway provides `DATABASE_URL`.

Required Railway variables:

- `DJANGO_SECRET_KEY`: set a new long random value
- `DJANGO_DEBUG`: `False`
- `DJANGO_ALLOWED_HOSTS`: `.railway.app,your-custom-domain.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS`: `https://your-railway-domain.up.railway.app,https://your-custom-domain.com`
- `DEMO_COMPANY_NAME`: `Demo AC Company` or your demo brand
- `DEMO_APP_NAME`: `Air Conditioning Services ERP`

The `Procfile` runs migrations, collects static files, reseeds fictional demo data, and starts Gunicorn. The reset command uses `DEMO_RESET_CONFIRM=allow` inside the Procfile so it can run safely on the demo Railway database.

## Safety Notes

- This demo uses its own SQLite database at `puriaccooling-demo/db.sqlite3`.
- This demo uses its own virtual environment at `puriaccooling-demo/venv`.
- Production media, client database, and production secrets are not copied into this demo.
- Do not deploy this demo with the default demo credentials unchanged.

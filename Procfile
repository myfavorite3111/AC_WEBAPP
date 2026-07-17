web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && DEMO_RESET_CONFIRM=allow python manage.py reset_demo_data && gunicorn puriaccooling.wsgi --bind 0.0.0.0:$PORT

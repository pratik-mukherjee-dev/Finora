@echo off
python -m nuitka ^
  --standalone ^
  --output-filename=finora-backend-debug ^
  --include-package=apps ^
  --include-package=config ^
  --include-package=django ^
  --include-package=rest_framework ^
  --include-package=django_filters ^
  --include-package=psycopg ^
  --include-package=waitress ^
  --include-module=config.wsgi ^
  --module-parameter=django-settings-module=config.settings.production ^
  --include-data-dir=apps=apps ^
  --include-data-dir=config=config ^
  --assume-yes-for-downloads ^
  run_server.py

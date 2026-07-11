@echo off
python -m nuitka ^
  --standalone ^
  --onefile ^
  --output-filename=finora-backend ^
  --include-package=apps ^
  --include-package=config ^
  --include-package=django ^
  --include-package-data=django ^
  --include-package=rest_framework ^
  --include-package-data=rest_framework ^
  --include-package=rest_framework_simplejwt ^
  --include-package-data=rest_framework_simplejwt ^
  --include-package=django_filters ^
  --include-package=psycopg ^
  --include-package=waitress ^
  --include-module=config.wsgi ^
  --module-parameter=django-settings-module=config.settings.production ^
  --assume-yes-for-downloads ^
  --windows-console-mode=disable ^
  run_server.py

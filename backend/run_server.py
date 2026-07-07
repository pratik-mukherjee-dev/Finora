import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")


def main():
    rc = os.environ.get("FINORA_RUNTIME_CONFIG", "")
    if not rc or not Path(rc).is_file():
        raise SystemExit(
            "FINORA_RUNTIME_CONFIG missing — Tauri must write runtime config before starting backend."
        )

    from django.core.management import call_command
    import django

    django.setup()
    call_command("migrate", interactive=False, verbosity=1)

    from waitress import serve
    from config.wsgi import application

    port = int(os.environ.get("DJANGO_PORT", "8799"))
    serve(application, host="127.0.0.1", port=port, threads=8)


if __name__ == "__main__":
    main()

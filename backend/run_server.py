import io
import os
import sys
from pathlib import Path

# The windowed Nuitka build (--windows-console-mode=disable) starts with no
# console attached, so sys.stdout / sys.stderr are None. Anything that writes
# to them — Django's migrate output, warnings, tracebacks — raises
# AttributeError: 'NoneType' object has no attribute 'write'. Redirect both to
# os.devnull before Django is imported or configured.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

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
    call_command("migrate", interactive=False, verbosity=0, stdout=io.StringIO())

    from waitress import serve
    from config.wsgi import application

    port = int(os.environ.get("DJANGO_PORT", "8799"))
    serve(application, host="127.0.0.1", port=port, threads=8)


if __name__ == "__main__":
    main()
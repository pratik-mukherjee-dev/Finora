"""Open a Django shell against the SAME database the Tauri app uses.

The app's Postgres runs on a random port and its params are written to
runtime.json by the Tauri bootstrap. A plain `manage.py shell` ignores that and
falls back to base.py's 5432 defaults (a DIFFERENT, usually empty DB), which is
why a manual shell can return [] while the app clearly has the data.

Usage (from backend/, app must be running so runtime.json exists):
    python dbshell_runtime.py
It locates runtime.json in the OS app-data dir, exports FINORA_RUNTIME_CONFIG,
then drops into the Django shell bound to the live sidecar DB.
"""
import os
import sys
from pathlib import Path


def _app_data_dir() -> Path:
    # Matches Tauri's app_data_dir() for identifier com.byteforce.finora on Windows.
    if os.name == "nt":
        base = Path(os.environ["APPDATA"])
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "com.byteforce.finora"


def main() -> None:
    runtime = _app_data_dir() / "runtime.json"
    if not runtime.is_file():
        sys.exit(f"runtime.json not found at {runtime}. Is the app running?")
    os.environ["FINORA_RUNTIME_CONFIG"] = str(runtime)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    print(f"Using runtime config: {runtime}")
    print(f"Contents: {runtime.read_text()}")

    from django.core.management import execute_from_command_line

    execute_from_command_line([sys.argv[0], "shell"])


if __name__ == "__main__":
    main()

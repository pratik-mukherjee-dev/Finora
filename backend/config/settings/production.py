import json
import os
from pathlib import Path
from .base import *  # noqa

DEBUG = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# Runtime config written by the Tauri bootstrap (embedded Postgres port, data dir).
# Do NOT raise here — settings must stay importable for the Nuitka build and
# for `collectstatic`. The hard requirement is enforced at startup in run_server.py.
_runtime = os.environ.get("FINORA_RUNTIME_CONFIG", "")
if _runtime and Path(_runtime).is_file():
    cfg = json.loads(Path(_runtime).read_text())
    DATABASES["default"].update({
        "NAME": cfg.get("db_name", "finora"),
        "USER": cfg.get("db_user", "finora"),
        "PASSWORD": cfg.get("db_password", "finora"),
        "HOST": cfg.get("db_host", "127.0.0.1"),
        "PORT": str(cfg.get("db_port", "5432")),
    })

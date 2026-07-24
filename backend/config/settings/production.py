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

FINORA_DEV_MODE = os.environ.get("FINORA_DEV_MODE", "0") == "1"

# Runtime config written by the Tauri bootstrap (embedded Postgres port, data dir).
# In the packaged app this is the ONLY source of truth for the DB connection.
# We deliberately do not fall back to base.py's DB_* / 5432 defaults here: doing
# so previously let a stale value bind the frozen backend to a different Postgres
# than the sidecar, so writes and reads landed in different databases.
_runtime = os.environ.get("FINORA_RUNTIME_CONFIG", "")
if _runtime and Path(_runtime).is_file():
    cfg = json.loads(Path(_runtime).read_text())
    DATABASES["default"].update({
        "NAME": cfg["db_name"],
        "USER": cfg["db_user"],
        "PASSWORD": cfg["db_password"],
        "HOST": cfg["db_host"],
        "PORT": str(cfg["db_port"]),
    })
else:
    # run_server.py already hard-requires FINORA_RUNTIME_CONFIG before serving,
    # so reaching here means a misconfiguration; keep base defaults for
    # collectstatic/build importability only.
    pass

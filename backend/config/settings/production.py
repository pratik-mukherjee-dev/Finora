import json
from pathlib import Path
from .base import *  # noqa

DEBUG = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Runtime config written by the Tauri bootstrap (embedded Postgres port, data dir).
_runtime = Path(os.environ.get("FINORA_RUNTIME_CONFIG", ""))
if _runtime.is_file():
    cfg = json.loads(_runtime.read_text())
    DATABASES["default"].update({
        "NAME": cfg.get("db_name", "finora"),
        "USER": cfg.get("db_user", "finora"),
        "PASSWORD": cfg.get("db_password", "finora"),
        "HOST": cfg.get("db_host", "127.0.0.1"),
        "PORT": str(cfg.get("db_port", "5432")),
    })

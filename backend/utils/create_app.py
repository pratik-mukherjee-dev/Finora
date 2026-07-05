import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPS_DIR = PROJECT_ROOT / "apps"
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings" / "base.py"


def write_file(path: Path, content: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_app(app_name: str, packages=None):
    MODULES = [
        "models",
        "views",
        "admin",
        "selectors",
        "services",
        "serializers",
    ]

    if not re.fullmatch(r"[a-z][a-z0-9_]*", app_name):
        print("❌ Invalid app name.")
        sys.exit(1)

    app_dir = APPS_DIR / app_name

    if app_dir.exists():
        print(f"❌ App '{app_name}' already exists.")
        sys.exit(1)

    # Root package
    write_file(app_dir / "__init__.py")

    # Apps
    write_file(
        app_dir / "apps.py",
        f"""from django.apps import AppConfig


class {app_name.capitalize()}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.{app_name}"
""",
    )

    # URLs
    write_file(
        app_dir / "urls.py",
        """from django.urls import path

urlpatterns = []
""",
    )

    # Tests
    write_file(
        app_dir / "tests.py",
        """from django.test import TestCase
""",
    )

    # Modules
    for module in MODULES:
        if module in packages:
            write_file(app_dir / module / "__init__.py")
        else:
            write_file(app_dir / f"{module}.py")

    # Migrations
    write_file(app_dir / "migrations" / "__init__.py")

    print(f"✅ App '{app_name}' created successfully.")

    register_app(app_name)


def register_app(app_name: str):
    text = SETTINGS_FILE.read_text(encoding="utf-8")

    app_entry = f"'apps.{app_name}',"

    if app_entry in text:
        print("ℹ️ App already registered.")
        return

    pattern = r"INSTALLED_APPS\s*=\s*\[(.*?)\]"
    match = re.search(pattern, text, flags=re.DOTALL)

    if not match:
        print("⚠️ Could not update INSTALLED_APPS.")
        return

    content = match.group(1).rstrip()

    new_content = content + f"\n    {app_entry}\n"

    text = text.replace(match.group(1), new_content)

    SETTINGS_FILE.write_text(text, encoding="utf-8")

    print("✅ Added to INSTALLED_APPS.")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("Usage:")
        print("python utils/create_app.py app_name")
        sys.exit(1)

    packages = []

    if len(sys.argv) == 3:
        packages = [
            p.strip()
            for p in sys.argv[2].split(",")
            if p.strip()
        ]

    create_app(sys.argv[1], packages)

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")


def main():
    from django.core.management import call_command
    import django

    django.setup()
    # Ensure schema is current on the client's machine
    call_command("migrate", interactive=False, verbosity=1)

    from waitress import serve
    from config.wsgi import application

    port = int(os.environ.get("DJANGO_PORT", "8799"))
    serve(application, host="127.0.0.1", port=port, threads=8)


if __name__ == "__main__":
    main()

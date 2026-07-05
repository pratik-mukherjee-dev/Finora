from django.db import transaction


def atomic(fn):
    def wrapper(*args, **kwargs):
        with transaction.atomic():
            return fn(*args, **kwargs)
    return wrapper

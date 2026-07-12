from django.db import transaction

from ..common.exceptions import LicenseError, DomainError
from .models import Company, UserCompanySetting, License, User


class AlreadyInitialized(Exception):
    """Raised when registration is attempted but a local account already exists."""
    pass


@transaction.atomic
def register_first_user(username, password):
    """First-run only: create the single local user + base license + setting.

    Guards on User.objects.exists() inside the transaction so a second call can
    never create a competing account. Password is hashed by create_user.
    """
    if User.objects.exists():
        raise AlreadyInitialized()
    user = User.objects.create_user(username=username, password=password)
    License.objects.create(
        user=user, plan="base", mode=License.SINGLE, is_active=True
    )
    UserCompanySetting.objects.create(
        user=user,
        active_mode=UserCompanySetting.SINGLE,
        segregation_enabled=False,
        is_mode_locked=True,
    )
    return user


@transaction.atomic
def create_company(user, name, make_default=False):
    setting = UserCompanySetting.objects.select_for_update().filter(user=user).first()
    if (
        setting
        and setting.active_mode == UserCompanySetting.SINGLE
        and user.companies.exists()
    ):
        raise LicenseError("Single-company mode allows only one company.")
    if make_default:
        Company.objects.filter(user=user, is_default=True).update(is_default=False)
    company = Company.objects.create(user=user, name=name, is_default=make_default)
    if setting and setting.default_company_id is None:
        setting.default_company = company
        setting.save(update_fields=["default_company"])
    return company


@transaction.atomic
def switch_to_multi(user, segregation_enabled=False):
    lic = License.objects.select_for_update().filter(user=user).first()
    if not lic or not lic.allows_multi:
        raise LicenseError("Multi-company mode is not unlocked for this license.")
    setting, _ = UserCompanySetting.objects.select_for_update().get_or_create(user=user)
    setting.active_mode = UserCompanySetting.MULTI
    setting.segregation_enabled = segregation_enabled
    setting.is_mode_locked = True
    setting.save()
    return setting


@transaction.atomic
def set_segregation(user, enabled):
    setting = UserCompanySetting.objects.select_for_update().get(user=user)
    if setting.active_mode != UserCompanySetting.MULTI:
        raise DomainError("Segregation applies only in multi-company mode.")
    setting.segregation_enabled = enabled
    setting.save(update_fields=["segregation_enabled"])
    return setting
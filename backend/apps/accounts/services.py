from django.db import transaction
from apps.ledgers.services import seed_default_ledgers
from ..common.exceptions import LicenseError, DomainError
from .models import Company, UserCompanySetting, License, User, SettlementMode


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
    seed_default_ledgers(user)
    seed_default_settlement_modes(user)
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

    lic = License.objects.filter(user=user).first()
    if lic and user.companies.count() >= lic.max_companies:
        raise LicenseError(f"Your license allows a maximum of {lic.max_companies} companies.")

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
def switch_to_single(user):
    setting = UserCompanySetting.objects.select_for_update().get(user=user)
    setting.active_mode = UserCompanySetting.SINGLE
    setting.segregation_enabled = False
    setting.save(
        update_fields=["active_mode", "segregation_enabled"]
    )
    return setting


@transaction.atomic
def set_segregation(user, enabled):
    setting = UserCompanySetting.objects.select_for_update().get(user=user)
    if setting.active_mode != UserCompanySetting.MULTI:
        raise DomainError("Segregation applies only in multi-company mode.")
    setting.segregation_enabled = enabled
    setting.save(update_fields=["segregation_enabled"])
    return setting


# (name, is_system, category, bank_type)
DEFAULT_SETTLEMENT_MODES = (
    ("Cash", True, "CASH", None),
    ("UPI", False, "BANK", "UPI"),
    ("Bank Transfer", False, "BANK", "TRANSFER"),
)

@transaction.atomic
def seed_default_settlement_modes(user):
    """
    Idempotent: create standard settlement modes if mising.
    :param user:
    :return: list of created settlement modes
    """
    created = []
    for i, (name, is_system, category, bank_type) in enumerate(DEFAULT_SETTLEMENT_MODES):
        obj, was_created = SettlementMode.objects.get_or_create(
            user=user,
            name=name,
            defaults={
                "is_system": is_system,
                "category": category,
                "bank_type": bank_type,
                "sort_order": i,
                "created_by": user
            }
        )
        if was_created:
            created.append(obj)
    return created


@transaction.atomic
def create_settlement_mode(user, name, sort_order=0, category="CASH", bank_type=None):
    name = name.strip()
    if not name:
        raise DomainError("Settlement mode name is required.")
    if category == 'CASH':
        bank_type = None
    return SettlementMode.objects.get_or_create(
        user=user,
        name=name,
        defaults={
            'is_system': False,
            'category': category,
            'bank_type': bank_type,
            'sort_order': sort_order,
            'created_by': user
        }
    )


@transaction.atomic
def delete_settlement_mode(user, mode_id):
    mode = SettlementMode.objects.filter(user=user, pk=mode_id).first()
    if not mode:
        raise DomainError("Settlement mode not found.")
    if mode.is_system:
        raise DomainError("System settlement mode cannot be deleted.")
    mode.delete()

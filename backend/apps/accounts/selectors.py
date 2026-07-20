from .models import UserCompanySetting, License


def user_setting(user):
    return UserCompanySetting.objects.filter(user=user).select_related("default_company").first()


def user_license(user):
    return License.objects.filter(user=user).first()


def default_company(user):
    s = user_setting(user)
    return s.default_company if s else None


def is_multi_mode(user):
    s = user_setting(user)
    return bool(s and s.active_mode == UserCompanySetting.MULTI)

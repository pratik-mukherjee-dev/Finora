from .models import Ledger


def ledger_for(user, company_id=None, kind=None):
    """Ledgers visible to company: it's own + shared (company is null). """
    qs = Ledger.objects.filter(user=user)
    if company_id:
        qs = qs.filter(company_id=company_id)
    if kind:
        qs = qs.filter(kind=kind)
    return qs


def models_q_company(company_id):
    from django.db.models import Q
    return Q(company_id=company_id) | Q(company__isnull=True)



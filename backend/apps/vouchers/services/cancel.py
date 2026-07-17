from django.db import transaction

from apps.common.exceptions import DomainError
from apps.stock.services import reverse_voucher_movements
from apps.parties.services import reverse_entries
from ..models import SaleMaster, SaleDerived, Purchase, Received, Payment
from .reconciliation import reverse_allocations
from .charges import cancel_charges


@transaction.atomic
def cancel_sale(user, master_id):
    master = SaleMaster.all_objects.select_for_update().get(pk=master_id)
    if master.is_cancelled:
        raise DomainError("Sale already cancelled.")
    fy, date = master.financial_year, master.date
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    for derived in SaleDerived.all_objects.filter(master=master, is_cancelled=False):
        reverse_voucher_movements("SALE", derived.id, date, fy)
        cancel_charges("SALE_DERIVED", derived.id, user)
        derived.soft_cancel(user)
    reverse_entries("SALE", master.id, date, fy)
    cancel_charges("SALE", master.id, user=user)
    master.soft_cancel(user)
    return master


@transaction.atomic
def cancel_purchase(user, purchase_id):
    p = Purchase.all_objects.select_for_update().get(pk=purchase_id)
    if p.is_cancelled:
        raise DomainError("Purchase already cancelled.")
    fy, date = p.financial_year, p.date
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    reverse_voucher_movements("PURCHASE", p.id, date, fy)
    reverse_entries("PURCHASE", p.id, date, fy)
    cancel_charges("PURCHASE", p.id, user=user)
    p.soft_cancel(user)
    return p


@transaction.atomic
def cancel_received(user, received_id):
    r = Received.all_objects.select_for_update().get(pk=received_id)
    if r.is_cancelled:
        raise DomainError("Receipt already cancelled.")
    fy, date = r.financial_year, r.date
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    reverse_allocations("RECEIVED", r.id)
    reverse_entries("RECEIVED", r.id, date, fy)
    r.soft_cancel(user)
    return r


@transaction.atomic
def cancel_payment(user, payment_id):
    p = Payment.all_objects.select_for_update().get(pk=payment_id)
    if p.is_cancelled:
        raise DomainError("Payment already cancelled.")
    fy, date = p.financial_year, p.date
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    reverse_allocations("PAYMENT", p.id)
    reverse_entries("PAYMENT", p.id, date, fy)
    p.soft_cancel(user)
    return p

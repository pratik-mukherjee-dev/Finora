from django.db import transaction
from decimal import Decimal

from apps.common.exceptions import DomainError
from apps.catalogue.models import ItemCompanyMapping
from .models import StockLedger, StockConversion


@transaction.atomic
def post_movement(mapping_id, date, fy, qty_in=Decimal("0.000"),
                  qty_out=Decimal("0.000"), voucher_type="", voucher_id=None,
                  is_manual=False, is_reversal=False, is_opening=False):
    mapping = ItemCompanyMapping.objects.select_for_update().get(pk=mapping_id)
    new_balance = mapping.stock + qty_in - qty_out
    entry = StockLedger.objects.create(
        mapping=mapping, date=date, financial_year=fy,
        qty_in=qty_in, qty_out=qty_out, balance=new_balance,
        voucher_type=voucher_type, voucher_id=voucher_id,
        is_manual=is_manual, is_reversal=is_reversal, is_opening=is_opening,
    )
    mapping.stock = new_balance
    mapping.save(update_fields=["stock"])
    return entry


@transaction.atomic
def manual_adjust(mapping_id, date, fy, new_stock):
    mapping = ItemCompanyMapping.objects.select_for_update().get(pk=mapping_id)
    delta = Decimal(new_stock) - mapping.stock
    if delta == 0:
        return None
    return post_movement(
        mapping_id, date, fy,
        qty_in=delta if delta > 0 else Decimal("0.000"),
        qty_out=-delta if delta < 0 else Decimal("0.000"),
        voucher_type="ADJUST", is_manual=True,
    )


@transaction.atomic
def reverse_voucher_movements(voucher_type, voucher_id, date, fy):
    moves = StockLedger.objects.select_for_update().filter(
        voucher_type=voucher_type, voucher_id=voucher_id, is_reversal=False
    )
    for m in moves:
        post_movement(
            m.mapping_id, date, fy,
            qty_in=m.qty_out, qty_out=m.qty_in,
            voucher_type=voucher_type, voucher_id=voucher_id, is_reversal=True,
        )


@transaction.atomic
def convert(user, date, fy, source_mapping, source_qty, target_item,
            target_qty, target_company=None):
    target_company = target_company or source_mapping.company
    target_mapping, _ = ItemCompanyMapping.objects.get_or_create(
        item=target_item, company=target_company,
        defaults={"rate": Decimal("0.00")},
    )
    conv = StockConversion.objects.create(
        user=user, date=date, financial_year=fy,
        source_mapping=source_mapping, target_mapping=target_mapping,
        source_qty=source_qty, target_qty=target_qty,
    )
    post_movement(source_mapping.id, date, fy, qty_out=source_qty,
                  voucher_type="CONVERT", voucher_id=conv.id)
    post_movement(target_mapping.id, date, fy, qty_in=target_qty,
                  voucher_type="CONVERT", voucher_id=conv.id)
    return conv


@transaction.atomic
def cancel_conversion(conv_id, date, fy):
    conv = StockConversion.objects.select_for_update().get(pk=conv_id)
    if conv.is_cancelled:
        raise DomainError("Conversion already cancelled.")
    reverse_voucher_movements("CONVERT", conv.id, date, fy)
    conv.is_cancelled = True
    conv.save(update_fields=["is_cancelled"])
    return conv


@transaction.atomic
def carry_forward_stock(from_fy, to_fy):
    mappings = ItemCompanyMapping.objects.select_for_update().filter(
        company__user=from_fy.user
    )
    for mapping in mappings:
        closing = mapping.stock
        mapping.opening_stock = closing
        mapping.save(update_fields=["opening_stock"])
        StockLedger.objects.create(
            mapping=mapping, date=to_fy.start_date, financial_year=to_fy,
            qty_in=closing, qty_out=Decimal("0.000"), balance=closing,
            voucher_type="OPENING", is_opening=True,
        )

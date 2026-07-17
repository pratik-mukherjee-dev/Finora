from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP, getcontext
from apps.ledgers.models import Ledger
from ..models import VoucherCharge



# Fixed display / calculation order for the totals section.
CHARGE_ORDER = {
    VoucherCharge.DISCOUNT: 10,
    VoucherCharge.CGST: 20,
    VoucherCharge.SGST: 21,
    VoucherCharge.ROUND_OFF: 90,
}


def tally_default_round(value, precision=0.01):
    getcontext().prec = 12
    value = Decimal(str(value))
    step = Decimal(str(precision))
    rounded_value = (value / step).quantize(
        Decimal('1'),
        rounding=ROUND_HALF_UP,
    ) * step
    return rounded_value


def _discount_amount(base, mode, input_value):
    """Returns a NEGATIVE decimal reducing the total"""
    input_value = Decimal(str(input_value))
    if mode == VoucherCharge.PERCENT:
        raw = base * input_value / Decimal("100")
    else:
        raw = input_value
    return -(raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def apply_charges(subtotal, charge_inputs):
    """
    Pure calculator. `charge_inputs` = list of dicts:
        {ledger_id, charge_type, mode, input_value}
    Returns (final_total, resolved_charges) where resolved_charges is a list of
    dicts ready to persist as VoucherCharge rows (amount + sort_order filled in).

    v1 handles DISCOUNT and ROUND_OFF. CGST/SGST slots are accepted but computed
    upstream (item-wise) in v2 and passed in with a precomputed `amount`.
    """
    subtotal = Decimal(str(subtotal))
    running = subtotal
    resolved = []

    # 1. Discount (percent of subtotal, or flat amount)
    for c in charge_inputs:
        if c.get("charge_type") != VoucherCharge.DISCOUNT:
            continue
        amt = _discount_amount(subtotal, c.get("mode", VoucherCharge.PERCENT),
                               c.get("input_value", 0))
        running += amt
        resolved.append({**c, "amount": amt,
                         "sort_order": CHARGE_ORDER[VoucherCharge.DISCOUNT]})

    # 2. CGST / SGST (v2) — amount is precomputed item-wise upstream, just apply.
    for c in charge_inputs:
        if c.get("charge_type") not in (VoucherCharge.CGST, VoucherCharge.SGST):
            continue
        amt = Decimal(str(c.get("amount", "0"))).quantize(Decimal("0.01"))
        running += amt
        resolved.append({**c, "amount": amt,
                         "sort_order": CHARGE_ORDER[c["charge_type"]]})

    # 3. Round-off (Tally): delta between rounded running total and running total
    for c in charge_inputs:
        if c.get("charge_type") != VoucherCharge.ROUND_OFF:
            continue
        rounded = tally_default_round(running)
        amt = (rounded - running).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        running += amt
        resolved.append({**c, "mode": VoucherCharge.AMOUNT,
                         "input_value": Decimal("0.0000"), "amount": amt,
                         "sort_order": CHARGE_ORDER[VoucherCharge.ROUND_OFF]})

    return running, resolved


def persist_charges(voucher_type, voucher_id, resolved_charges):
    """Write resolved charge dicts as VoucherCharge rows."""
    objs = [
        VoucherCharge(
            voucher_type=voucher_type,
            voucher_id=voucher_id,
            ledger_id=c["ledger_id"],
            charge_type=c["charge_type"],
            mode=c.get("mode", VoucherCharge.PERCENT),
            input_value=c.get("input_value", 0),
            amount=c["amount"],
            sort_order=c.get("sort_order", 0),
        )
        for c in resolved_charges
    ]
    VoucherCharge.objects.bulk_create(objs)
    return objs


def cancel_charges(voucher_type, voucher_id, user=None):
    """Soft-cancel all live charges on a cancelled voucher (audit-preserving)."""
    VoucherCharge.objects.filter(
        voucher_type=voucher_type, voucher_id=voucher_id
    ).update(is_cancelled=True, cancelled_at=timezone.now(), cancelled_by=user)


def prorate_master_charges(master_id, groups_value):
    """
    Split a master's persisted DISCOUNT/tax charges across derived companies by
    line-value weight, and compute a per-company round-off.

    `groups_value` = {company_id: pre_charge_subtotal_for_that_company}.
    Returns {company_id: [resolved_charge_dict, ...]} ready for persist_charges
    against voucher_type="SALE_DERIVED".
    """
    master_charges = list(
        VoucherCharge.objects.filter(voucher_type="SALE", voucher_id=master_id)
    )
    subtotal = sum(groups_value.values(), Decimal("0.00"))
    company_ids = list(groups_value.keys())
    result = {cid: [] for cid in company_ids}
    if subtotal <= 0 or not company_ids:
        return result

    # 1. Prorate every non-round-off charge (discount now, CGST/SGST later)
    for ch in master_charges:
        if ch.charge_type == VoucherCharge.ROUND_OFF:
            continue
        allocated = Decimal("0.00")
        for i, cid in enumerate(company_ids):
            if i < len(company_ids) - 1:
                share = (ch.amount * groups_value[cid] / subtotal).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                allocated += share
            else:
                share = ch.amount - allocated  # remainder to last company
            result[cid].append({
                "ledger_id": ch.ledger_id,
                "charge_type": ch.charge_type,
                "mode": ch.mode,
                "input_value": ch.input_value,
                "amount": share,
                "sort_order": ch.sort_order,
            })

    # 2. Per-company round-off on each company's (value + its charges) total
    round_ledger = next(
        (c.ledger_id for c in master_charges
         if c.charge_type == VoucherCharge.ROUND_OFF), None
    )
    if round_ledger is not None:
        for cid in company_ids:
            base = groups_value[cid] + sum(
                (c["amount"] for c in result[cid]), Decimal("0.00")
            )
            delta = (tally_default_round(base) - base).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if delta != 0:
                result[cid].append({
                    "ledger_id": round_ledger,
                    "charge_type": VoucherCharge.ROUND_OFF,
                    "mode": VoucherCharge.AMOUNT,
                    "input_value": Decimal("0.0000"),
                    "amount": delta,
                    "sort_order": CHARGE_ORDER[VoucherCharge.ROUND_OFF],
                })
    return result

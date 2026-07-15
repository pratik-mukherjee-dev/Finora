from django.db import transaction
from decimal import Decimal

from apps.common.exceptions import DomainError
from .models import Item, ItemCategory, ItemCompanyMapping


def _norm_unit(unit):
    """Canonicalise a base unit so 'BAG', 'Bag' and 'bag' are the same value."""
    return (unit or "pcs").strip().upper() or "PCS"


@transaction.atomic
def create_item(user, name, company=None, base_unit="pcs", rate=Decimal("0.00"),
                category=None, opening_stock=Decimal("0.000")):
    item, _ = Item.objects.get_or_create(
        user=user, name=name.strip(), defaults={"base_unit": _norm_unit(base_unit)}
    )
    if company:
        ItemCompanyMapping.objects.get_or_create(
            item=item,
            company=company,
            defaults={
                "rate": rate,
                "category": category,
                "opening_stock": opening_stock,
                "stock": opening_stock,
            },
        )
    return item


@transaction.atomic
def add_mapping(item, company, rate=Decimal("0.00"), category=None,
                opening_stock=Decimal("0.000")):
    if item.user_id != company.user_id:
        raise DomainError("Item and company belong to different users.")
    mapping, created = ItemCompanyMapping.objects.get_or_create(
        item=item,
        company=company,
        defaults={
            "rate": rate,
            "category": category,
            "opening_stock": opening_stock,
            "stock": opening_stock,
        },
    )
    return mapping


@transaction.atomic
def update_rate(mapping_id, rate):
    updated = ItemCompanyMapping.objects.filter(pk=mapping_id).update(rate=rate)
    if not updated:
        raise DomainError("Item mapping not found.")


@transaction.atomic
def create_category(company, name):
    return ItemCategory.objects.create(company=company, name=name.strip())

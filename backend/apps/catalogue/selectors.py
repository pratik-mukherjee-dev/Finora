from .models import Item, ItemCompanyMapping, ItemCategory


def mappings_for_item(item):
    return ItemCompanyMapping.objects.filter(item=item).select_related("company", "category")


def resolve_mapping(item, company_id):
    return (
        ItemCompanyMapping.objects.select_related("company", "category")
        .filter(item=item, company_id=company_id)
        .first()
    )


def item_company_ids(item):
    return list(
        ItemCompanyMapping.objects.filter(item=item).values_list("company_id", flat=True)
    )


def categories_for_company(company_id):
    return ItemCategory.objects.filter(company_id=company_id)

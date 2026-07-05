import django_filters as df
from .models import ItemCompanyMapping, ItemCategory


class MappingFilter(df.FilterSet):
    class Meta:
        model = ItemCompanyMapping
        fields = ["company", "category", "item"]


class CategoryFilter(df.FilterSet):
    class Meta:
        model = ItemCategory
        fields = ["company"]

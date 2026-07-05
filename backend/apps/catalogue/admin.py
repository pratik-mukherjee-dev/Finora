from django.contrib import admin
from .models import Item, ItemCategory, ItemCompanyMapping

admin.site.register(Item)
admin.site.register(ItemCategory)
admin.site.register(ItemCompanyMapping)

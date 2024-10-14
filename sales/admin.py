from django.contrib import admin
from .models import Order, OrderProduct


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['client', 'vat', 'is_confirmed', 'confirmed_at', 'is_rejected', 'rejected_at', 'created_at']
    list_filter = ['client', 'is_confirmed', 'is_rejected']
    search_fields = ['client', ]


@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = ['order', 'name', 'quantity', 'price', 'created_at']
    list_filter = ['order', ]
    search_fields = ['order', 'name']
    autocomplete_fields = ['order']

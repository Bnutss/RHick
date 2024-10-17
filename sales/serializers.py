from rest_framework import serializers
from .models import Order, OrderProduct
from datetime import timedelta
from django.utils import timezone


class OrderSerializer(serializers.ModelSerializer):
    warranty_days_left = serializers.SerializerMethodField()
    confirmed_at = serializers.DateTimeField(format="%Y-%m-%d", required=False)
    total_price_without_vat = serializers.SerializerMethodField()
    total_price_with_vat = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'client', 'vat', 'created_at', 'is_confirmed', 'is_rejected', 'confirmed_at',
                  'warranty_days_left',
                  'total_price_without_vat', 'total_price_with_vat']

    # Метод для расчета оставшихся дней гарантии
    def get_warranty_days_left(self, obj):
        if obj.is_confirmed and obj.confirmed_at:
            warranty_end_date = obj.confirmed_at + timedelta(days=365)
            remaining_days = (warranty_end_date - timezone.now()).days
            return max(remaining_days, 0)
        return None

    # Метод для расчета общей суммы без НДС
    def get_total_price_without_vat(self, obj):
        total_price = sum([product.quantity * product.price for product in obj.products.all()])
        return total_price

    # Метод для расчета общей суммы с НДС
    def get_total_price_with_vat(self, obj):
        total_price_without_vat = self.get_total_price_without_vat(obj)
        total_price_with_vat = total_price_without_vat + (total_price_without_vat * (obj.vat / 100))
        return total_price_with_vat

    # Валидация
    def validate(self, data):
        if data.get('is_confirmed') and data.get('is_rejected'):
            raise serializers.ValidationError("Заказ не может быть одновременно подтвержденным и отклоненным.")
        return data


class OrderProductSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderProduct
        fields = ['id', 'name', 'quantity', 'price', 'total_price', 'order', 'photo']

    def get_total_price(self, obj):
        return obj.quantity * obj.price


class OrderDetailSerializer(serializers.ModelSerializer):
    products = OrderProductSerializer(many=True, read_only=True)
    total_price_without_vat = serializers.SerializerMethodField()
    total_price_with_vat = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'client', 'vat', 'products', 'total_price_without_vat', 'total_price_with_vat']

    # Метод для расчета общей суммы без НДС
    def get_total_price_without_vat(self, obj):
        total_price = sum([product.quantity * product.price for product in obj.products.all()])
        return total_price

    # Метод для расчета общей суммы с НДС
    def get_total_price_with_vat(self, obj):
        total_price_without_vat = self.get_total_price_without_vat(obj)
        total_price_with_vat = total_price_without_vat + (total_price_without_vat * (obj.vat / 100))
        return total_price_with_vat

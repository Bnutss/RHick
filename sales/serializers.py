from rest_framework import serializers
from .models import Order, OrderProduct, Password
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal


class OrderSerializer(serializers.ModelSerializer):
    warranty_days_left = serializers.SerializerMethodField()
    confirmed_at = serializers.DateTimeField(format="%Y-%m-%d", required=False)
    total_price_without_vat = serializers.SerializerMethodField()
    total_price_with_vat = serializers.SerializerMethodField()
    vat_amount = serializers.SerializerMethodField()
    additional_expenses_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'client', 'vat', 'additional_expenses', 'created_at', 'is_confirmed', 'is_rejected',
                  'confirmed_at', 'warranty_days_left', 'total_price_without_vat', 'total_price_with_vat', 'vat_amount',
                  'additional_expenses_amount']

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

    # Метод для расчета суммы НДС
    def get_vat_amount(self, obj):
        total_price_without_vat = self.get_total_price_without_vat(obj)
        vat = obj.vat or Decimal(0)
        vat_amount = total_price_without_vat * (vat / Decimal(100))
        return vat_amount

    # Метод для расчета суммы прочих расходов
    def get_additional_expenses_amount(self, obj):
        total_price_without_vat = self.get_total_price_without_vat(obj)
        additional_expenses = obj.additional_expenses or Decimal(0)
        additional_expenses_amount = total_price_without_vat * (additional_expenses / Decimal(100))
        return additional_expenses_amount

    # Метод для расчета общей суммы с НДС и прочими расходами
    def get_total_price_with_vat(self, obj):
        total_price_without_vat = self.get_total_price_without_vat(obj)
        vat_amount = self.get_vat_amount(obj)
        additional_expenses_amount = self.get_additional_expenses_amount(obj)
        total_price_with_vat = total_price_without_vat + vat_amount + additional_expenses_amount
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
    additional_expenses_amount = serializers.SerializerMethodField()
    total_general_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'client', 'vat', 'additional_expenses', 'products', 'total_price_without_vat',
                  'total_price_with_vat', 'additional_expenses_amount', 'total_general_amount']

    # Метод для расчета общей суммы без НДС
    def get_total_price_without_vat(self, obj):
        return sum(product.quantity * product.price for product in obj.products.all())

    # Метод для расчета суммы дополнительных расходов
    def get_additional_expenses_amount(self, obj):
        total_price_without_vat = self.get_total_price_without_vat(obj)
        additional_expenses = obj.additional_expenses or Decimal(0)
        return total_price_without_vat * (additional_expenses / Decimal(100))

    # Метод для расчета общей суммы с НДС
    def get_total_price_with_vat(self, obj):
        total_price_without_vat = self.get_total_price_without_vat(obj)
        vat = obj.vat or Decimal(0)
        return total_price_without_vat + (total_price_without_vat * (vat / Decimal(100)))

    # Метод для расчета общей итоговой суммы
    def get_total_general_amount(self, obj):
        total_price_without_vat = self.get_total_price_without_vat(obj)
        additional_expenses_amount = self.get_additional_expenses_amount(obj)
        total_price_with_vat = self.get_total_price_with_vat(obj)
        return total_price_with_vat + additional_expenses_amount


class PasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Password
        fields = '__all__'

from django.db import models
from django.utils import timezone


class Order(models.Model):
    client = models.CharField(max_length=100, verbose_name='Название клиента')
    vat = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='НДС (%)', blank=True, null=True)
    additional_expenses = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Прочие расходы (%)',
                                              blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_confirmed = models.BooleanField(default=False, verbose_name="Подтвержденный заказ")
    is_rejected = models.BooleanField(default=False, verbose_name="Отклоненный заказ")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата подтверждения")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отклонения")

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f"Заказ {self.id} от {self.client}"

    def get_total_price(self):
        """
        Вычисляем общую стоимость всех товаров в заказе без НДС.
        """
        total_price = sum([product.quantity * product.price for product in self.products.all()])
        return total_price

    def get_total_price_with_vat(self):
        """
        Вычисляем общую стоимость заказа только с учетом НДС.
        """
        total_price = self.get_total_price()
        vat_multiplier = 1 + (self.vat / 100 if self.vat else 0)  # Учет НДС
        return total_price * vat_multiplier

    def get_additional_expenses_amount(self):
        """
        Вычисляем сумму прочих расходов в абсолютном значении на основе общей стоимости заказа без НДС.
        """
        total_price = self.get_total_price()
        if self.additional_expenses:
            return total_price * (self.additional_expenses / 100)
        return 0

    def save(self, *args, **kwargs):
        if self.is_confirmed and self.confirmed_at is None:
            self.confirmed_at = timezone.now()

        if self.is_rejected and self.rejected_at is None:
            self.rejected_at = timezone.now()

        if self.is_confirmed and self.is_rejected:
            raise ValueError("Заказ не может быть одновременно подтвержденным и отклоненным.")

        super(Order, self).save(*args, **kwargs)


class OrderProduct(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='products', verbose_name="Заказ")
    name = models.CharField(max_length=255, verbose_name="Название")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    photo = models.ImageField(upload_to='order_product_photos/', null=True, blank=True, verbose_name="Фото")

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return f'{self.name} - {self.order}'

    def save(self, *args, **kwargs):
        if self.pk and self.photo:
            old_photo = OrderProduct.objects.get(pk=self.pk).photo
            if old_photo and old_photo != self.photo:
                old_photo.delete(save=False)

        super().save(*args, **kwargs)


class Password(models.Model):
    organization_name = models.CharField(max_length=255, verbose_name="Название организации")
    nvr_password = models.CharField(max_length=255, verbose_name="Пароль от NVR")
    camera_password = models.CharField(max_length=255, verbose_name="Пароль от камеры")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.organization_name

    class Meta:
        verbose_name = "Пароль"
        verbose_name_plural = "Пароли"

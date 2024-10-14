from django.db import models
from django.utils import timezone


class Order(models.Model):
    client = models.CharField(max_length=100, verbose_name='Название клиента')
    vat = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='НДС (%)')
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

    def save(self, *args, **kwargs):
        if self.is_confirmed and self.confirmed_at is None:
            self.confirmed_at = timezone.now()

        if self.is_rejected and self.rejected_at is None:
            self.rejected_at = timezone.now()

        if self.is_confirmed and self.is_rejected:
            raise ValueError("Заказ не может быть одновременно подтвержденным и отклоненным.")

        super(Order, self).save(*args, **kwargs)


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='products', verbose_name="Заказ")
    name = models.CharField(max_length=255, verbose_name="Название")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return f'{self.name} - {self.order}'

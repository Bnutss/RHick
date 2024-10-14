from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    mobile_app = models.BooleanField(default=False, verbose_name='Мобильное приложение')
    id_telegram = models.CharField(max_length=50, null=True, blank=True, verbose_name="Телеграмм ID")

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return self.user.username

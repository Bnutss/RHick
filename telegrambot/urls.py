from django.urls import path
from . import views

app_name = 'telegrambot'

urlpatterns = [
    path('webhook/', views.telegram_webhook, name='telegram_webhook'),
]

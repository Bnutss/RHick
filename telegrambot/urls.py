from django.urls import path
from . import simple_views

urlpatterns = [
    path('webhook/', simple_views.telegram_webhook, name='telegram_webhook'),
]

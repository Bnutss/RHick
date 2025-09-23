from django.core.management.base import BaseCommand
from django.conf import settings
import requests


class Command(BaseCommand):
    help = 'Проверить статус webhook'

    def handle(self, *args, **options):
        response = requests.get(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        )

        data = response.json()
        if data.get('ok'):
            info = data['result']
            self.stdout.write(f"URL: {info.get('url', 'Не установлен')}")
            self.stdout.write(f"Ошибки: {info.get('last_error_message', 'Нет')}")
            self.stdout.write(f"Последнее обновление: {info.get('last_update', 'Нет')}")
        else:
            self.stdout.write(self.style.ERROR(f"Ошибка: {response.text}"))

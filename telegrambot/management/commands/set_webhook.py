from django.core.management.base import BaseCommand
from django.conf import settings
import requests


class Command(BaseCommand):
    help = 'Установить webhook для Telegram бота'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, help='URL для webhook')

    def handle(self, *args, **options):
        webhook_url = options.get('url') or f"https://rhik.pythonanywhere.com/telegram/webhook/"

        response = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook",
            data={'url': webhook_url}
        )

        if response.json().get('ok'):
            self.stdout.write(
                self.style.SUCCESS(f'✅ Webhook установлен: {webhook_url}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка: {response.text}')
            )

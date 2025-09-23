from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserProfile


class Command(BaseCommand):
    help = 'Настройка Telegram пользователя'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username пользователя')
        parser.add_argument('--telegram_id', type=str, help='Telegram ID пользователя')

    def handle(self, *args, **options):
        username = options['username']
        telegram_id = options['telegram_id']

        if not username or not telegram_id:
            self.stdout.write(self.style.ERROR('Укажите --username и --telegram_id'))
            return

        # Создаем или получаем пользователя
        user, created = User.objects.get_or_create(username=username)
        if created:
            self.stdout.write(f'Создан пользователь: {username}')

        # Создаем или обновляем профиль
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'id_telegram': telegram_id}
        )

        if not created:
            profile.id_telegram = telegram_id
            profile.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Пользователь {username} настроен для Telegram ID: {telegram_id}'
            )
        )

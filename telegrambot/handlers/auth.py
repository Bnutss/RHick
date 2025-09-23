from asgiref.sync import sync_to_async
from users.models import UserProfile


class AuthHandler:
    @sync_to_async
    def get_user_profile(self, telegram_id):
        try:
            return UserProfile.objects.get(id_telegram=telegram_id)
        except UserProfile.DoesNotExist:
            return None

    async def is_authorized_user(self, update) -> bool:
        user_id = str(update.effective_user.id)
        profile = await self.get_user_profile(user_id)

        if profile:
            return True
        else:
            message_obj = update.message or update.callback_query.message
            await message_obj.reply_text(
                f"❌ У вас нет доступа к этому боту\n"
                f"🆔 Ваш Telegram ID: `{user_id}`\n"
                f"👨‍💼 Обратитесь к администратору для получения доступа",
                parse_mode='Markdown'
            )
            return False

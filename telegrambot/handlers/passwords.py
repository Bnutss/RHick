from asgiref.sync import sync_to_async
from sales.models import Password
from .auth import AuthHandler


class PasswordHandler(AuthHandler):
    @sync_to_async
    def get_passwords(self):
        return list(Password.objects.all().order_by('-created_at'))

    @sync_to_async
    def create_password_sync(self, org_name, nvr_pass, camera_pass):
        return Password.objects.create(
            organization_name=org_name,
            nvr_password=nvr_pass,
            camera_password=camera_pass
        )

    async def show_passwords(self, update, context):
        if not await self.is_authorized_user(update):
            return

        passwords = await self.get_passwords()

        if not passwords:
            message_obj = update.message or update.callback_query.message
            await message_obj.reply_text("🔑 Паролей пока нет")
            return

        message = "🔑 **Пароли организаций:**\n\n"
        for i, pwd in enumerate(passwords, 1):
            message += f"🏢 **{i}. {pwd.organization_name}**\n"
            message += f"📹 **NVR:** `{pwd.nvr_password}`\n"
            message += f"📷 **Камера:** `{pwd.camera_password}`\n"
            message += f"📅 **Обновлено:** {pwd.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
            message += "─────────────\n"

        if update.message:
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.callback_query.message.reply_text(message, parse_mode='Markdown')

    async def handle_password_creation(self, update, context):
        text = update.message.text
        step = context.user_data.get('password_step')

        if step == 'organization':
            context.user_data['password_org'] = text
            context.user_data['password_step'] = 'nvr'
            await update.message.reply_text(
                f"📝 **Шаг 2/3:** Введите пароль для NVR\n"
                f"🏢 **Организация:** {text}",
                parse_mode='Markdown'
            )

        elif step == 'nvr':
            context.user_data['password_nvr'] = text
            context.user_data['password_step'] = 'camera'
            await update.message.reply_text(
                "📝 **Шаг 3/3:** Введите пароль для камеры",
                parse_mode='Markdown'
            )

        elif step == 'camera':
            password = await self.create_password_sync(
                context.user_data['password_org'],
                context.user_data['password_nvr'],
                text
            )

            context.user_data.clear()

            await update.message.reply_text(
                f"✅ **Пароль для '{password.organization_name}' добавлен!**\n\n"
                f"🏢 **Организация:** {password.organization_name}\n"
                f"📹 **Пароль NVR:** `{password.nvr_password}`\n"
                f"📷 **Пароль камеры:** `{password.camera_password}`\n"
                f"📅 **Создан:** {password.created_at.strftime('%d.%m.%Y %H:%M')}",
                parse_mode='Markdown'
            )

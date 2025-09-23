from django.core.management.base import BaseCommand
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from django.conf import settings
from telegrambot.handlers.orders import OrderHandler
from telegrambot.handlers.products import ProductHandler
from telegrambot.handlers.passwords import PasswordHandler
from telegrambot.handlers.callbacks import CallbackHandler
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def __init__(self):
        super().__init__()
        self.order_handler = OrderHandler()
        self.product_handler = ProductHandler()
        self.password_handler = PasswordHandler()
        self.callback_handler = CallbackHandler()

    def handle(self, *args, **options):
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("orders", self.order_handler.show_orders))
        application.add_handler(CommandHandler("passwords", self.password_handler.show_passwords))
        application.add_handler(CommandHandler("create_order", self.create_order))
        application.add_handler(CommandHandler("add_password", self.add_password))
        application.add_handler(CallbackQueryHandler(self.callback_handler.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, self.product_handler.handle_photo))

        self.stdout.write(self.style.SUCCESS('🤖 Telegram бот запущен!'))
        application.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.order_handler.is_authorized_user(update):
            return

        keyboard = [
            [KeyboardButton("📋 Заказы"), KeyboardButton("🔑 Пароли")],
            [KeyboardButton("➕ Создать заказ"), KeyboardButton("🔒 Добавить пароль")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("❌ Отмена")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"🎉 **Добро пожаловать, {update.effective_user.first_name}!**\n\n"
            f"🤖 **Система управления заказами**\n\n"
            f"✨ **Доступные функции:**\n"
            f"📋 Просмотр и управление заказами\n"
            f"🔑 Управление паролями\n"
            f"➕ Создание новых заказов\n"
            f"📦 Добавление товаров с фото\n"
            f"📄 Генерация PDF документов\n"
            f"📊 Просмотр статистики\n\n"
            f"🚀 **Выберите действие из меню ниже:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def create_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.order_handler.is_authorized_user(update):
            return

        context.user_data['creating_order'] = True
        context.user_data['order_step'] = 'client'

        await update.message.reply_text(
            "➕ **Создание нового заказа**\n\n"
            "📝 **Шаг 1/3:** Введите название клиента\n"
            "💡 Например: ООО \"Рога и Копыта\"",
            parse_mode='Markdown'
        )

    async def add_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.password_handler.is_authorized_user(update):
            return

        context.user_data['adding_password'] = True
        context.user_data['password_step'] = 'organization'

        await update.message.reply_text(
            "🔒 **Добавление пароля**\n\n"
            "📝 **Шаг 1/3:** Введите название организации\n"
            "💡 Например: Офис на Чиланзаре",
            parse_mode='Markdown'
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.order_handler.is_authorized_user(update):
            return

        text = update.message.text

        if text == "📋 Заказы":
            await self.order_handler.show_orders(update, context)
        elif text == "🔑 Пароли":
            await self.password_handler.show_passwords(update, context)
        elif text == "➕ Создать заказ":
            await self.create_order(update, context)
        elif text == "🔒 Добавить пароль":
            await self.add_password(update, context)
        elif text == "📊 Статистика":
            await self.show_statistics(update, context)
        elif text == "❌ Отмена":
            context.user_data.clear()
            await update.message.reply_text("❌ **Операция отменена**", parse_mode='Markdown')
        elif context.user_data.get('creating_order'):
            await self.order_handler.handle_order_creation(update, context)
        elif context.user_data.get('adding_password'):
            await self.password_handler.handle_password_creation(update, context)
        elif context.user_data.get('adding_product'):
            await self.product_handler.handle_product_creation(update, context)
        elif context.user_data.get('editing_order'):
            await self.order_handler.handle_order_editing(update, context)
        else:
            await update.message.reply_text(
                "❓ **Команда не распознана**\n\n"
                "🎯 **Используйте кнопки меню или команды:**\n"
                "🏠 /start - главное меню\n"
                "📋 /orders - список заказов\n"
                "🔑 /passwords - список паролей",
                parse_mode='Markdown'
            )

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = await self.order_handler.get_statistics()

        await update.message.reply_text(
            f"📊 **Статистика системы:**\n\n"
            f"📋 **Заказы:**\n"
            f"🔢 Всего: **{stats['total_orders']}**\n"
            f"✅ Подтвержденных: **{stats['confirmed_orders']}**\n"
            f"❌ Отклоненных: **{stats['rejected_orders']}**\n"
            f"⏳ В ожидании: **{stats['pending_orders']}**\n\n"
            f"📦 **Товары:** **{stats['total_products']}**\n"
            f"🔑 **Пароли:** **{stats['passwords_count']}**",
            parse_mode='Markdown'
        )

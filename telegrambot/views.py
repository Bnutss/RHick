import json
import logging
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from telegram import Update
from telegram.ext import Application
import asyncio

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def telegram_webhook(request):
    try:
        json_str = request.body.decode('UTF-8')
        update_data = json.loads(json_str)

        # Создаем Update объект
        update = Update.de_json(update_data, None)

        # Обрабатываем update асинхронно
        asyncio.create_task(process_telegram_update(update))

        return HttpResponse("OK")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return HttpResponse("OK")  # Всегда возвращаем OK для Telegram


async def process_telegram_update(update):
    """Асинхронная обработка обновлений от Telegram"""
    try:
        from .handlers.orders import OrderHandler
        from .handlers.passwords import PasswordHandler
        from .handlers.products import ProductHandler
        from .handlers.callbacks import CallbackHandler

        # Создаем handlers
        order_handler = OrderHandler()
        password_handler = PasswordHandler()
        product_handler = ProductHandler()
        callback_handler = CallbackHandler()

        # Создаем временный контекст
        class Context:
            def __init__(self):
                self.user_data = {}
                self.bot = None

        context = Context()

        # Обрабатываем разные типы обновлений
        if update.message:
            if update.message.text:
                if update.message.text.startswith('/'):
                    await handle_command(update, context)
                else:
                    await handle_text_message(update, context)
            elif update.message.photo:
                await product_handler.handle_photo(update, context)

        elif update.callback_query:
            await callback_handler.handle_callback(update, context)

    except Exception as e:
        logger.error(f"Error processing update: {e}")


async def handle_command(update, context):
    """Обработка команд"""
    from .handlers.orders import OrderHandler
    from .handlers.passwords import PasswordHandler

    command = update.message.text
    order_handler = OrderHandler()
    password_handler = PasswordHandler()

    if command == '/start':
        await start_command(update, context)
    elif command == '/orders':
        await order_handler.show_orders(update, context)
    elif command == '/passwords':
        await password_handler.show_passwords(update, context)
    elif command == '/create_order':
        await create_order(update, context)
    elif command == '/add_password':
        await add_password(update, context)


async def handle_text_message(update, context):
    """Обработка текстовых сообщений"""
    from .handlers.orders import OrderHandler
    from .handlers.passwords import PasswordHandler
    from .handlers.products import ProductHandler

    text = update.message.text
    order_handler = OrderHandler()
    password_handler = PasswordHandler()
    product_handler = ProductHandler()

    if not await order_handler.is_authorized_user(update):
        return

    if text == "📋 Заказы":
        await order_handler.show_orders(update, context)
    elif text == "🔑 Пароли":
        await password_handler.show_passwords(update, context)
    elif text == "➕ Создать заказ":
        await create_order(update, context)
    elif text == "🔐 Добавить пароль":
        await add_password(update, context)
    elif text == "📊 Статистика":
        await show_statistics(update, context)
    elif text == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text("❌ **Операция отменена**", parse_mode='Markdown')
    elif context.user_data.get('creating_order'):
        await order_handler.handle_order_creation(update, context)
    elif context.user_data.get('adding_password'):
        await password_handler.handle_password_creation(update, context)
    elif context.user_data.get('adding_product'):
        await product_handler.handle_product_creation(update, context)
    elif context.user_data.get('editing_order'):
        await order_handler.handle_order_editing(update, context)


async def start_command(update, context):
    from telegram import ReplyKeyboardMarkup, KeyboardButton
    from .handlers.orders import OrderHandler

    order_handler = OrderHandler()
    if not await order_handler.is_authorized_user(update):
        return

    keyboard = [
        [KeyboardButton("📋 Заказы"), KeyboardButton("🔑 Пароли")],
        [KeyboardButton("➕ Создать заказ"), KeyboardButton("🔐 Добавить пароль")],
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


async def create_order(update, context):
    from .handlers.orders import OrderHandler
    order_handler = OrderHandler()

    if not await order_handler.is_authorized_user(update):
        return

    context.user_data['creating_order'] = True
    context.user_data['order_step'] = 'client'

    await update.message.reply_text(
        "➕ **Создание нового заказа**\n\n"
        "📝 **Шаг 1/3:** Введите название клиента\n"
        "💡 Например: ООО \"Рога и Копыта\"",
        parse_mode='Markdown'
    )


async def add_password(update, context):
    from .handlers.passwords import PasswordHandler
    password_handler = PasswordHandler()

    if not await password_handler.is_authorized_user(update):
        return

    context.user_data['adding_password'] = True
    context.user_data['password_step'] = 'organization'

    await update.message.reply_text(
        "🔐 **Добавление пароля**\n\n"
        "📝 **Шаг 1/3:** Введите название организации\n"
        "💡 Например: Офис на Чиланзаре",
        parse_mode='Markdown'
    )


async def show_statistics(update, context):
    from .handlers.orders import OrderHandler
    order_handler = OrderHandler()

    stats = await order_handler.get_statistics()

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

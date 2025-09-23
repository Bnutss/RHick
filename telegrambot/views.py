import json
import logging
import asyncio
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

logger = logging.getLogger(__name__)


async def start_command(update, context):
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


async def handle_message(update, context):
    from .handlers.orders import OrderHandler
    from .handlers.passwords import PasswordHandler
    from .handlers.products import ProductHandler

    order_handler = OrderHandler()
    password_handler = PasswordHandler()
    product_handler = ProductHandler()

    if not await order_handler.is_authorized_user(update):
        return

    text = update.message.text

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
    else:
        await update.message.reply_text(
            "❓ **Команда не распознана**\n\n"
            "🎯 **Используйте кнопки меню или команды:**\n"
            "🏠 /start - главное меню\n"
            "📋 /orders - список заказов\n"
            "🔑 /passwords - список паролей",
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


async def handle_photo(update, context):
    from .handlers.products import ProductHandler
    product_handler = ProductHandler()
    await product_handler.handle_photo(update, context)


async def handle_callback(update, context):
    from .handlers.callbacks import CallbackHandler
    callback_handler = CallbackHandler()
    await callback_handler.handle_callback(update, context)


@csrf_exempt
@require_POST
def telegram_webhook(request):
    try:
        json_str = request.body.decode('UTF-8')
        update = Update.de_json(json.loads(json_str), None)

        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(
            CommandHandler("orders", lambda u, c: asyncio.create_task(order_handler_show_orders(u, c))))
        application.add_handler(
            CommandHandler("passwords", lambda u, c: asyncio.create_task(password_handler_show_passwords(u, c))))
        application.add_handler(CommandHandler("create_order", create_order))
        application.add_handler(CommandHandler("add_password", add_password))
        application.add_handler(CallbackQueryHandler(handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

        asyncio.create_task(application.process_update(update))

        return HttpResponse("OK")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return HttpResponseBadRequest("Bad Request")


async def order_handler_show_orders(update, context):
    from .handlers.orders import OrderHandler
    order_handler = OrderHandler()
    await order_handler.show_orders(update, context)


async def password_handler_show_passwords(update, context):
    from .handlers.passwords import PasswordHandler
    password_handler = PasswordHandler()
    await password_handler.show_passwords(update, context)

import logging
from telegram import ReplyKeyboardMarkup, KeyboardButton
from .handlers.orders import OrderHandler
from .handlers.passwords import PasswordHandler
from .handlers.products import ProductHandler
from .handlers.callbacks import CallbackHandler
import asyncio

logger = logging.getLogger(__name__)

user_sessions = {}


def handle_telegram_update(update):
    try:
        user_id = update.effective_user.id

        if user_id not in user_sessions:
            user_sessions[user_id] = {}

        context = type('Context', (), {
            'user_data': user_sessions[user_id],
            'bot': update.get_bot()
        })()

        # Запускаем асинхронную обработку в новом event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process_update_async(update, context))
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error in handle_telegram_update: {e}")


async def process_update_async(update, context):
    try:
        if update.message:
            if update.message.text:
                if update.message.text.startswith('/'):
                    await handle_command(update, context)
                else:
                    await handle_text(update, context)
            elif update.message.photo:
                await handle_photo(update, context)
        elif update.callback_query:
            await handle_callback(update, context)
    except Exception as e:
        logger.error(f"Error in process_update_async: {e}")


async def handle_command(update, context):
    command = update.message.text

    if command == '/start':
        await start_command(update, context)
    elif command == '/orders':
        handler = OrderHandler()
        await handler.show_orders(update, context)
    elif command == '/passwords':
        handler = PasswordHandler()
        await handler.show_passwords(update, context)
    elif command == '/create_order':
        await create_order_command(update, context)
    elif command == '/add_password':
        await add_password_command(update, context)


async def handle_text(update, context):
    text = update.message.text
    order_handler = OrderHandler()

    if not await order_handler.is_authorized_user(update):
        return

    if text == "📋 Заказы":
        await order_handler.show_orders(update, context)
    elif text == "🔑 Пароли":
        password_handler = PasswordHandler()
        await password_handler.show_passwords(update, context)
    elif text == "➕ Создать заказ":
        await create_order_command(update, context)
    elif text == "🔐 Добавить пароль":
        await add_password_command(update, context)
    elif text == "📊 Статистика":
        await show_statistics(update, context)
    elif text == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text("❌ **Операция отменена**", parse_mode='Markdown')
    elif context.user_data.get('creating_order'):
        await order_handler.handle_order_creation(update, context)
    elif context.user_data.get('adding_password'):
        password_handler = PasswordHandler()
        await password_handler.handle_password_creation(update, context)
    elif context.user_data.get('adding_product'):
        product_handler = ProductHandler()
        await product_handler.handle_product_creation(update, context)
    elif context.user_data.get('editing_order'):
        await order_handler.handle_order_editing(update, context)


async def handle_photo(update, context):
    product_handler = ProductHandler()
    await product_handler.handle_photo(update, context)


async def handle_callback(update, context):
    callback_handler = CallbackHandler()
    await callback_handler.handle_callback(update, context)


async def start_command(update, context):
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


async def create_order_command(update, context):
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


async def add_password_command(update, context):
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

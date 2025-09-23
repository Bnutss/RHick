from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from sales.models import Order, Password, OrderProduct
from .auth import AuthHandler


class OrderHandler(AuthHandler):
    @sync_to_async
    def get_orders(self):
        return list(Order.objects.select_related().prefetch_related('products').order_by('-created_at')[:10])

    @sync_to_async
    def get_order_by_id(self, order_id):
        try:
            return Order.objects.prefetch_related('products').get(id=order_id)
        except Order.DoesNotExist:
            return None

    @sync_to_async
    def create_order_sync(self, client, vat, expenses):
        return Order.objects.create(
            client=client,
            vat=vat,
            additional_expenses=expenses
        )

    @sync_to_async
    def update_order_sync(self, order_id, **kwargs):
        Order.objects.filter(id=order_id).update(**kwargs)
        return Order.objects.get(id=order_id)

    @sync_to_async
    def get_statistics(self):
        total_orders = Order.objects.count()
        confirmed_orders = Order.objects.filter(is_confirmed=True).count()
        rejected_orders = Order.objects.filter(is_rejected=True).count()
        pending_orders = total_orders - confirmed_orders - rejected_orders
        total_products = OrderProduct.objects.count()
        passwords_count = Password.objects.count()

        return {
            'total_orders': total_orders,
            'confirmed_orders': confirmed_orders,
            'rejected_orders': rejected_orders,
            'pending_orders': pending_orders,
            'total_products': total_products,
            'passwords_count': passwords_count
        }

    async def show_orders(self, update, context):
        if not await self.is_authorized_user(update):
            return

        orders = await self.get_orders()

        if not orders:
            message_obj = update.message or update.callback_query.message
            await message_obj.reply_text("📋 Заказов пока нет")
            return

        message = "📋 **Последние заказы:**\n\n"
        keyboard = []

        for order in orders:
            status_emoji = "✅" if order.is_confirmed else "❌" if order.is_rejected else "⏳"
            status_text = "Подтвержден" if order.is_confirmed else "Отклонен" if order.is_rejected else "В ожидании"
            total = order.get_total_price()
            products_count = order.products.count()

            message += f"🆔 **Заказ #{order.id}**\n"
            message += f"👤 Клиент: {order.client}\n"
            message += f"📦 Товаров: {products_count}\n"
            message += f"💰 Сумма: ${total:.2f}\n"
            message += f"{status_emoji} Статус: {status_text}\n"
            message += f"📅 Создан: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            if order.confirmed_at:
                message += f"✅ Подтвержден: {order.confirmed_at.strftime('%d.%m.%Y %H:%M')}\n"
            message += "─────────────\n"

            keyboard.append([InlineKeyboardButton(f"🔍 Заказ #{order.id}", callback_data=f"order_{order.id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)

    async def show_order_detail(self, update, context, order_id):
        order = await self.get_order_by_id(order_id)
        if not order:
            await update.callback_query.answer("❌ Заказ не найден")
            return

        message = f"📋 **Заказ #{order.id}**\n\n"
        message += f"👤 **Клиент:** {order.client}\n"
        message += f"🏷️ **НДС:** {order.vat}%\n" if order.vat else "🏷️ **НДС:** Нет\n"
        message += f"💼 **Прочие расходы:** {order.additional_expenses}%\n" if order.additional_expenses else "💼 **Прочие расходы:** Нет\n"
        message += f"📅 **Создан:** {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"

        status_emoji = "✅" if order.is_confirmed else "❌" if order.is_rejected else "⏳"
        status_text = "Подтвержден" if order.is_confirmed else "Отклонен" if order.is_rejected else "В ожидании"
        message += f"{status_emoji} **Статус:** {status_text}\n\n"

        if order.products.exists():
            message += "📦 **Товары:**\n"
            for i, product in enumerate(order.products.all(), 1):
                total_product_price = product.quantity * product.price
                photo_emoji = "📷" if product.photo else "🚫"
                message += f"**{i}.** {product.name}\n"
                message += f"   📊 Количество: {product.quantity}\n"
                message += f"   💵 Цена: ${product.price:.2f}\n"
                message += f"   💰 Сумма: ${total_product_price:.2f}\n"
                message += f"   {photo_emoji} Фото: {'Есть' if product.photo else 'Нет'}\n\n"
        else:
            message += "📦 **Товаров пока нет**\n\n"

        total_without_vat = order.get_total_price()
        total_with_vat = order.get_total_price_with_vat()
        additional_expenses = order.get_additional_expenses_amount()
        final_total = total_with_vat + additional_expenses

        message += f"💰 **Итого:**\n"
        message += f"💵 Без НДС: ${total_without_vat:.2f}\n"
        message += f"🏷️ С НДС: ${total_with_vat:.2f}\n"
        message += f"💼 Доп. расходы: ${additional_expenses:.2f}\n"
        message += f"💎 **Итого к оплате: ${final_total:.2f}**"

        keyboard = [
            [InlineKeyboardButton("➕ Добавить товар", callback_data=f"add_product_{order_id}")],
            [InlineKeyboardButton("📝 Редактировать", callback_data=f"edit_order_{order_id}")],
            [InlineKeyboardButton("📄 Скачать PDF", callback_data=f"pdf_{order_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_orders")]
        ]

        if order.products.exists():
            keyboard.insert(1, [
                InlineKeyboardButton("🗑️ Управление товарами", callback_data=f"manage_products_{order_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_order_creation(self, update, context):
        text = update.message.text
        step = context.user_data.get('order_step')

        if step == 'client':
            context.user_data['order_client'] = text
            context.user_data['order_step'] = 'vat'
            await update.message.reply_text(
                "📝 **Шаг 2/3:** Введите НДС (%) или отправьте 0 если НДС нет\n"
                "💡 Пример: 12 или 0",
                parse_mode='Markdown'
            )

        elif step == 'vat':
            try:
                vat = float(text) if text != '0' else None
                if vat and (vat < 0 or vat > 100):
                    await update.message.reply_text("❌ НДС должен быть от 0 до 100%")
                    return

                context.user_data['order_vat'] = vat
                context.user_data['order_step'] = 'expenses'
                await update.message.reply_text(
                    "📝 **Шаг 3/3:** Введите прочие расходы (%) или отправьте 0\n"
                    "💡 Пример: 5 или 0",
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для НДС (например: 12 или 0)")

        elif step == 'expenses':
            try:
                expenses = float(text) if text != '0' else None
                if expenses and (expenses < 0 or expenses > 100):
                    await update.message.reply_text("❌ Прочие расходы должны быть от 0 до 100%")
                    return

                order = await self.create_order_sync(
                    context.user_data['order_client'],
                    context.user_data['order_vat'],
                    expenses
                )

                context.user_data.clear()

                vat_text = f"{order.vat}%" if order.vat else "Нет"
                expenses_text = f"{order.additional_expenses}%" if order.additional_expenses else "Нет"

                await update.message.reply_text(
                    f"✅ **Заказ #{order.id} успешно создан!**\n\n"
                    f"👤 **Клиент:** {order.client}\n"
                    f"🏷️ **НДС:** {vat_text}\n"
                    f"💼 **Прочие расходы:** {expenses_text}\n"
                    f"📅 **Создан:** {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"💡 Теперь можно добавить товары через /orders",
                    parse_mode='Markdown'
                )

            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для расходов (например: 5 или 0)")

    async def handle_order_editing(self, update, context):
        text = update.message.text
        step = context.user_data.get('edit_step')
        order_id = context.user_data.get('edit_order_id')

        if step == 'client':
            await self.update_order_sync(order_id, client=text)
            context.user_data.clear()
            await update.message.reply_text(f"✅ Название клиента изменено на: **{text}**", parse_mode='Markdown')

        elif step == 'vat':
            try:
                vat = float(text) if text != '0' else None
                if vat and (vat < 0 or vat > 100):
                    await update.message.reply_text("❌ НДС должен быть от 0 до 100%")
                    return

                await self.update_order_sync(order_id, vat=vat)
                context.user_data.clear()
                vat_text = f"{vat}%" if vat else "убран"
                await update.message.reply_text(f"✅ НДС изменен: **{vat_text}**", parse_mode='Markdown')
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для НДС")

        elif step == 'expenses':
            try:
                expenses = float(text) if text != '0' else None
                if expenses and (expenses < 0 or expenses > 100):
                    await update.message.reply_text("❌ Прочие расходы должны быть от 0 до 100%")
                    return

                await self.update_order_sync(order_id, additional_expenses=expenses)
                context.user_data.clear()
                expenses_text = f"{expenses}%" if expenses else "убраны"
                await update.message.reply_text(f"✅ Прочие расходы изменены: **{expenses_text}**",
                                                parse_mode='Markdown')
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для расходов")

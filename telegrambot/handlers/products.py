from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from sales.models import OrderProduct
from .auth import AuthHandler


class ProductHandler(AuthHandler):
    @sync_to_async
    def create_product_sync(self, order_id, name, quantity, price, photo_data=None):
        product = OrderProduct.objects.create(
            order_id=order_id,
            name=name,
            quantity=quantity,
            price=price
        )
        if photo_data:
            photo_file = ContentFile(photo_data, name=f'product_{product.id}.jpg')
            product.photo.save(f'product_{product.id}.jpg', photo_file)
        return product

    @sync_to_async
    def delete_product_sync(self, product_id):
        OrderProduct.objects.filter(id=product_id).delete()

    @sync_to_async
    def get_order_by_id(self, order_id):
        try:
            from sales.models import Order
            return Order.objects.prefetch_related('products').get(id=order_id)
        except Order.DoesNotExist:
            return None

    async def show_products_management(self, update, context, order_id):
        order = await self.get_order_by_id(order_id)
        if not order:
            await update.callback_query.answer("❌ Заказ не найден")
            return

        message = f"🗑️ **Управление товарами заказа #{order_id}**\n\n"
        keyboard = []

        for i, product in enumerate(order.products.all(), 1):
            photo_emoji = "📷" if product.photo else "🚫"
            message += f"**{i}.** {product.name}\n"
            message += f"   📊 x{product.quantity} - ${product.price:.2f} {photo_emoji}\n"
            keyboard.append([InlineKeyboardButton(f"🗑️ Удалить {product.name}",
                                                  callback_data=f"delete_product_{product.id}_{order_id}")])

        keyboard.append([InlineKeyboardButton("⬅️ Назад к заказу", callback_data=f"order_{order_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_product_creation(self, update, context):
        text = update.message.text
        step = context.user_data.get('product_step')

        if step == 'name':
            context.user_data['product_name'] = text
            context.user_data['product_step'] = 'quantity'
            await update.message.reply_text("📝 **Шаг 2/4:** Введите количество товара\n💡 Например: 5")

        elif step == 'quantity':
            try:
                quantity = int(text)
                if quantity <= 0:
                    await update.message.reply_text("❌ Количество должно быть больше 0")
                    return

                context.user_data['product_quantity'] = quantity
                context.user_data['product_step'] = 'price'
                await update.message.reply_text(
                    "📝 **Шаг 3/4:** Введите цену за единицу в долларах\n💡 Например: 150.50")
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для количества")

        elif step == 'price':
            try:
                price = float(text)
                if price <= 0:
                    await update.message.reply_text("❌ Цена должна быть больше 0")
                    return

                context.user_data['product_price'] = price
                context.user_data['product_step'] = 'photo'

                keyboard = [
                    [InlineKeyboardButton("⭐️ Пропустить фото", callback_data="skip_photo")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"📝 **Шаг 4/4:** Отправьте фото товара или пропустите\n\n"
                    f"📦 **Товар:** {context.user_data['product_name']}\n"
                    f"📊 **Количество:** {context.user_data['product_quantity']}\n"
                    f"💰 **Цена:** ${price:.2f}\n\n"
                    f"📷 Отправьте фото или нажмите кнопку ниже",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )

            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для цены")

    async def handle_photo(self, update, context):
        if not await self.is_authorized_user(update):
            return

        if context.user_data.get('adding_product') and context.user_data.get('product_step') == 'photo':
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            photo_bytes = await file.download_as_bytearray()

            order_id = context.user_data.get('product_order_id')
            name = context.user_data.get('product_name')
            quantity = context.user_data.get('product_quantity')
            price = context.user_data.get('product_price')

            product = await self.create_product_sync(order_id, name, quantity, price, photo_bytes)

            context.user_data.clear()

            await update.message.reply_text(
                f"✅ **Товар с фото успешно добавлен!**\n\n"
                f"📦 **Название:** {product.name}\n"
                f"📊 **Количество:** {product.quantity}\n"
                f"💰 **Цена:** ${product.price:.2f}\n"
                f"📷 **Фото:** Добавлено\n"
                f"💎 **Общая стоимость:** ${product.quantity * product.price:.2f}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("📷 Фото можно отправлять только при добавлении товара")

    async def handle_skip_photo(self, update, context):
        order_id = context.user_data.get('product_order_id')
        name = context.user_data.get('product_name')
        quantity = context.user_data.get('product_quantity')
        price = context.user_data.get('product_price')

        product = await self.create_product_sync(order_id, name, quantity, price)

        context.user_data.clear()

        await update.callback_query.edit_message_text(
            f"✅ **Товар успешно добавлен!**\n\n"
            f"📦 **Название:** {product.name}\n"
            f"📊 **Количество:** {product.quantity}\n"
            f"💰 **Цена:** ${product.price:.2f}\n"
            f"💎 **Общая стоимость:** ${product.quantity * product.price:.2f}",
            parse_mode='Markdown'
        )

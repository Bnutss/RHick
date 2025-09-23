from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from telegrambot.utils.pdf_generator import PDFGenerator
from .orders import OrderHandler
from .products import ProductHandler


class CallbackHandler:
    def __init__(self):
        self.order_handler = OrderHandler()
        self.product_handler = ProductHandler()

    async def handle_callback(self, update, context):
        if not await self.order_handler.is_authorized_user(update):
            return

        query = update.callback_query
        await query.answer()

        if query.data == "skip_photo":
            await self.product_handler.handle_skip_photo(update, context)

        elif query.data.startswith("order_"):
            order_id = int(query.data.split("_")[1])
            await self.order_handler.show_order_detail(update, context, order_id)

        elif query.data.startswith("add_product_"):
            order_id = int(query.data.split("_")[2])
            context.user_data['adding_product'] = True
            context.user_data['product_order_id'] = order_id
            context.user_data['product_step'] = 'name'

            await query.edit_message_text(
                "➕ **Добавление товара**\n\n"
                "📝 **Шаг 1/4:** Введите название товара\n"
                "💡 Например: Камера видеонаблюдения",
                parse_mode='Markdown'
            )

        elif query.data.startswith("edit_order_"):
            order_id = int(query.data.split("_")[2])
            context.user_data['editing_order'] = True
            context.user_data['edit_order_id'] = order_id
            context.user_data['edit_step'] = 'choice'

            keyboard = [
                [InlineKeyboardButton("👤 Изменить клиента", callback_data=f"edit_client_{order_id}")],
                [InlineKeyboardButton("🏷️ Изменить НДС", callback_data=f"edit_vat_{order_id}")],
                [InlineKeyboardButton("💼 Изменить расходы", callback_data=f"edit_expenses_{order_id}")],
                [InlineKeyboardButton("✅ Подтвердить заказ", callback_data=f"confirm_order_{order_id}")],
                [InlineKeyboardButton("❌ Отклонить заказ", callback_data=f"reject_order_{order_id}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"order_{order_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"📝 **Редактирование заказа #{order_id}**\n\n"
                f"🔧 Выберите что хотите изменить:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        elif query.data.startswith("edit_client_"):
            order_id = int(query.data.split("_")[2])
            context.user_data['editing_order'] = True
            context.user_data['edit_order_id'] = order_id
            context.user_data['edit_step'] = 'client'

            await query.edit_message_text("👤 **Введите новое название клиента:**", parse_mode='Markdown')

        elif query.data.startswith("edit_vat_"):
            order_id = int(query.data.split("_")[2])
            context.user_data['editing_order'] = True
            context.user_data['edit_order_id'] = order_id
            context.user_data['edit_step'] = 'vat'

            await query.edit_message_text("🏷️ **Введите новый НДС (%) или 0:**\n💡 Например: 12 или 0",
                                          parse_mode='Markdown')

        elif query.data.startswith("edit_expenses_"):
            order_id = int(query.data.split("_")[2])
            context.user_data['editing_order'] = True
            context.user_data['edit_order_id'] = order_id
            context.user_data['edit_step'] = 'expenses'

            await query.edit_message_text("💼 **Введите новые прочие расходы (%) или 0:**\n💡 Например: 5 или 0",
                                          parse_mode='Markdown')

        elif query.data.startswith("confirm_order_"):
            order_id = int(query.data.split("_")[2])
            await self.order_handler.update_order_sync(order_id, is_confirmed=True, is_rejected=False)
            await query.edit_message_text("✅ **Заказ подтвержден!**", parse_mode='Markdown')
            await self.order_handler.show_order_detail(update, context, order_id)

        elif query.data.startswith("reject_order_"):
            order_id = int(query.data.split("_")[2])
            await self.order_handler.update_order_sync(order_id, is_rejected=True, is_confirmed=False)
            await query.edit_message_text("❌ **Заказ отклонен!**", parse_mode='Markdown')
            await self.order_handler.show_order_detail(update, context, order_id)

        elif query.data.startswith("pdf_"):
            order_id = int(query.data.split("_")[1])
            order = await self.order_handler.get_order_by_id(order_id)
            if order:
                pdf_buffer = await sync_to_async(PDFGenerator.generate_order_pdf)(order)
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=pdf_buffer,
                    filename=f"order_{order_id}.pdf",
                    caption=f"📄 PDF заказа #{order_id}"
                )

        elif query.data.startswith("manage_products_"):
            order_id = int(query.data.split("_")[2])
            await self.product_handler.show_products_management(update, context, order_id)

        elif query.data.startswith("delete_product_"):
            parts = query.data.split("_")
            product_id = int(parts[2])
            order_id = int(parts[3])
            await self.product_handler.delete_product_sync(product_id)
            await query.answer("✅ Товар удален!")
            await self.product_handler.show_products_management(update, context, order_id)

        elif query.data == "back_to_orders":
            await self.order_handler.show_orders(update, context)

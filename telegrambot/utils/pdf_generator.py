from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from io import BytesIO
import base64
import os


class PDFGenerator:
    @staticmethod
    def get_image_base64(image_field):
        if not image_field:
            return None

        try:
            image_path = image_field.path
            if os.path.exists(image_path):
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
                    encoded_string = base64.b64encode(image_data).decode('utf-8')

                    file_extension = os.path.splitext(image_path)[1].lower()
                    if file_extension in ['.jpg', '.jpeg']:
                        mime_type = 'image/jpeg'
                    elif file_extension == '.png':
                        mime_type = 'image/png'
                    elif file_extension == '.gif':
                        mime_type = 'image/gif'
                    else:
                        mime_type = 'application/octet-stream'

                    return f"data:{mime_type};base64,{encoded_string}"
        except Exception as e:
            print(f"Ошибка при обработке изображения: {e}")
            return None

        return None

    @staticmethod
    def generate_order_pdf(order):
        products = order.products.all()
        products_with_total = []

        for product in products:
            product_data = {
                'name': product.name,
                'quantity': product.quantity,
                'price': product.price,
                'total_price': product.quantity * product.price,
                'photo': product.photo if product.photo else None,
                'photo_base64': PDFGenerator.get_image_base64(product.photo) if product.photo else None
            }
            products_with_total.append(product_data)

        context = {
            'order': order,
            'products': products_with_total,
            'total_without_vat': order.get_total_price(),
            'total_with_vat': order.get_total_price_with_vat(),
            'additional_expenses': order.get_additional_expenses_amount(),
            'final_total': order.get_total_price_with_vat() + order.get_additional_expenses_amount(),
        }

        html_string = render_to_string('telegram/order_pdf.html', context)

        # base_url нужен в 53.4 для корректной подгрузки css и статики
        pdf_bytes = HTML(
            string=html_string,
            base_url=os.getcwd()
        ).write_pdf(
            stylesheets=[CSS(string='@page { size: A4; margin: 8mm; }')]
        )

        return BytesIO(pdf_bytes)

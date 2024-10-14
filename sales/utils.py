from openpyxl.styles import Font, Alignment
import os
import requests
from openpyxl.drawing.image import Image
from openpyxl import Workbook
from PIL import Image as PILImage

TELEGRAM_BOT_TOKEN = '7775474735:AAFHyJw-YL1e91AIVj-KIrWxg8Ps6GprXhs'
TELEGRAM_CHAT_ID = '-1002411014709'


def convert_webp_to_png(webp_path):
    img = PILImage.open(webp_path)
    temp_png_path = webp_path.replace('.webp', '.png')
    img.save(temp_png_path, 'PNG')
    return temp_png_path


def generate_order_excel(order):
    wb = Workbook()
    ws = wb.active
    ws.title = "Order"

    # Устанавливаем значения и выравнивание для заголовков
    headers = ["Название клиента:", order.client, "Использованный НДС:", f"{order.vat}%"]
    for col in range(0, len(headers), 2):
        cell = ws.cell(row=1 + col // 2, column=1, value=headers[col])
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='left', vertical='center')

        cell = ws.cell(row=1 + col // 2, column=2, value=headers[col + 1])
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Заголовки таблицы
    table_headers = ["Название продукта", "Фото", "Количество", "Цена за единицу", "Общая стоимость"]
    for col_num, header in enumerate(table_headers, 1):
        cell = ws.cell(row=4, column=col_num, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    row_num = 5
    for product in order.products.all():
        ws.cell(row=row_num, column=1, value=product.name).alignment = Alignment(horizontal='center', vertical='center')

        if product.photo:
            photo_path = product.photo.path
            if photo_path.lower().endswith('.webp'):
                photo_path = convert_webp_to_png(photo_path)

            img = Image(photo_path)
            img.width = 30  # Установите ширину изображения (в соответствии с шириной ячейки)
            img.height = 30  # Установите высоту изображения (в соответствии с высотой ячейки)

            # Привязка изображения к ячейке
            img.anchor = f'B{row_num}'  # Привязка к ячейке

            ws.add_image(img)

        ws.cell(row=row_num, column=3, value=product.quantity).alignment = Alignment(horizontal='center',
                                                                                     vertical='center')
        ws.cell(row=row_num, column=4, value=product.price).alignment = Alignment(horizontal='center',
                                                                                  vertical='center')
        ws.cell(row=row_num, column=5, value=product.quantity * product.price).alignment = Alignment(
            horizontal='center', vertical='center')

        # Устанавливаем высоту строки для изображений
        ws.row_dimensions[row_num].height = 30  # Высота строки для соответствия высоте изображения

        row_num += 1

    total_price = order.get_total_price()
    total_price_with_vat = order.get_total_price_with_vat()

    ws.cell(row=row_num, column=4, value="Итого без НДС:").font = Font(bold=True)
    ws.cell(row=row_num, column=4).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=row_num, column=5, value=total_price).font = Font(bold=True)
    ws.cell(row=row_num, column=5).alignment = Alignment(horizontal='center', vertical='center')

    ws.cell(row=row_num + 1, column=4, value="Итого с НДС:").font = Font(bold=True)
    ws.cell(row=row_num + 1, column=4).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=row_num + 1, column=5, value=total_price_with_vat).font = Font(bold=True)
    ws.cell(row=row_num + 1, column=5).alignment = Alignment(horizontal='center', vertical='center')

    # Устанавливаем ширину столбцов
    ws.column_dimensions['A'].width = 30  # Ширина столбца "Название продукта"
    ws.column_dimensions['B'].width = 30  # Ширина столбца "Фото" (размер ячейки для изображения)
    ws.column_dimensions['C'].width = 20  # Ширина столбца "Количество"
    ws.column_dimensions['D'].width = 20  # Ширина столбца "Цена за единицу"
    ws.column_dimensions['E'].width = 20  # Ширина столбца "Общая стоимость"

    file_name = f"order_{order.id}.xlsx"
    file_path = os.path.join("/tmp", file_name)
    wb.save(file_path)

    return file_path


def send_order_to_telegram(order):
    file_path = generate_order_excel(order)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as file:
        response = requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'document': file})

    os.remove(file_path)

    return response.status_code == 200

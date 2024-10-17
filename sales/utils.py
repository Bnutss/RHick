from openpyxl.styles import Font, Alignment
from openpyxl.drawing.image import Image
from openpyxl import Workbook
from PIL import Image as PILImage
import os
import requests
import mimetypes
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import SimpleDocTemplate, Table, Spacer, TableStyle, Image as ReportLabImage

# Регистрация MIME-типа для .webp
mimetypes.add_type('image/webp', '.webp')

TELEGRAM_BOT_TOKEN = '7775474735:AAFHyJw-YL1e91AIVj-KIrWxg8Ps6GprXhs'
TELEGRAM_CHAT_ID = '-1002411014709'


# TELEGRAM_CHAT_ID = '-4535617387'


def convert_webp_to_png(photo_path):
    """Конвертирует изображение .webp в .png."""
    png_path = photo_path.replace('.webp', '.png')
    with PILImage.open(photo_path) as img:
        img.save(png_path, 'PNG')
    return png_path


def generate_order_excel(order):
    """Генерирует Excel-файл с заказом."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Order"

    # Заголовки
    headers = ["Название клиента:", order.client, "Использованный НДС:", f"{order.vat}%"]
    for col in range(0, len(headers), 2):
        cell = ws.cell(row=1 + col // 2, column=1, value=headers[col])
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='left', vertical='center')

        cell = ws.cell(row=1 + col // 2, column=2, value=headers[col + 1])
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Таблица с продуктами
    table_headers = ["Название товара", "Фото", "Количество", "Цена за единицу", "Общая стоимость"]
    for col_num, header in enumerate(table_headers, 1):
        cell = ws.cell(row=4, column=col_num, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    row_num = 5
    for product in order.products.all():
        ws.cell(row=row_num, column=1, value=product.name).alignment = Alignment(horizontal='center', vertical='center')

        if product.photo:
            photo_path = product.photo.path
            try:
                # Если изображение в формате .webp, конвертируем его
                if photo_path.lower().endswith('.webp'):
                    photo_path = convert_webp_to_png(photo_path)

                img = Image(photo_path)
                img.width = 30  # Устанавливаем ширину изображения
                img.height = 30  # Устанавливаем высоту изображения

                # Добавляем изображение в ячейку
                img.anchor = f'B{row_num}'
                ws.add_image(img)
            except Exception as e:
                # Обработка ошибок при добавлении изображения
                print(f"Ошибка обработки изображения: {e}")
                ws.cell(row=row_num, column=2, value="Изображение недоступно")

        ws.cell(row=row_num, column=3, value=product.quantity).alignment = Alignment(horizontal='center',
                                                                                     vertical='center')
        ws.cell(row=row_num, column=4, value=product.price).alignment = Alignment(horizontal='center',
                                                                                  vertical='center')
        ws.cell(row=row_num, column=5, value=product.quantity * product.price).alignment = Alignment(
            horizontal='center', vertical='center')

        ws.row_dimensions[row_num].height = 30  # Устанавливаем высоту строки для соответствия изображения
        row_num += 1

    # Итого
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

    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20

    # Сохраняем Excel-файл
    file_name = f"Заказ-{order.id}.xlsx"
    file_path = os.path.join("/tmp", file_name)
    wb.save(file_path)

    return file_path


# Функция для регистрации шрифта
def register_fonts():
    font_path = os.path.join(os.path.dirname(__file__), 'static', 'fonts', 'Roboto-Regular.ttf')
    # Для автономного проекта используйте:
    # font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'Roboto-Regular.ttf')

    # Регистрация шрифта Roboto
    pdfmetrics.registerFont(TTFont('Roboto', font_path))


# Функция для конвертации изображения (если оно в формате webp)
def convert_image_for_pdf(photo_path):
    """Конвертирует изображение для вставки в PDF, если оно в формате .webp."""
    if photo_path.lower().endswith('.webp'):
        png_path = photo_path.replace('.webp', '.png')
        with PILImage.open(photo_path) as img:
            img.save(png_path, 'PNG')
        return png_path
    return photo_path


# Основная функция для генерации PDF
def generate_order_pdf(order):
    register_fonts()

    pdf_file_name = f"Заказ-{order.id}.pdf"
    pdf_file_path = os.path.join("/tmp", pdf_file_name)
    doc = SimpleDocTemplate(pdf_file_path, pagesize=A4, rightMargin=1 * cm, leftMargin=1 * cm, topMargin=1 * cm,
                            bottomMargin=1 * cm)
    elements = []

    # Логотип в правом верхнем углу с уменьшенным размером
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images',
                             'Logo.png')  # Замените на ваш путь к логотипу
    if os.path.exists(logo_path):
        logo = ReportLabImage(logo_path, width=1.3 * cm, height=1.3 * cm)
        elements.append(Table([[logo]], colWidths=[18 * cm], style=[('ALIGN', (0, 0), (-1, -1), 'RIGHT')]))

    elements.append(Spacer(1, 0.2 * cm))  # Небольшой отступ после логотипа

    # Таблица с клиентом и НДС
    elements.append(Table([[f"Клиент: {order.client}"], [f"НДС: {order.vat}%"]], colWidths=[20 * cm],
                          style=[('FONTNAME', (0, 0), (-1, -1), 'Roboto'), ('FONTSIZE', (0, 0), (-1, -1), 10)]))
    elements.append(Spacer(2, 0.2 * cm))  # Добавляем небольшой отступ

    # Данные таблицы товаров
    data = [["Название товара", "Фото", "Количество", "Цена за единицу", "Общая стоимость"]]

    for product in order.products.all():
        row = [product.name, "", product.quantity, product.price, product.quantity * product.price]

        # Обработка фото продукта
        if product.photo:
            photo_path = convert_image_for_pdf(product.photo.path)
            if os.path.exists(photo_path):
                img = ReportLabImage(photo_path, width=1 * cm, height=1 * cm)
                row[1] = img

        data.append(row)

    # Создание таблицы с товарами
    table = Table(data, colWidths=[7 * cm, 2 * cm, 3 * cm, 4 * cm, 4 * cm])  # Уменьшаем ширину столбцов
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (0, -1), 'Roboto'),
        ('FONTSIZE', (0, 1), (0, -1), 7.3),  # Уменьшаем шрифт в названиях продукта до 6
        ('FONTNAME', (0, 0), (-1, 0), 'Roboto'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))  # Добавляем отступ

    # Расчет итогов
    total_price = order.get_total_price()
    total_price_with_vat = order.get_total_price_with_vat()

    # Данные итогов
    totals_data = [
        ["Итого без НДС", f"{total_price:.2f}"],
        ["Итого с НДС", f"{total_price_with_vat:.2f}"]
    ]

    # Создание таблицы с итогами
    totals_table = Table(totals_data, colWidths=[5 * cm, 15 * cm])
    totals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Выравнивание итоговых сумм по правому краю
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),  # Выравнивание по нижнему краю
        ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(totals_table)

    # Сохранение PDF
    doc.build(elements)

    return pdf_file_path


def send_order_to_telegram(order, file_type='excel'):
    """Отправляет заказ в Telegram в виде Excel- или PDF-файла."""
    if file_type == 'pdf':
        file_path = generate_order_pdf(order)
    else:
        file_path = generate_order_excel(order)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as file:
        response = requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'document': file})

    # Удаляем временный файл после отправки
    os.remove(file_path)

    return response.status_code == 200

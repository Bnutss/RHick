from openpyxl.styles import Font, Alignment
from openpyxl.drawing.image import Image
from openpyxl import Workbook
from PIL import Image as PILImage
import os
import base64
import requests
import mimetypes
from weasyprint import HTML

mimetypes.add_type('image/webp', '.webp')

TELEGRAM_BOT_TOKEN = '7775474735:AAHcPmCc7VpC_bxzgDWQvQs_lTpjCAV0C8Q'
TELEGRAM_CHAT_ID = '-1002411014709'

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'sales', 'order_pdf.html')
LOGO_PATH = os.path.join(os.path.dirname(__file__), 'static', 'images', 'Logo.png')


def get_logo_base64():
    try:
        with open(LOGO_PATH, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"Ошибка при загрузке логотипа: {e}")
        return None


def convert_webp_to_png(photo_path):
    png_path = photo_path.replace('.webp', '.png')
    with PILImage.open(photo_path) as img:
        img.save(png_path, 'PNG')
    return png_path


def get_image_base64(photo_field):
    if not photo_field:
        return None
    try:
        path = photo_field.path
        if path.lower().endswith('.webp'):
            path = convert_webp_to_png(path)
        if not os.path.exists(path):
            return None
        ext = os.path.splitext(path)[1].lower()
        mime = 'image/jpeg' if ext in ['.jpg',
                                       '.jpeg'] else 'image/png' if ext == '.png' else 'image/gif' if ext == '.gif' else 'application/octet-stream'
        with open(path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime};base64,{encoded}"
    except Exception as e:
        print(f"Ошибка при обработке изображения: {e}")
        return None


def generate_order_excel(order):
    wb = Workbook()
    ws = wb.active
    ws.title = "Order"

    headers = [
        "Название клиента:", order.client,
        "Использованный НДС:", f"{order.vat}%",
        "Прочие расходы (%):", f"{order.additional_expenses}%"
    ]

    for col in range(0, len(headers), 2):
        cell = ws.cell(row=1 + col // 2, column=1, value=headers[col])
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='left', vertical='center')
        cell = ws.cell(row=1 + col // 2, column=2, value=headers[col + 1])
        cell.alignment = Alignment(horizontal='center', vertical='center')

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
                if photo_path.lower().endswith('.webp'):
                    photo_path = convert_webp_to_png(photo_path)
                img = Image(photo_path)
                img.width = 30
                img.height = 30
                img.anchor = f'B{row_num}'
                ws.add_image(img)
            except Exception as e:
                print(f"Ошибка обработки изображения: {e}")
                ws.cell(row=row_num, column=2, value="Изображение недоступно")

        ws.cell(row=row_num, column=3, value=product.quantity).alignment = Alignment(horizontal='center',
                                                                                     vertical='center')
        ws.cell(row=row_num, column=4, value=product.price).alignment = Alignment(horizontal='center',
                                                                                  vertical='center')
        ws.cell(row=row_num, column=5, value=product.quantity * product.price).alignment = Alignment(
            horizontal='center', vertical='center')
        ws.row_dimensions[row_num].height = 30
        row_num += 1

    total_price = order.get_total_price()
    total_price_with_vat = order.get_total_price_with_vat()
    additional_expenses_amount = order.get_additional_expenses_amount()
    total_sum = total_price_with_vat + additional_expenses_amount

    ws.cell(row=row_num, column=4, value="Итого без НДС:").font = Font(bold=True)
    ws.cell(row=row_num, column=4).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=row_num, column=5, value=total_price).font = Font(bold=True)
    ws.cell(row=row_num, column=5).alignment = Alignment(horizontal='center', vertical='center')

    ws.cell(row=row_num + 1, column=4, value="Итого с НДС:").font = Font(bold=True)
    ws.cell(row=row_num + 1, column=4).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=row_num + 1, column=5, value=total_price_with_vat).font = Font(bold=True)
    ws.cell(row=row_num + 1, column=5).alignment = Alignment(horizontal='center', vertical='center')

    ws.cell(row=row_num + 2, column=4, value="Прочие расходы:").font = Font(bold=True)
    ws.cell(row=row_num + 2, column=4).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=row_num + 2, column=5, value=additional_expenses_amount).font = Font(bold=True)
    ws.cell(row=row_num + 2, column=5).alignment = Alignment(horizontal='center', vertical='center')

    ws.cell(row=row_num + 3, column=4, value="Общий итог:").font = Font(bold=True)
    ws.cell(row=row_num + 3, column=4).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=row_num + 3, column=5, value=total_sum).font = Font(bold=True)
    ws.cell(row=row_num + 3, column=5).alignment = Alignment(horizontal='center', vertical='center')

    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20

    file_name = f"Заказ-{order.id}.xlsx"
    file_path = os.path.join("/tmp", file_name)
    wb.save(file_path)
    return file_path


def generate_order_pdf(order):
    products_rows = ''
    for i, product in enumerate(order.products.all(), 1):
        photo_base64 = get_image_base64(product.photo) if product.photo else None
        if photo_base64:
            photo_cell = (
                f'<div class="photo-wrap">'
                f'<img src="{photo_base64}" class="product-image">'
                f'</div>'
            )
        else:
            photo_cell = '<div class="photo-wrap"><div class="no-photo-icon">Нет<br>фото</div></div>'

        total = product.quantity * product.price
        products_rows += f'''
        <tr>
            <td class="td-num"><span class="row-num">{i:02d}</span></td>
            <td class="td-name">
                <div class="product-name-text">{product.name}</div>
            </td>
            <td class="td-photo">{photo_cell}</td>
            <td class="td-qty">{product.quantity}</td>
            <td class="td-price">{product.price:.2f}</td>
            <td class="td-total">{total:.2f}</td>
        </tr>'''

    total_without_vat = order.get_total_price()
    total_with_vat = order.get_total_price_with_vat()
    additional_expenses_amount = order.get_additional_expenses_amount()
    final_total = total_with_vat + additional_expenses_amount

    if order.is_confirmed:
        status_class, status_text = 'status-confirmed', 'Подтвержден'
    elif order.is_rejected:
        status_class, status_text = 'status-rejected', 'Отклонен'
    else:
        status_class, status_text = 'status-pending', 'В ожидании'

    created_at = order.created_at.strftime('%d.%m.%Y %H:%M') if hasattr(order.created_at, 'strftime') else str(
        order.created_at)

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()

    advance_row = (
        f'<div class="totals-row advance-row">'
        f'<span class="t-label">Аванс</span>'
        f'<span class="t-value">{order.advance:.2f}</span>'
        f'</div>'
    ) if order.advance else ''

    logo_base64 = get_logo_base64()
    logo_html = (
        f'<img src="{logo_base64}" class="logo-img" alt="RHIK">'
        if logo_base64
        else '<span>RHIK</span>'
    )

    html = (template
            .replace('{{ order_id }}', str(order.id))
            .replace('{{ created_at }}', created_at)
            .replace('{{ client }}', str(order.client))
            .replace('{{ vat }}', str(order.vat if order.vat else 0))
            .replace('{{ additional_expenses_pct }}',
                     str(order.additional_expenses if order.additional_expenses else 0))
            .replace('{{ status_class }}', status_class)
            .replace('{{ status_text }}', status_text)
            .replace('{{ products_rows }}', products_rows)
            .replace('{{ total_without_vat }}', f'{total_without_vat:.2f}')
            .replace('{{ total_with_vat }}', f'{total_with_vat:.2f}')
            .replace('{{ additional_expenses_amount }}', f'{additional_expenses_amount:.2f}')
            .replace('{{ advance_row }}', advance_row)
            .replace('{{ final_total }}', f'{final_total:.2f}')
            .replace('{{ logo_img }}', logo_html)
            )

    pdf_bytes = HTML(string=html, base_url=os.getcwd()).write_pdf()

    pdf_file_path = os.path.join("/tmp", f"Заказ-{order.id}.pdf")
    with open(pdf_file_path, 'wb') as f:
        f.write(pdf_bytes)

    return pdf_file_path


def send_order_to_telegram(order, file_type='excel'):
    if file_type == 'pdf':
        file_path = generate_order_pdf(order)
    else:
        file_path = generate_order_excel(order)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as file:
        response = requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'document': file})

    os.remove(file_path)
    return response.status_code == 200

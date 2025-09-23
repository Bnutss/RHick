import json
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from telegram import Update
import threading

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def telegram_webhook(request):
    try:
        json_str = request.body.decode('UTF-8')
        update_data = json.loads(json_str)

        # Запускаем обработку в отдельном потоке
        thread = threading.Thread(target=process_update_sync, args=(update_data,))
        thread.start()

        return HttpResponse("OK")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return HttpResponse("OK")


def process_update_sync(update_data):
    """Синхронная обработка обновления"""
    try:
        # Здесь будет простая логика без async/await
        print(f"Received update: {update_data}")
    except Exception as e:
        logger.error(f"Error processing update: {e}")

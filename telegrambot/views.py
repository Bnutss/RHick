import json
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from telegram import Update, Bot
from django.utils.decorators import method_decorator
from django.views import View

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def telegram_webhook(request):
    try:
        json_data = json.loads(request.body.decode('utf-8'))
        update = Update.de_json(json_data, Bot(settings.TELEGRAM_BOT_TOKEN))

        from .bot_logic import handle_telegram_update
        handle_telegram_update(update)

        return HttpResponse('OK')
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return HttpResponse('OK')

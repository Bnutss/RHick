from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import Order, OrderProduct
from .serializers import OrderSerializer, OrderProductSerializer, OrderDetailSerializer
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from .utils import send_order_to_telegram
from django.views.decorators.csrf import csrf_exempt
import logging
import os
from django.utils.dateparse import parse_date
from datetime import datetime, time

logger = logging.getLogger(__name__)


class OrderListCreateAPIView(APIView):
    def get(self, request):
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderSerializer(order, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderProductsAPIView(APIView):
    """
    API для работы с продуктами заказа
    """

    def get(self, request, order_id):
        """
        Получить список продуктов для указанного заказа и общую сумму заказа.
        """
        order = get_object_or_404(Order, id=order_id)
        products = OrderProduct.objects.filter(order=order)

        if not products.exists():
            return Response({"detail": "Продукты для этого заказа не найдены."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderProductSerializer(products, many=True)
        total_order_price = sum([product.quantity * product.price for product in products])

        return Response({
            "products": serializer.data,
            "total_order_price": total_order_price
        }, status=status.HTTP_200_OK)

    def post(self, request, order_id):
        """
        Добавить продукт в указанный заказ.
        """
        order = get_object_or_404(Order, id=order_id)
        data = request.data.copy()
        data.pop('id', None)
        data['order'] = order.id

        if 'photo' in request.FILES:
            data['photo'] = request.FILES['photo']

        logger.debug(f"Data before saving: {data}")
        serializer = OrderProductSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Ошибки сериализатора: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, order_id, product_id):
        """
        Редактировать продукт в указанном заказе.
        """
        order = get_object_or_404(Order, id=order_id)
        product = get_object_or_404(OrderProduct, id=product_id, order=order)
        data = request.data.copy()
        data['order'] = order.id

        if 'photo' in request.FILES:
            data['photo'] = request.FILES['photo']

        serializer = OrderProductSerializer(product, data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            print(f"Ошибки сериализатора: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, order_id, product_id):
        """
        Удалить продукт из указанного заказа и его фото.
        """
        order = get_object_or_404(Order, id=order_id)
        product = get_object_or_404(OrderProduct, id=product_id, order=order)

        if product.photo:
            photo_path = product.photo.path
            product.delete()

            if os.path.exists(photo_path):
                os.remove(photo_path)
        else:
            product.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderConfirmAPIView(APIView):
    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if order.is_rejected:
            return Response({"error": "Нельзя подтвердить отклоненный заказ"}, status=status.HTTP_400_BAD_REQUEST)
        order.is_confirmed = True
        order.save()
        return Response({"status": "Заказ подтвержден"}, status=status.HTTP_200_OK)


class OrderRejectAPIView(APIView):
    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if order.is_confirmed:
            return Response({"error": "Нельзя отклонить подтвержденный заказ"}, status=status.HTTP_400_BAD_REQUEST)
        order.is_rejected = True
        order.save()
        return Response({"status": "Заказ отклонен"}, status=status.HTTP_200_OK)


@csrf_exempt
def export_order_to_telegram(request, order_id):
    """
    Эндпоинт для экспорта заказа в Telegram в формате Excel или PDF.
    """
    try:
        # Получаем заказ по ID
        order = Order.objects.get(id=order_id)

        # Получаем тип файла из параметров GET, по умолчанию 'excel'
        file_type = request.GET.get('file_type', 'excel')

        # Отправляем заказ в Telegram
        success = send_order_to_telegram(order, file_type=file_type)

        if success:
            return JsonResponse({'status': 'success', 'message': 'Заказ успешно отправлен в Telegram.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Не удалось отправить заказ в Telegram.'}, status=500)

    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Заказ не найден.'}, status=404)


class ConfirmedOrdersView(APIView):
    def get(self, request, *args, **kwargs):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        confirmed_orders = Order.objects.filter(is_confirmed=True)

        if start_date:
            start_date = parse_date(start_date)
            if start_date:
                start_datetime = datetime.combine(start_date, time.min)
                confirmed_orders = confirmed_orders.filter(created_at__gte=start_datetime)

        if end_date:
            end_date = parse_date(end_date)
            if end_date:
                end_datetime = datetime.combine(end_date, time.max)
                confirmed_orders = confirmed_orders.filter(created_at__lte=end_datetime)

        # Serialize the data
        serializer = OrderSerializer(confirmed_orders, many=True)
        total_sum = sum(order['total_price_with_vat'] for order in serializer.data)

        return Response({
            "orders": serializer.data,
            "total_sum": total_sum
        }, status=status.HTTP_200_OK)

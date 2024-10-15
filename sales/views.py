from rest_framework import status
from .models import Order, OrderProduct
from .serializers import OrderSerializer, OrderProductSerializer, OrderDetailSerializer
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from .utils import send_order_to_telegram
from django.views.decorators.csrf import csrf_exempt


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

        # Общая сумма по всем продуктам заказа
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

        # Указание id заказа
        data['order'] = order.id

        # Проверка наличия файла фото
        if 'photo' in request.FILES:
            data['photo'] = request.FILES['photo']

        serializer = OrderProductSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            # Логирование ошибок сериализатора для отладки
            print(f"Ошибки сериализатора: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, order_id, product_id):
        """
        Редактировать продукт в указанном заказе.
        """
        order = get_object_or_404(Order, id=order_id)
        product = get_object_or_404(OrderProduct, id=product_id, order=order)

        data = request.data.copy()
        data['order'] = order.id

        # Обработка фото, если оно передается
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
        Удалить продукт из указанного заказа.
        """
        order = get_object_or_404(Order, id=order_id)
        product = get_object_or_404(OrderProduct, id=product_id, order=order)

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
    Эндпоинт для экспорта заказа в Telegram без проверки CSRF.
    """
    try:
        order = Order.objects.get(id=order_id)
        success = send_order_to_telegram(order)

        if success:
            return JsonResponse({'status': 'success', 'message': 'Заказ успешно отправлен в Telegram.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Не удалось отправить заказ в Telegram.'}, status=500)

    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Заказ не найден.'}, status=404)

from django.urls import path
from .views import (OrderListCreateAPIView, OrderDetailAPIView, OrderProductsAPIView, OrderConfirmAPIView,
                    OrderRejectAPIView, export_order_to_telegram, ConfirmedOrdersView)

app_name = 'sales'

urlpatterns = [
    path('api/orders/', OrderListCreateAPIView.as_view(), name='order-list-create'),
    path('api/orders/<int:pk>/', OrderDetailAPIView.as_view(), name='order-detail'),
    path('api/orders/<int:order_id>/products/', OrderProductsAPIView.as_view(), name='order-products'),
    path('api/orders/<int:order_id>/products/<int:product_id>/', OrderProductsAPIView.as_view(),
         name='order-product-detail'),

    # Маршруты для подтверждения и отклонения заказов
    path('api/orders/<int:pk>/confirm/', OrderConfirmAPIView.as_view(), name='order-confirm'),
    path('api/orders/<int:pk>/reject/', OrderRejectAPIView.as_view(), name='order-reject'),
    path('api/orders/<int:order_id>/export_to_telegram/', export_order_to_telegram, name='export_to_telegram'),
    path('api/confirmed-orders/', ConfirmedOrdersView.as_view(), name='confirmed-orders'),

]

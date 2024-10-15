from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LoginAPIView, UserDetailView

app_name = 'users'

urlpatterns = [
    path('', LoginView.as_view(), name='login'),
    path('api/login/', LoginAPIView.as_view(), name='api_login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/user/', UserDetailView.as_view(), name='user-detail'),

]

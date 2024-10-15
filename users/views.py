from django.contrib.auth import login, authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import LoginSerializer, UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    http_method_names = ['post', ]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            login(request, user)
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Успешный вход!",
                "user_id": user.id,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        return Response(serializer.errors, status=400)

    def options(self, request, *args, **kwargs):
        return Response(status=200)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class LoginView(View):
    def get(self, request):
        return render(request, 'users/login_page.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Вы успешно вошли в систему.')
            return redirect('users:dashboard')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
            return render(request, 'users/login_page.html')
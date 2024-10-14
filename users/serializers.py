from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from users.models import UserProfile


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)

        if user and user.is_active:
            if hasattr(user, 'userprofile'):
                if user.userprofile.mobile_app or user.is_superuser:
                    return user
                else:
                    raise serializers.ValidationError("Этот пользователь не имеет доступа через мобильное приложение.")
            else:
                raise serializers.ValidationError("Профиль пользователя не найден.")
        else:
            raise serializers.ValidationError("Неправильный логин или пароль.")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id_telegram']


class UserSerializer(serializers.ModelSerializer):
    userprofile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['username', 'email', 'userprofile']

    def update(self, instance, validated_data):
        userprofile_data = validated_data.pop('userprofile', {})
        id_telegram = userprofile_data.get('id_telegram')

        instance.email = validated_data.get('email', instance.email)
        instance.save()
        profile = instance.userprofile
        if id_telegram is not None:
            profile.id_telegram = id_telegram
        profile.save()

        return instance

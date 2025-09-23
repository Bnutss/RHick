from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sales/', include('sales.urls', namespace='sales')),
    path('telegram/', include('telegrambot.urls', namespace='telegrambot')),
    path('', include('users.urls', namespace='users')),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

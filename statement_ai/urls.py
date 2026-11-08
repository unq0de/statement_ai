from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from statements.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('api/', include('statements.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
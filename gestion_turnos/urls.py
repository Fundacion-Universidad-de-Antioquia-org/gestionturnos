from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    settings.AUTH.urlpattern,
    path('admin/', admin.site.urls),
    path('account/',include('asignacion_turnos.urls')),
]

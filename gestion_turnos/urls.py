from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.generic import TemplateView
from django.shortcuts import redirect

urlpatterns = [
    settings.AUTH.urlpattern,
    path('admin/', admin.site.urls),
    path('account/',include('asignacion_turnos.urls')),
    path('', lambda request: redirect('/account/home/')),
    #path('', TemplateView.as_view(template_name='account/home.html'), name='home'),
]

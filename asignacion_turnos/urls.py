from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import LoginForm

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(authentication_form=LoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logged_out.html'), name='logout'),
    path('sucesiones_trenes/',views.vista_cargarSucesionTrenes, name= 'vista_cargarSucesionTrenes'),
    path('operadores/',views.vista_cargarSucesionOperador, name='sucesion_operadores'),
    path ('home.html/',views.vista_home, name = 'home'),
    path('cambios_turnos.html/',views.get_solicitudes_cambios_turnos, name= 'cambios_turnos'),
    path('editarHorario.html/',views.editar_horario, name='editar_horario'),
    path('configuraciones.html/',views.vista_configuraciones, name= 'configuraciones'),
    path('cargarInstruccionesOperacionales/',views.vista_cargarIo, name = 'cargarIo'),
    # urls  - > API
    path("api/mis-turnos/", views.get_mis_turnos, name="get_mis_turnos"),
    path('api/sucesion/',views.get_sucesion_cargo,name="get_sucesion_cargo"),
    path('api/actualizar_turno/',views.actualizar_turno, name="actualizar_turno"),
    path('api/consultar_turno/',views.consultar_turno, name="consultar_turno"),
    path('api/traer_horarios/',views.traer_horarios, name = "traer_horarios"),
    path('api/eliminar_horario/',views.eliminar_horario, name="eliminar_horario"),
    path('api/insertar_horario/', views.insertar_horario, name="insertar_horario"),
    path('api/buscar_cambio_turno/', views.buscar_cambio_turno, name="buscar_cambio_turno"),
    path('api/solicitar_cambio_turno/', views.solicitar_cambio_turno, name= "solicitar_cambio_turno"),
    path('api/aprobar_solicitudes_cambios_turnos/', views.aprobar_solicitudes_cambios_turnos, name = "aprobar_solicitudes_cambios_turnos"),
    path('api/desaprobar_solicitudes_cambios_turnos/', views.desaprobar_solicitudes_cambios, name = "desaprobar_solicitudes_cambios_turnos"),
]
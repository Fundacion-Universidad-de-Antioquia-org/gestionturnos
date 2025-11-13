from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CargarDocumentosForm, CargarSucesionOperadoresForm,CargarDatosProno
from django.contrib.auth import authenticate , login
from django.http import HttpResponse
from .resources import peticion_Oddo
from .resources.cargarSucesion import procesar_sucesion_multifila
from .resources.cargarCuadroTunos import procesar_cuadro_turnos
from .resources.validarExtension import validarExcel
from .resources.revisarFestivos import es_festivo_o_domingo
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime
from django.conf import settings
from pathlib import Path
from zoneinfo import ZoneInfo
from django.db.models import F, Value, ExpressionWrapper, DateTimeField, DateField, DurationField
from django.db.models.functions import Cast, TruncWeek, TruncMonth

import pandas as pd
from io import BytesIO


from datetime import datetime, timedelta, date, time
from django.utils import timezone
from django.db.models.functions import TruncMinute, Upper, Trim, Coalesce


from django.db.models import Count
from rest_framework.decorators import api_view
from rest_framework.response import Response
from asignacion_turnos.models import Sucesion
from asignacion_turnos.models import Horario , Cambios_de_turnos, Estados_servicios,Empleado_Oddo, Parametros, Archivos, Solicitudes_Gt, Notificaciones, ConfirmacionLectura,Respuesta_Solicitudes_Gt
from .resources.validarDescanso import validar_descanso
from .resources.registrarLog import send_log
from .resources.cargarArchivosBlob import upload_to_azure_blob
from .resources.enviarCorreoGmail import enviarCorreoGmail, enviarCorreoGmailHTML
from .resources.buscarErrores import sobreCargaLaboral,asignacionServicios, asignacionServiciosTranvia, sobreCargaLaboralTranvia
from .resources.peticion_Oddo import sincronizarDbEmpleados



@settings.AUTH.login_required
def vista_home(request,*, context):

    usuarioLogeado = str(request.user).upper()
    print(usuarioLogeado)

    hoy = datetime.now(ZoneInfo("America/Bogota"))
    mensajeDesatendidas = "Sin solicitudes desatendidas"

    data = sincronizarDbEmpleados()

    if Solicitudes_Gt.objects.filter(fecha_inicial__lt = hoy , estado = "pendiente").exists():
        solicitudes = Solicitudes_Gt.objects.filter(fecha_inicial__lt = hoy , estado = "pendiente").count()
        Solicitudes_Gt.objects.filter(fecha_inicial__lt = hoy , estado = "pendiente").update(estado = "desatendida")
        mensajeDesatendidas = f"Se detectaron {solicitudes} solicitudes sin atender y serán reasignadas a desatendida"

    return render(request,'account/home.html',{
        
        "success": data.get('success'),
        "recibidos": data.get('recibidos'),
        "validos": data.get('validos'),
        "sin_cedula": data.get('sin_cedula'),
        "creados": data.get('creados'),
        "actualizados": data.get('creados'),
        "tiempo_s": data.get('tiempo'),
        "usuarioLogeado": usuarioLogeado,
        "mensajeDesatendidas": mensajeDesatendidas
    })

@settings.AUTH.login_required
def vista_dashboard(request,*, context):
   
    if request.method == "GET":
        
        usuarioLogeado = str(request.user).upper()
        fechaInicial = request.GET.get("fechaInicialFormateada")
        fechaFinal = request.GET.get("fechaFinalFormateada")
        peticion = request.GET.get("peticion")
        print(f"peticion: {peticion}")

        porcentajeAprobacion = None
        porcentajeDesaprobadas = None
        porcentajePendientes = None
        total = None

        MESES_ES = [
        "", "enero","febrero","marzo","abril","mayo","junio",
        "julio","agosto","septiembre","octubre","noviembre","diciembre"]

        if fechaInicial is not None and fechaFinal is not None and peticion is not None:
            print("Enoraadasdadasda")
            if peticion == "academica":

                solicitudesXmes = []
                solicitudesXtotales = []

                solicitudesXuni = []
                cantidadXuni = []
                
                numSolicitudesApro =  Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO", estado = "aprobado").count()
                numSolicitudesDesa =  Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO", estado = "desaprobado").count()
                numSolicitudesPend =  Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO", estado = "pendiente").count()
                numSolicitudesTotal =  Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO").count()
                numSolicitudesDesaten = Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO", estado = "desatendida").count()

                print(f"# aprobadas: {numSolicitudesApro}, desaprobadas: {numSolicitudesDesa}, pendientes: {numSolicitudesPend}, total: {numSolicitudesTotal}")
                
                if numSolicitudesTotal != 0:

                    porcentajeAprobacion = int(100* (numSolicitudesApro/numSolicitudesTotal))
                    porcentajeDesaprobadas = int( 100* (numSolicitudesDesa/numSolicitudesTotal))
                    porcentajePendientes = int (100* (numSolicitudesPend/numSolicitudesTotal))
                    porcentajeDesatendidas = int(100* (numSolicitudesDesaten/numSolicitudesTotal))
                else:

                    porcentajeAprobacion = 0
                    porcentajeDesaprobadas = 0
                    porcentajePendientes = 0
                    porcentajeDesatendidas = 0
               
                solicitudesPorMes = Solicitudes_Gt.objects.filter(tipo_solicitud = "PERMISO ACADEMICO", fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal).annotate(mes = TruncMonth('fecha_solicitud')).values('mes').annotate(total = Count('id')).order_by('mes')
                for s in solicitudesPorMes:
                    texto = f"{MESES_ES[s['mes'].month]} {s['mes'].year}"  # "octubre 2025"
                    solicitudesXmes.append({
                        "mes": texto.capitalize()
                    })
                    solicitudesXtotales.append({
                        "total": s.get("total")
                    })

                solicitudesPorUni = Solicitudes_Gt.objects.filter(tipo_solicitud = "PERMISO ACADEMICO", fecha_inicial__gte = fechaInicial, 
                                              fecha_final__lte = fechaFinal).annotate(u_norm=Upper(Trim('empleado__universidad'))).annotate(universidad=Coalesce('u_norm', 
                                                Value('SIN UNIVERSIDAD'))).values('universidad').annotate(total=Count('id')).order_by('-total', 'universidad')
                
                for s in solicitudesPorUni:
                    solicitudesXuni.append({
                        "nombre": s.get('universidad')
                    })

                    cantidadXuni.append({
                        "cantidad": s.get("total")
                    })
              
             
                return render(request,"account/dashboard.html",{
                    'usuarioLogeado': usuarioLogeado,
                    'porcentajeAprobacion': porcentajeAprobacion,
                    'porcentajeDesaprobadas': porcentajeDesaprobadas,
                    'porcentajePendientes':porcentajePendientes,
                    'porcentajeDesatendidas': porcentajeDesatendidas,
                    'numSolicitudesTotal':numSolicitudesTotal,
                    'fechaIni':fechaInicial,
                    'fechaFin': fechaFinal,
                    'solicitudesXmes': solicitudesXmes,
                    'solicitudesXtotales': solicitudesXtotales,
                    'solicitudesXuni': solicitudesXuni,
                    'cantidadXuni':cantidadXuni

                })
            elif peticion == "personal":

                numSolicitudesApro =  Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO", estado = "aprobado").count()
                numSolicitudesDesa =  Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO", estado = "desaprobado").count()
                numSolicitudesPend =  Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO", estado = "pendiente").count()
                numSolicitudesTotal =  Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal, tipo_solicitud = "PERMISO ACADEMICO").count()

                porcentajeAprobacion = int(100* (numSolicitudesApro/numSolicitudesTotal))
                porcentajeDesaprobadas = int(100* (numSolicitudesDesa/numSolicitudesTotal))
                porcentajePendientes = int(100* (numSolicitudesPend/numSolicitudesTotal))

                solicitudesXmes = []
                solicitudesXtotales = []
                solicitudesPorMes = Solicitudes_Gt.objects.filter(tipo_solicitud = "PERMISO ACADEMICO").annotate(mes = TruncMonth('fecha_solicitud')).values('mes').annotate(total = Count('id')).order_by('mes')
                for s in solicitudesPorMes:
                    solicitudesXmes.append({
                        "mes":s["mes"].strftime('%B %Y').capitalize()
                    })
                    solicitudesXtotales.append({
                        "total": s.get("total")
                    })

                print(f"Solicitudes por meses: {solicitudesXmes}")
                print(f"Solicitudes por totales: {solicitudesXtotales}")
                
                return render(request,"account/dashboard_personales.html",{
                    'usuarioLogeado': usuarioLogeado,
                    'porcentajeAprobacion': porcentajeAprobacion,
                    'porcentajeDesaprobadas': porcentajeDesaprobadas,
                    'porcentajePendientes':porcentajePendientes,
                    'numSolicitudesTotal':numSolicitudesTotal,
                    'fechaIni':fechaInicial,
                    'fechaFin': fechaFinal,
                    'solicitudesXmes': solicitudesXmes,
                    'solicitudesXtotales': solicitudesXtotales

                })
        else:
            print("parametros fallidos ")   
            return render(request,"account/dashboard.html",{
                    'usuarioLogeado': usuarioLogeado,
                    'porcentajeAprobacion': porcentajeAprobacion,
                    'porcentajeDesaprobadas': porcentajeDesaprobadas,
                    'porcentajePendientes':porcentajePendientes,
                    'numSolicitudesTotal':total,
                    'solicitudesXmes': solicitudesXmes,
                    'solicitudesXtotales': solicitudesXtotales
                })

    else:
        return render(request,"account/dashboard.html",{
                    'usuarioLogeado': usuarioLogeado,
                    'porcentajeAprobacion': porcentajeAprobacion,
                    'porcentajeDesaprobadas': porcentajeDesaprobadas,
                    'porcentajePendientes':porcentajePendientes,
                    'numSolicitudesTotal':total,
                })

@settings.AUTH.login_required
def vista_cargarSucesionTrenes(request, *, context):

    user_claims = context["user"]
    usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")
    foto = user_claims.get("picture")

    base_qs = (
        Sucesion.objects
        .select_related('empleado', 'horario')
        .only(
            'nombre', 'codigo', 'codigo_horario', 'fecha',
            'estado_sucesion', 'usuario_carga',
            'empleado__cargo',
            'horario__inilugar', 'horario__finallugar',
            'horario__inihora', 'horario__finalhora', 'horario__observaciones',
        )
    )

    # Por defecto mostramos sólo revisión
    sucesion_mas_particularidades = base_qs.filter(estado_sucesion="revision")

    # Inits
    total_cuadroServicios = total_cuadroServiciosSabado = None
    total_cuadroServiciosDomingo = total_cuadroServiciosEspecial = None
    erroresSabados = erroresSemana = erroresDomingos = erroresEspecial = None
    resultadosCargarSucesion = None
    errores = []

    if request.method == 'POST':
        form = CargarDocumentosForm(request.POST, request.FILES)
        accion = request.POST.get('action')

        if accion == "cargar" and form.is_valid():
            file_cuadro = form.cleaned_data.get('file_cuadroServicios')
            file_cuadroServiciosSabado = form.cleaned_data.get('file_cuadroServiciosSabado')
            file_cuadroServiciosDomingo = form.cleaned_data.get('file_cuadroServiciosDomingo')
            file_cuadroServiciosEspecial = form.cleaned_data.get('file_cuadroServiciosEspecial')
            file_sucesion = form.cleaned_data.get('file_sucesion')

            if not any((file_cuadro, file_cuadroServiciosSabado, file_cuadroServiciosDomingo, file_cuadroServiciosEspecial, file_sucesion)):
                form.add_error(None, "Debe cargar al menos un archivo para procesar.")
            else:
                if file_cuadro and validarExcel(file_cuadro):
                    total_cuadroServicios, erroresSemana = procesar_cuadro_turnos(file_cuadro, usuarioLogeado)

                if file_cuadroServiciosSabado and validarExcel(file_cuadroServiciosSabado):
                    total_cuadroServiciosSabado, erroresSabados = procesar_cuadro_turnos(file_cuadroServiciosSabado, usuarioLogeado)

                if file_cuadroServiciosDomingo and validarExcel(file_cuadroServiciosDomingo):
                    total_cuadroServiciosDomingo, erroresDomingos = procesar_cuadro_turnos(file_cuadroServiciosDomingo, usuarioLogeado)

                if file_cuadroServiciosEspecial and validarExcel(file_cuadroServiciosEspecial):
                    total_cuadroServiciosEspecial, erroresEspecial = procesar_cuadro_turnos(file_cuadroServiciosEspecial, usuarioLogeado)

                if file_sucesion and validarExcel(file_sucesion):
                    total_sucesion, errores = procesar_sucesion_multifila(file_sucesion, usuarioLogeado)
                    resultadosCargarSucesion = f"Se cargaron correctamente {total_sucesion} registros."

                sucesion_mas_particularidades = base_qs.filter(estado_sucesion="revision")

        elif accion == "publicar":
            Sucesion.objects.filter(estado_sucesion="revision").update(estado_sucesion='publicado')
            return redirect('vista_cargarSucesionTrenes')
    else:
        form = CargarDocumentosForm()

    return render(request, 'account/cargar_horario_sucesion.html', {
        'section': 'admin_gestion',
        'form': form,
        'resultadosCuadro': total_cuadroServicios,
        'resultadosCuadroSabados': total_cuadroServiciosSabado,
        'resultadosCuadroDomingo': total_cuadroServiciosDomingo,
        'resultadoCuadroEspecial': total_cuadroServiciosEspecial,
        'resultadosSucesion': resultadosCargarSucesion,
        'usuarioLogeado': usuarioLogeado,
        'datos_sucesion': sucesion_mas_particularidades,
        'erroresSemana':erroresSemana,
        'erroresSabados': erroresSabados,
        'erroresDomingos':erroresDomingos,
        'erroresEspecial':erroresEspecial,
        'success':True })

@settings.AUTH.login_required
def vista_configuraciones(request,*, context):

    user_claims = context["user"]               
    usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")

    if request.method == "GET":
        parametrosGestionTurnos = Parametros.objects.all()
        estadosServicios = Estados_servicios.objects.all()
        return render(request, 'account/configuraciones.html',{
            "parametrosGestionTurnos": parametrosGestionTurnos,
            "estadosServicios": estadosServicios,
            "usuarioLogeado": usuarioLogeado
        })
    else:
        return Response({"success":False , "message":"Error de peticion"})
        

@settings.AUTH.login_required
def get_solicitudes_cambios_turnos(request,*, context):
    fecha = request.GET.get('fecha')
    cargaDatos = None
    cargarDatosSolicitudes = None
    user_claims = context["user"]               
    usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")

    if request.method == "GET" and fecha: 
        if Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = fecha).exists():
            cargarDatosSolicitudes =  Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = fecha)
            cargaDatos = "ok"
        else:
            cargarDatosSolicitudes = None
            cargaDatos = "error"

        #fechaSolicitudes = timezone.localdate(timezone=ZoneInfo("America/Bogota")) + timedelta(days=1)
        # cargarDatosSolicitudes =  Cambios_de_turnos.objects.filter(fecha_solicitud_cambio= fechaSolicitudes)
    return render(request,'account/cambios_turnos.html',{
        'resultadosCambiosTurnos':cargarDatosSolicitudes,
        'usuarioLogeado':usuarioLogeado,
        'cargaDatos': cargaDatos
        })
    
@settings.AUTH.login_required
def editar_horario(request,*, context):

    horarioNombre = request.POST.get('horario')
    fechavigencia = request.POST.get('fechavigencia')
    fecha_carga = request.POST.get('fecha_carga')

    print(f"horario: {horarioNombre}, fecha vigencia: {fechavigencia}, fecha carga: {fecha_carga}")

    if request.method == "POST":
        if all([horarioNombre, fechavigencia, fecha_carga]):
        
            turnos_por_horario = Horario.objects.all().filter(horario=horarioNombre, fechavigencia=fechavigencia, fecha_carga= fecha_carga)

            return render(request,"account/editarHorario.html",{
                'turnos_por_horario':turnos_por_horario
            })
    return redirect('home')


@settings.AUTH.login_required
def vista_cargarIo(request,*, context):

    if request.method == "GET":
        user_claims = context["user"]               
        usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")
        return render(request,'account/cargar_instrucciones_operacionales.html',{
            "usuarioLogeado": usuarioLogeado
        })
    
#Vista solcitudes de GT  - > Rango por fechas
@settings.AUTH.login_required
def vista_solicitudes_gestion_turnos(request,*, context):
    
    user_claims = context["user"]
    usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")

    hoy = date.today()
    inicio = date(hoy.year, 1, 1) #Primer dia del año

    if request.method == "GET":

        fechaInicial_peticion = request.GET.get('fecha_inicio')
        fechaFinal_peticion = request.GET.get('fecha_fin')

        fechaInicial = None
        fechaFinal = None
    
        if fechaInicial_peticion and fechaFinal_peticion:
            #Formateamos las fechas para que evitar error de formato ---> Datetime
            fechaInicial = datetime.strptime(fechaInicial_peticion, "%Y-%m-%d").date()
            fechaFinal = datetime.strptime(fechaFinal_peticion, "%Y-%m-%d").date()

            #print(f"fecha inicial {fechaInicial} fecha final: {fechaFinal}") 
            
            if Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal).exists():

                solicitudesGt = Solicitudes_Gt.objects.select_related('empleado').filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal).order_by('fecha_inicial')
                #print(f"solicitudes sin relacion ::: {Solicitudes_Gt.objects.filter(empleado__isnull=False).count()}")
                indicadorTotal = solicitudesGt.count()
                indicadorPendiente = Solicitudes_Gt.objects.filter((Q(fecha_inicial__gte = fechaInicial) & Q(fecha_final__lte = fechaFinal)), estado = "pendiente").count()
                indicadorAprobada = Solicitudes_Gt.objects.filter((Q(fecha_inicial__gte = fechaInicial) & Q(fecha_final__lte = fechaFinal)), estado = "aprobado").count()
                indicadorDesaprobado = Solicitudes_Gt.objects.filter((Q(fecha_inicial__gte = fechaInicial) & Q(fecha_final__lte = fechaFinal)), estado = "desaprobado").count()
                indicadorDesatendida = Solicitudes_Gt.objects.filter((Q(fecha_inicial__gte = fechaInicial) & Q(fecha_final__lte = fechaFinal)), estado = "desatendida").count()
                print(f" DESATENDIDAS:: {indicadorDesatendida}")

                #print("Si existen solicitudes entre estas fechas")
                return render(request,"account/solicitudes_gestion_turnos.html",{
                    "mensaje":f"Se cargaron: {indicadorTotal} solicitudes entre: {fechaInicial} , {fechaFinal} \nPendientes: {indicadorPendiente} - Aprobadas: {indicadorAprobada} - Desaprobadas: {indicadorDesaprobado} ",
                    "solicitudesGt":solicitudesGt,
                    "usuarioLogeado":usuarioLogeado,
                    "solicitudAnual": indicadorTotal,
                    "solicitudAnualAprobadas":indicadorAprobada,
                    "solicitudAnualPendientes":indicadorPendiente,
                    "solicitudAnualDesaprobadas":indicadorDesaprobado,
                    "SolicitudDesatendida": indicadorDesatendida
                })
            else: # Si no ingresa un rango de fechas donde existan solicitudes, no se devuelve nada
                solicitudAnual = 0
                solicitudAnualAprobadas = 0
                solicitudAnualPendientes = 0
                solicitudAnualDesaprobadas = 0
                indicadorDesatendida = 0
                return render(request, "account/solicitudes_gestion_turnos.html",{
                    "mensaje:":f"No hay solicitudes para este rango de fechas: {fechaInicial} , {fechaFinal}",
                     "usuarioLogeado":usuarioLogeado,
                     "solicitudAnual": solicitudAnual,
                     "solicitudAnualAprobadas": solicitudAnualAprobadas,
                     "solicitudAnualPendientes": solicitudAnualPendientes,
                     "solicitudAnualDesaprobadas":solicitudAnualDesaprobadas,
                     "SolicitudDesatendida": indicadorDesatendida

                })
        else:
            solicitudAnual = 0
            solicitudAnualAprobadas = 0
            solicitudAnualPendientes = 0
            solicitudAnualDesaprobadas = 0
            indicadorDesatendida = 0

            return render(request,"account/solicitudes_gestion_turnos.html",{
                "mensaje:":f"No hay solicitudes para este rango de fechas: {fechaInicial} , {fechaFinal}",
                "solicitudesGt":solicitudesGt,
                 "usuarioLogeado":usuarioLogeado,
                 "solicitudAnual": solicitudAnual,
                 "solicitudAnualAprobadas":solicitudAnualAprobadas,
                 "solicitudAnualPendientes": solicitudAnualPendientes,
                 "solicitudAnualDesaprobadas":solicitudAnualDesaprobadas,
                 "SolicitudDesatendida": indicadorDesatendida
            })
    else:
        return Response({
            "success":False,
            "message":"Peticion invalida"
        })

@settings.AUTH.login_required
def vista_verificacion(request, context):
    if request.method == "GET":
        user_claims = context["user"]               
        usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")
        fecha = request.GET.get('fecha')
        cargo = request.GET.get('cargo')
        if fecha and cargo:
            if Sucesion.objects.filter(fecha = fecha, cargo = cargo).exists():

                sucesion = Sucesion.objects.filter( fecha = fecha, cargo = cargo).select_related('horario').order_by('hora_inicio')
                return render(request, "account/verificacion.html",{
                    "sucesion": sucesion,
                    "usuarioLogeado": usuarioLogeado,
                    "success": True
                })
            else:
                return render(request, "account/verificacion.html",{
                    "usuarioLogeado": usuarioLogeado,
                    "success": False
                })

@settings.AUTH.login_required
def vista_notificaciones(request,*, context):

    if request.method == "GET":
        user_claims = context["user"]               
        usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")
        notificaciones = Notificaciones.objects.select_related('empleado','solicitudes_Gt').order_by('id')
        return render(request,"account/notificaciones.html",{
            "notificaciones": notificaciones,
            "usuarioLogeado": usuarioLogeado
        })

# views.py
@settings.AUTH.login_required
def vista_precarga(request, *, context):
    
    user_claims = context["user"]               
    usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")
   
    if request.method == "GET":
        return render(request, "account/preCarga.html", {
            "form": CargarDatosProno(),
            "dfresultado": None,
            "usuarioLogeado": usuarioLogeado
        })

    form = CargarDatosProno(request.POST, request.FILES)

    if not form.is_valid():
        return render(request, "account/preCarga.html", {
            "form": form,
            "dfresultado": None,
            "error": "Formulario inválido",
            "usuarioLogeado": usuarioLogeado
        })

    f = form.cleaned_data["file_cargarDatosProno"]
    if not validarExcel(f):
        return render(request, "account/preCarga.html", {
            "form": form,
            "dfresultado": None,
            "error": "Excel no válido",
            "usuarioLogeado": usuarioLogeado
        })

    sobreCargaLaboralTrenes = sobreCargaLaboral(f) 
    #sobreCargaTranvia = sobreCargaLaboralTranvia(f)


    serviciosRepetidos, faltantes_lunes_viernes, faltantes_sabado_json, faltantes_domingo_json = asignacionServicios(f) 
    serviciosRepetidosTranvia, faltantes_lunes_viernesTranvia, faltantes_sabado_jsonTranvia, faltantes_domingo_jsonTranvia = asignacionServiciosTranvia(f) 
   
    return render(request, "account/preCarga.html", {
        "form": form,
        "dfresultado": sobreCargaLaboralTrenes,
        #"sobreCargaLaboralTranvia": sobreCargaTranvia,
        "usuarioLogeado": usuarioLogeado,
        "serviciosRepetidos": serviciosRepetidos,
        "faltantes_lunes_viernes": faltantes_lunes_viernes,
        "faltantes_sabado_json": faltantes_sabado_json,
        "faltantes_domingo_json": faltantes_domingo_json,
        "serviciosRepetidosTranvia" : serviciosRepetidosTranvia,
        "faltantes_lunes_viernesTranvia": faltantes_lunes_viernesTranvia,
        "faltantes_sabado_jsonTranvia": faltantes_sabado_jsonTranvia,
        "faltantes_domingo_jsonTranvia": faltantes_domingo_jsonTranvia,
        
    })

# [ ------ API ------]

@api_view(["GET"])
def get_archivos_solicitudesgt(request):

    idSolicitud = request.GET.get("idSolicitud")
    print(idSolicitud)
    solicitud = Solicitudes_Gt.objects.get(id =idSolicitud)
    return Response({"success":True, "url":solicitud.urlArchivo, "tipoArchivo": solicitud.tipoArchivo})

#Devulve los datos del turno consultado, usa como parametro el codigo de turno para devolver los datos, este GET es para el modal editar en cargar sucesion
@api_view(["GET"])
def consultar_turno(request):
    codigoTurno = request.GET.get('codigo')
    print(f"Codigo extraido: {codigoTurno}")
    if not codigoTurno:
        return Response({"error": "Se requiere el parámetro 'codigo'"}, status=400)
    
    turnoConsultado = Horario.objects.filter(turno = codigoTurno)
    data=[]
    for t in turnoConsultado:
        data.append({
            "inicir":t.inicir,
            "finbalcir": t.finbalcir,
            "inihora": t.inihora,
            "finalhora": t.finalhora,
            "inilugar": t.inilugar,
            "finallugar": t.finallugar,
            "observaciones": t.observaciones
        })
    return Response(data)


@api_view(["POST"])
def gestionarSolicitudeGt(request):
    print("accedio a la vista")
    hoy = datetime.now(ZoneInfo("America/Bogota"))

    idSolicitud = request.data.get("idSolicitud")
    estadoSolicitud = request.data.get("estadoSolicitud")
    respuestaEstado = request.data.get("respuestaEstado")

    if idSolicitud and estadoSolicitud:
        print(respuestaEstado)
        
        solicitud = Solicitudes_Gt.objects.get(id = idSolicitud)
        solicitud.estado = estadoSolicitud
        solicitud.save(update_fields=["estado"])
        Respuesta_Solicitudes_Gt.objects.create(solicitud = solicitud, respuesta = respuestaEstado, fechaRespuesta = hoy)

        if estadoSolicitud in ["aprobado", "desaprobado"]:
            asunto = f"Solicitud de Gestión de turnos - solicitud: {solicitud.tipo_solicitud}" #solicitud.empleado.correo
            estadoEnvioCorreo = enviarCorreoGmailHTML("sbastianpp@gmail.com", solicitud.empleado.nombre, solicitud.tipo_solicitud, solicitud.fecha_solicitud, asunto, estado = estadoSolicitud)

        return Response({
            "success":True,
            "message": f"Se gestiono correctamente la solicitud con id: {idSolicitud} y su nuevo estado es: {estadoSolicitud}"
        })
    return Response({
        "success":False,
        "message":"No se recepciono un id valido, verifique"
    })    
    
@api_view(["POST"])
def cargar_Io(request):

    print("POST KEYS:", request.POST.keys())
    print("FILES KEYS:", request.FILES.keys())
    print("FILES OBJ:", request.FILES)

    if request is not None :

        titulo = request.data['tituloComunicado']
        tipoComunicado = request.data['tipoComunicado']
        print(request.data['fechaVigenciaCargar'])
        fechaVigencia = request.data['fechaVigenciaCargar'] if request.data['fechaVigenciaCargar'] else None
        cargoVisualizacion = request.data['cargos']
        usuarioLogeado = request.data['usuarioLogeado']
        tipoArchivo = request.data['tipoArchivo']
        

        comunicado =  Archivos.objects.create(titulo = titulo,  usuarioCarga = usuarioLogeado, fechaVigencia = fechaVigencia,
                                tipoComunicado = tipoComunicado, 
                                cargoVisualizacion = cargoVisualizacion)
        comunicado.id
        print(comunicado.id)
        nombreComunicado = f"{tipoComunicado}_{comunicado.id}"
        print(nombreComunicado)
        
        urlArchivo = upload_to_azure_blob(request.FILES['archivoCargar'], nombreComunicado, "comunicaciones")
        Archivos.objects.filter(id = comunicado.id).update(urlArchivo = urlArchivo, tipoArchivo = tipoArchivo)

        return Response({"success":True, "message": f"Se cargo correctamente el archivo con id: {nombreComunicado}, usuario que carga: {usuarioLogeado}"})
    
    else:
        return Response({"success":False, "message":"No se cargo ningún archivo"})    
    

#---------------------------- ENDPOINTS FRONT -------------------------------------------------]
#Consulta: http://localhost:8000/account/api/mis-turnos/?codigo=
#Trae los turnos del conductor usando como parametro el codigo, este endpoint es para el conductor logeado
@api_view(["GET"])
def get_mis_turnos(request):

    codigo = request.GET.get('codigo')
    fechaInicial = request.GET.get("fechaInicial")
    fechaFinal = request.GET.get('fechaFinal')
    cedula = request.GET.get('cedula')

    if not codigo and not fechaInicial and not fechaFinal and not cedula:
        return Response({"success":True, "message": f"Error de parametros, codigo: {codigo}, fecha incial: {fechaInicial}, fecha final {fechaFinal}, cedula: {cedula}"})
    
    try:
        turnos  = Sucesion.objects.filter((Q(fecha__gte = fechaInicial) & Q(fecha__lte = fechaFinal)), codigo = codigo, cedula = cedula, estado_sucesion = "publicado" ).order_by('fecha')
    except Sucesion.DoesNotExist:
        return Response({"success":False, "message":f"Para este rango de fechas no fue posible cargar la sucesión"})

    data = []
    for t in turnos:
        data.append({
            "fecha":t.fecha,
            "turno":t.codigo_horario,
            "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
            "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
            "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
            "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
            "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
            "duracion":t.horario.duracion if t.horario and t.horario.duracion else "" 
        })

    if len(data)> 1:
        print(f"Data tiene datos {data}")

    return Response(data)


#Devulve todos lo empleados con cargo: Conductor de trenes
#Consulta: http://localhost:8000/account/api/sucesion/?cargo=CONDUCTOR DE VEHICULOS DE PASAJEROS TIPO METRO
@api_view(["GET"])
def get_sucesion_cargo(request):
    
    cargo = request.GET.get('cargo').strip()
    fechaInicial = request.GET.get("fechaInicio")
    fechaFinal = request.GET.get("fechaFinal")

    #print(f" cargo: {cargo}, fechaIni: {fechaInicial}, fechafin: {fechaFinal}")

    if not cargo:
        return Response({"Error":"Parametro cargo es requerido"}, status=400)
    
    turnos = Sucesion.objects.filter((Q(fecha__gte = fechaInicial) & Q(fecha__lte = fechaFinal)) , cargo= cargo, empleado__estado = "Activo", estado_sucesion = "publicado").distinct()

    data = []
    for t in turnos:
        data.append({
            "foto": t.empleado.foto,
            "nombre":t.nombre,
            "codigo":t.codigo,
            "fecha":t.fecha,
            "turno":t.codigo_horario,
            "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
            "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
            "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
            "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
            "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
            "duracion":t.horario.duracion if t.horario and t.horario.duracion else "00:00" 
        })
    return Response({"success":True, "data":data})

#Esta vista actualiza los detalles de un turno en el modelo Horario, por ejemplo: COD SRM548 -> modifica hora de inicio, final, estacion inicial, final y particularidades
@api_view(["POST"])
def actualizar_turno(request):

    data = request.data

    turnoOriginal = data.get("turnoOriginal")
    turno = data.get("turno")
    codigo = data.get("codigo")
    fecha = data.get("fecha")
    peticion = request.data.get('peticion')

    if not turno:
        return Response({"Success":False,
                         "message":f"No se encontro codigo"}, status=400)
    
    if peticion == "accesoRapido":
        print(peticion)

        horario_relacion = Horario.objects.filter(turno = turno)

        Sucesion.objects.filter(fecha = fecha, codigo = codigo, codigo_horario = turnoOriginal).update(codigo_horario = turno,horario = horario_relacion, 
                estado_inicio = data.get("inilugar"),estado_fin = data.get("inilugar"), 
                hora_inicio = data.get("inihora"), hora_fin = data.get("finalhora"))

        return Response({
            "success":True,
            "message": f"Turno: {turno}, actualizado correctamente"
        })
    
    elif peticion =="editarHorario":
        print(peticion)
        horario = get_object_or_404(Horario, turno=turno)  
        
        horario.inilugar = data.get('inilugar') 
        horario.finallugar = data.get('finallugar')
        horario.inihora = data.get('inihora')
        horario.finalhora = data.get('finalhora')
        horario.inicir = data.get('circulacionIni')
        horario.finbalcir =  data.get('circulacionFin')
        horario.duracion = data.get('duracion')
        horario.observaciones = data.get('observaciones')
        horario.save()

        Sucesion.objects.filter(codigo_horario = turno).update(estado_inicio = data.get('inilugar'), estado_fin = data.get('finallugar'), hora_inicio = data.get('inihora'), hora_fin = data.get('finalhora'))

        return Response({
            "success":True,
            "message": f"Turno: {turno}, actualizado correctamente"
        })

    return Response({
            "success":False,
            "message": "No se reconoce la petición"
        })
#-------------------------------------------------------------------------------------------]

#Esta vista permite agrupar los horarios y devolverlos en orden de fecha de carga, Modal editar
@api_view(["GET"])
def traer_horarios(request):
    if request.method == "GET":

        horariosRecientes = Horario.objects.values('horario','fechavigencia','fecha_carga').annotate(numeroDatos = Count('id')).order_by('-fechavigencia').filter(numeroDatos__gt=1)
        data = []
        for h in horariosRecientes:
            data.append({
                "horario" : h['horario'],
                "fechavigencia": h['fechavigencia'].strftime('%Y-%m-%d') if h['fechavigencia'] else '',
                "fecha_carga": h['fecha_carga'].strftime(('%Y-%m-%d')) if h['fecha_carga'] else '',
                "numeroDatos": h['numeroDatos']
            })
        return Response({"horarios":data})
    return  Response({"error":"acceso denegado"}, status=400 )

# Modal Editar-Eliminar
# Esta vista recibe como parametros nombre del horario, fecha de vigencia y fecha de carga para poder eliminar todos los registros asociados - Modal editar

# [Modal editar horario - template: editarHorario.html] Esta vista permite insertar un turno dentro del modelo Horario, esta vista se ejecuta desde la vista editarHoratio.html
@api_view(["POST"])
def insertar_horario(request):
    if request.method == "POST":
        
        horario = request.data.get('horario')
        fechavigencia = request.data.get('fechavigencia')
        fecha_carga = request.data.get('fecha_carga')
        fechaimplementacion= request.data.get('fechaimplementacion')
        version = request.data.get('version')
        turno = request.data.get('turno')
        inilugar = request.data.get('inilugar')
        finallugar = request.data.get('finallugar')
        inihora = request.data.get('inihora')
        finalhora = request.data.get('finalhora')
        inicir = request.data.get('inicir')
        finbalcir = request.data.get('finbalcir')
        duracion = request.data.get('duracion')
        observaciones = request.data.get('observaciones')
        
        print(f"Fecha de carga: {fecha_carga}")
        if Horario.objects.filter(horario=horario, fechavigencia=fechavigencia,fecha_carga= fecha_carga,turno=turno).exists():
            return Response({
            "Sucess":False,
            "message": f"Este codigo de turno: {turno}, ya se encuentra registrado para el horario: {horario} y vigencia de: {fechavigencia}"
        })
        else:
            Horario.objects.create(horario=horario,fechavigencia= fechavigencia, fechaimplementacion = fechaimplementacion, fecha_carga= fecha_carga, version = version, turno=turno,inilugar = inilugar,
                                finallugar=finallugar, inihora=inihora, finalhora = finalhora, inicir = inicir, finbalcir = finbalcir ,duracion=duracion, observaciones= observaciones)
            return Response({
                "success": True,            
                "message" : f"Se inserto con exito el turno: {turno}" 
                })
        
    return Response({
        "Success": False,
        "message": "Eror al insertar el turno:"
    })
    
#[Modal horarios cargados - template: sucesiones_trenes.html]
@api_view(["POST"])
def eliminar_horario(request):
    
    if request.method == "POST":
        print(f"Horario: {request.data.get('horario')}")
        horario = request.data.get('horario')
        fechaVigencia = request.data.get('fechavigencia')
        fechaCarga = request.data.get('fecha_carga')

        horarioRelacion = Horario.objects.filter(horario= horario, fechavigencia= fechaVigencia, fecha_carga = fechaCarga).first()

        if not horarioRelacion:
            return Response({"error": "Horario no encontrado"}, status=404)
        
        relacion = Sucesion.objects.filter(horario=horarioRelacion).exists()
        if relacion:
            return Response({
                "success": False,
                "message": "No se puede eliminar. El horario tiene datos relacionados en Sucesión."
            })
        
        Horario.objects.filter(horario=horario, fechavigencia= fechaVigencia, fecha_carga = fechaCarga).delete()
        return Response({
            "success": True,
            "message": f"Se eliminó el horario: {horario}, {fechaVigencia}, {fechaCarga}"
        })

    return Response({"error": "Solicitud no válida"}, status=400)
        

@api_view(["GET"])
def buscar_cambio_turno(request):

    codigoSolicitante = request.GET.get('codigoSolicitante') #Formato para la fecha: Y/m/d
    fechaCambio = datetime.strptime(request.GET.get('fechaCambio'),"%Y/%m/%d")

    
    if not Sucesion.objects.filter(codigo = codigoSolicitante, fecha = fechaCambio, estado_sucesion = "publicado").exists():
        return Response({"success":False, "message": f"Para esta fecha: {fechaCambio} no hay sucesión cargada"})

    #horaActual = datetime.now().time()
    horaActual = datetime.now(ZoneInfo("America/Bogota")).time()
    parametros = Parametros.objects.first()
    horaInicial = parametros.hora_inicio_permitida_cambios
    horaFinal = parametros.hora_final_permitida_cambios

    print(f"Hora actual: {horaActual}, hora incial: {horaInicial} , hora final:{horaFinal}")

    #Validacion de horas seegun el modelo Parametros

    if horaActual < horaInicial:
        return Response({
            "success":False,
            "message":f"Estas intentando realizar una solicitud de cambio por fuera del horario establecido entre: {horaInicial} y {horaFinal}, hora actual: {horaActual}"
        })
    
    if horaActual > horaFinal:
        return Response({
            "success":False,
            "message":f"Estas intentando realizar una solicitud de cambio por fuera del horario establecido entre: {horaInicial} y {horaFinal}, hora actual: {horaActual}"
        })

    fechaAnterior =  fechaCambio - timedelta(days=1)
    fechaPosterior = fechaCambio + timedelta(days=1)

    print(f"FECHA POSTERIROR AL CAMBIO: {fechaPosterior}")

    empleado = Empleado_Oddo.objects.filter(codigo=codigoSolicitante , estado = "Activo").first()
    print(f"Codigo del empleado: { empleado.codigo}")


    #crear en configuraciones
    cargos10HorasDescanso = ["CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO","CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO TRANVIA"]
    cargos8HorasDescanso = ["OPERADOR(A) DE CONDUCCION","MANIOBRISTA TRENES","MANIOBRISTA TRANVIA"]

    estadosServicios = Estados_servicios.objects.all()
    turnosInvalidados =  []

    sucesionSolicitanteDiaCambio =  get_object_or_404(Sucesion, codigo = codigoSolicitante , fecha = fechaCambio)
    # Turnos que no se pueden cambiar:
    for e in estadosServicios:
        turnosInvalidados.append(e.estado) #["LIBRE","COMPE","CP","INCAPACI","SUSPENSI","CAFTA","MAN","FUNDA" "LICENCIA"]

    #Aca validamos que el turno no sea invalido para cambiar
    if sucesionSolicitanteDiaCambio.codigo_horario in turnosInvalidados:
        return Response({
            "success":False,
             "message": f"{sucesionSolicitanteDiaCambio.nombre}, No es posible cambiar dias LIBRE, COMPE, CP, INCAPACI, SUSPENSI , CAFTA , MAN , FUNDA, VACACION"
        })

    if Sucesion.objects.filter(codigo = codigoSolicitante, fecha = fechaPosterior).exists():
        sucesionSolicitanteDiaPosterior = Sucesion.objects.filter(codigo = codigoSolicitante, fecha = fechaPosterior).first()
        if sucesionSolicitanteDiaPosterior.hora_inicio is not None:
            sucesionSolicitanteDiaPosterior_horaIni = sucesionSolicitanteDiaPosterior.hora_inicio
    else:
        sucesionSolicitanteDiaPosterior = None
        sucesionSolicitanteDiaPosterior_horaIni =  None

    horaInicioDiaPosteriorCambio10Hrs = None
    horaInicioDiaPosteriorCambio8Hrs = None

    
    if sucesionSolicitanteDiaPosterior is not None:               #Aca validamos si es DISPO, FUNDA ETC
        if sucesionSolicitanteDiaPosterior.hora_inicio:
            horaInicioDiaPosteriorCambio10Hrs = datetime.combine(fechaPosterior,sucesionSolicitanteDiaPosterior.hora_inicio)
            print(f"Calculo incial de la hora incio posterior: {horaInicioDiaPosteriorCambio10Hrs}")
            horaInicioDiaPosteriorCambio8Hrs = datetime.combine(fechaPosterior,sucesionSolicitanteDiaPosterior.hora_inicio)

            horaInicioDiaPosteriorCambio10Hrs = horaInicioDiaPosteriorCambio10Hrs - timedelta(hours=10)   
            print(f"Calculo final de la hora incio posterior: {horaInicioDiaPosteriorCambio10Hrs}")
            horaInicioDiaPosteriorCambio8Hrs = horaInicioDiaPosteriorCambio8Hrs - timedelta(hours=8)  

            print(f" DIA POSTERIOR - 10 horas: {horaInicioDiaPosteriorCambio10Hrs.time()}")
    
    SusecionEmpleadoDiaAnterior = Sucesion.objects.filter(codigo = codigoSolicitante , fecha = fechaAnterior).first()
    print(f"Codigo turno dia anteriror : {SusecionEmpleadoDiaAnterior.codigo_horario}")
    sucesionFiltrada = []
  
    if empleado.cargo in cargos10HorasDescanso:
        #SusecionEmpleadoDiaAnterior.codigo_horario not in ["DISPO", "LIBRE","COMPE","CP"] or SusecionEmpleadoDiaAnterior.codigo_horario not in turnosInvalidados and sucesionSolicitanteDiaPosterior.hora_inicio is not None:
        if SusecionEmpleadoDiaAnterior.hora_inicio is not None and sucesionSolicitanteDiaPosterior_horaIni is not None: 
            print("CASO: TURNO -  X - TURNO")
            #CASO 888DDD - X - 888DDD
            # NO ES DISPO, LIBRE, FUNDA O TURNOS INVALIDOS NI EL TURNO ANTERIOR Y POSTERIROR - CONDUCTOR TRENES
            horaFinalTurnoAnterior = datetime.combine(fechaAnterior, SusecionEmpleadoDiaAnterior.hora_fin) # Aca tenemos tanto la fecha, como la hora para calular las 10 despues
            horaFinalTurnoAnterior = horaFinalTurnoAnterior + timedelta(hours=10)

            sucesionDiaCambio = (Sucesion.objects.select_related('empleado').annotate(inicio_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_inicio"), 
                                        output_field=DateTimeField(),
                                        ), 
                                        fin_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_fin"), 
                                        output_field=DateTimeField(),
                                        ),
                                        ).filter(Q(fecha = fechaCambio), Q(empleado__cargo = empleado.cargo), ~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante),
                                        (Q(codigo_horario__in = ["DISPO"])) | (Q(inicio_cambio__gte = horaFinalTurnoAnterior) & Q(fin_cambio__lte = horaInicioDiaPosteriorCambio10Hrs))))
            
            for t in sucesionDiaCambio:
                sucesionFiltrada.append({
                            "foto": t.empleado.foto,
                            "nombre":t.nombre,
                            "codigo":t.codigo,
                            "cargo":t.empleado.cargo,
                            "fecha":t.fecha,
                            "turno":t.codigo_horario,
                            "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
                            "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
                            "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
                            "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
                            "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
                            "duracion":t.horario.duracion if t.horario and t.horario.duracion else "Sin duración" 
                                })
            return Response(sucesionFiltrada)
        #CASO DISPO - X - 888DDD
        #ACA TENEMOS EL CASO SI EL DIA ANTERIROR TIENE DISPO O CUALQUIER TURNO QUE NO TENGA HORA DE INCIO - HORA FIN, ASI NO CALCULAMOS LAS 10HRS DESPUES
        elif SusecionEmpleadoDiaAnterior.hora_inicio is None and sucesionSolicitanteDiaPosterior_horaIni is not None:
            print("CASO: DISPO -  X - TURNO") #ACA NO SE CALCULA LAS 10 HORAS DE DESCANSO CON EL TURNO ANTERIOR PORQUE ES UN::::::::::::::::: DISPO
            sucesionDiaCambio = (Sucesion.objects.select_related('empleado').annotate(fin_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_fin"), 
                                        output_field=DateTimeField(),
                                        ),
                                        ).filter(Q(fecha = fechaCambio), Q(empleado__cargo = empleado.cargo), ~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante),
                                        (Q(codigo_horario__in = ["DISPO"])) | (Q(fin_cambio__lte = horaInicioDiaPosteriorCambio10Hrs))))
            for t in sucesionDiaCambio:
                sucesionFiltrada.append({
                                "foto":t.empleado.foto,
                                "nombre":t.nombre,
                                "codigo":t.codigo,
                                "cargo":t.empleado.cargo,
                                "fecha":t.fecha,
                                "turno":t.codigo_horario,
                                "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
                                "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
                                "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
                                "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
                                "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
                                "duracion":t.horario.duracion if t.horario and t.horario.duracion else "Sin duración" 
                                    })
            return Response(sucesionFiltrada)
        elif SusecionEmpleadoDiaAnterior.hora_inicio is not None and sucesionSolicitanteDiaPosterior_horaIni is None:
            print("CASO: TURNO -  X - DISPO")

            horaFinalTurnoAnterior = datetime.combine(fechaAnterior, SusecionEmpleadoDiaAnterior.hora_fin) 
            horaFinalTurnoAnterior = horaFinalTurnoAnterior + timedelta(hours=10)

            if sucesionSolicitanteDiaPosterior is not None:
                sucesionDiaCambio = (Sucesion.objects.select_related('empleado').annotate(inicio_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_inicio"), 
                                        output_field=DateTimeField(),
                                        ),
                                        ).filter(Q(fecha = fechaCambio), Q(empleado__cargo = empleado.cargo), ~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante),
                                        (Q(codigo_horario__in = ["DISPO"])) | (Q(inicio_cambio__gte = horaFinalTurnoAnterior))))
            else:
                print("Sin sucesion del dia siguiente")
                sucesionDiaCambio = (Sucesion.objects.select_related('empleado').annotate(inicio_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_inicio"), 
                                        output_field=DateTimeField(),
                                        ),
                                        ).filter(Q(fecha = fechaCambio), Q(empleado__cargo = empleado.cargo), ~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante),
                                        (Q(codigo_horario__in = ["DISPO"])) | (Q(inicio_cambio__gte = horaFinalTurnoAnterior))))

            for t in sucesionDiaCambio:
                sucesionFiltrada.append({
                                "foto":t.empleado.foto,
                                "nombre":t.nombre,
                                "codigo":t.codigo,
                                "cargo":t.empleado.cargo,
                                "fecha":t.fecha,
                                "turno":t.codigo_horario,
                                "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
                                "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
                                "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
                                "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
                                "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
                                "duracion":t.horario.duracion if t.horario and t.horario.duracion else "Sin duración" 
                                    })
            return Response(sucesionFiltrada)
        elif SusecionEmpleadoDiaAnterior.hora_inicio is None :
            print("CASO: DISPO - X - DISPO ")
            sucesionDiaCambio = Sucesion.objects.select_related("empleado").filter(~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante), fecha = fechaCambio, empleado__cargo = empleado.cargo)
            for t in sucesionDiaCambio:
                sucesionFiltrada.append({
                                "foto":t.empleado.foto,
                                "nombre":t.nombre,
                                "codigo":t.codigo,
                                "cargo":t.empleado.cargo,
                                "fecha":t.fecha,
                                "turno":t.codigo_horario,
                                "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
                                "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
                                "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
                                "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
                                "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
                                "duracion":t.horario.duracion if t.horario and t.horario.duracion else "Sin duración"
                })
            return Response(sucesionFiltrada)
        
    elif empleado.cargo in cargos8HorasDescanso:
        
        if SusecionEmpleadoDiaAnterior.hora_inicio is not None and sucesionSolicitanteDiaPosterior_horaIni is not None:
            print("CASO: TURNO -  X - TURNO ")
            #CASO 888DDD - X - 888DDD
            # NO ES DISPO, LIBRE, FUNDA O TURNOS INVALIDOS NI EL TURNO ANTERIOR Y POSTERIROR - CONDUCTOR TRENES

            horaFinalTurnoAnterior = datetime.combine(fechaAnterior, SusecionEmpleadoDiaAnterior.hora_fin) # Aca tenemos tanto la fecha, como la hora para calular las 10 despues
            horaFinalTurnoAnterior = horaFinalTurnoAnterior + timedelta(hours=8)
            horaInicioDiaPosteriorCambio8Hrs

            sucesionDiaCambio = (Sucesion.objects.annotate(inicio_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_inicio"), 
                                    output_field=DateTimeField(),
                                    ), 
                                    fin_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_fin"), 
                                    output_field=DateTimeField(),
                                    ),
                                    ).filter(Q(fecha = fechaCambio), Q(empleado__cargo = empleado.cargo), ~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante),
                                    (Q(codigo_horario__in = ["DISPO"])) | (Q(inicio_cambio__gte = horaFinalTurnoAnterior) & Q(fin_cambio__lte = horaInicioDiaPosteriorCambio8Hrs))))
            for t in sucesionDiaCambio:
                sucesionFiltrada.append({
                            "nombre":t.nombre,
                            "codigo":t.codigo,
                            "cargo":t.empleado.cargo,
                            "fecha":t.fecha,
                            "turno":t.codigo_horario,
                            "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
                            "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
                            "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
                            "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
                            "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
                            "duracion":t.horario.duracion if t.horario and t.horario.duracion else "Sin duración" 
                                })
            return Response(sucesionFiltrada)
        elif SusecionEmpleadoDiaAnterior.hora_inicio is None and sucesionSolicitanteDiaPosterior_horaIni is not None:
            print("CASO: DISPO -  X - TURNO")
            print(f"Hora de inicio del dia posteriror{horaInicioDiaPosteriorCambio8Hrs}")
            sucesionDiaCambio = (Sucesion.objects.annotate(fin_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_fin"), 
                                    output_field=DateTimeField(),
                                    ),
                                    ).filter(Q(fecha = fechaCambio), Q(empleado__cargo = empleado.cargo), ~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante),
                                    (Q(codigo_horario__in = ["DISPO"])) | (Q(fin_cambio__lte = horaInicioDiaPosteriorCambio8Hrs))))
            for t in sucesionDiaCambio:
                sucesionFiltrada.append({
                                "nombre":t.nombre,
                                "codigo":t.codigo,
                                "cargo":t.empleado.cargo,
                                "fecha":t.fecha,
                                "turno":t.codigo_horario,
                                "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
                                "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
                                "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
                                "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
                                "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
                                "duracion":t.horario.duracion if t.horario and t.horario.duracion else "Sin duración" 
                                    })
            return Response(sucesionFiltrada)
        elif SusecionEmpleadoDiaAnterior.hora_inicio is not None and sucesionSolicitanteDiaPosterior_horaIni is None :
            print("CASO: TURNO -  X - DISPO")
            horaFinalTurnoAnterior = datetime.combine(fechaAnterior, SusecionEmpleadoDiaAnterior.hora_fin) 
            horaFinalTurnoAnterior = horaFinalTurnoAnterior + timedelta(hours=8)
            horaInicioDiaPosteriorCambio8Hrs

            if sucesionSolicitanteDiaPosterior is None:
                sucesionDiaCambio = (Sucesion.objects.annotate(inicio_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_inicio"), 
                                    output_field=DateTimeField(),
                                    ),
                                    ).filter(Q(fecha = fechaCambio), Q(empleado__cargo = empleado.cargo), ~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante),
                                    (Q(codigo_horario__in = ["DISPO"])) | (Q(inicio_cambio__gte = horaFinalTurnoAnterior))))
            else:
                sucesionDiaCambio = (Sucesion.objects.annotate(inicio_cambio = ExpressionWrapper(Cast(F("fecha"), DateTimeField()) + F("hora_inicio"), 
                                    output_field=DateTimeField(),
                                    ),
                                    ).filter(Q(fecha = fechaCambio), Q(empleado__cargo = empleado.cargo), ~Q(codigo_horario__in = turnosInvalidados), ~Q(codigo = codigoSolicitante),
                                    (Q(codigo_horario__in = ["DISPO"])) | (Q(inicio_cambio__gte = horaFinalTurnoAnterior))))
            
            
            for t in sucesionDiaCambio:
                sucesionFiltrada.append({
                                "nombre":t.nombre,
                                "codigo":t.codigo,
                                "cargo":t.empleado.cargo,
                                "fecha":t.fecha,
                                "turno":t.codigo_horario,
                                "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
                                "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
                                "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
                                "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
                                "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
                                "duracion":t.horario.duracion if t.horario and t.horario.duracion else "Sin duración" 
                                    })
            return Response(sucesionFiltrada)
    else:
        return Response({
            "success":False,
            "message": "Cargo invalido, revise por favor"
        })
        
@api_view(["POST"])
def solicitar_cambio_turno(request):

    codigoSolicitante = request.data.get('codigoSolicitante')
    codigoReceptor = request.data.get('codigoReceptor')

    print(codigoReceptor)
    
    fechaCambio = datetime.strptime(request.data.get('fechaCambio'), "%Y/%m/%d")
    fechaAnterior = fechaCambio - timedelta(days=1)
    fechaSiguiente = fechaCambio + timedelta(days=1)

    #Modelo Empleado // validar que los empleados existen
    solicitanteEmpleado = Empleado_Oddo.objects.filter(codigo = codigoSolicitante , estado = "Activo").exists()
    receptorEmpleado = Empleado_Oddo.objects.filter(codigo = codigoReceptor, estado = "Activo").exists()

    # Se valida si el codigo existe:
    if not solicitanteEmpleado:
        return Response ({"success":False , "message": f"El Empleado con codigo: {codigoSolicitante} no existe ó se encuentra inactivo"})
    
    if not receptorEmpleado:
        return Response ({"success":False , "message": f"El Empleado con codigo: {codigoReceptor} no existe ó se encuentra inactivo"})
    
    # Se valida el estado del empleado: Activo
    try:
        solicitanteEmpleado = Empleado_Oddo.objects.filter(codigo = codigoSolicitante , estado = "Activo").first()
    except Empleado_Oddo.DoesNotExist:
        return Response ({"success":False , "message": f"El Empleado con codigo{codigoSolicitante} no esta activo"})
    
    try:
        receptorEmpleado = Empleado_Oddo.objects.filter(codigo = codigoReceptor, estado = "Activo").first()
    except Empleado_Oddo.DoesNotExist:
         return Response ({"success":False , "message": f"El Empleado con codigo: {codigoReceptor} no esta activo"})

    print(f"solicitud cambio de turnos : Codigo solicitante: {codigoSolicitante}, codigo receptor: {codigoReceptor}, fecha de cambio: {fechaCambio}")

    solicitante = Empleado_Oddo.objects.filter(codigo=codigoSolicitante, estado  ="Activo").first()
    receptor = Empleado_Oddo.objects.filter(codigo=codigoReceptor, estado = "Activo").first()
    
    #existe_cruce_solicitudes = Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = fechaCambio).filter(Q(codigo_solicitante = codigoSolicitante, codigo_receptor = codigoReceptor) |  Q(codigo_solicitante = codigoReceptor, codigo_receptor = codigoSolicitante)).exists()
    #if existe_cruce_solicitudes:
       # return Response("Ya existe ca
       # mbio entre los dos")

    #Se valida que tanto el solicitante como el receptor eviten cambiar turno por si mismos
    if codigoSolicitante == codigoReceptor:
        return Response({
            "success": False,
            "message": "No es posible solicitar el cambios entre si mismo"
        })

    #Validar que tienen el mismo cargo
    if solicitanteEmpleado.cargo != receptorEmpleado.cargo:
        return Response({
            "success": False,
            "message": "Ambos empleados deben tener el mismo cargo para solicitar el cambio de turno."
        })

    #Validar que no tengas cambios pendientes para esa fecha
    errores = []

    if Cambios_de_turnos.objects.filter(codigo_solicitante=codigoSolicitante, fecha_solicitud_cambio=fechaCambio).exists():
        return Response({
            "success": False,
            "mensaje": f"El empleado {solicitante.nombre} ya tiene una solicitud de cambio para la fecha {fechaCambio}"

        })
      
    if Cambios_de_turnos.objects.filter(codigo_receptor = codigoSolicitante, fecha_solicitud_cambio=fechaCambio).exists():
        return Response({
             "success": False,
            "mensaje": f"El empleado {solicitante.nombre} ya tiene una solicitud de cambio para la fecha {fechaCambio}"
        })
       
    if Cambios_de_turnos.objects.filter(codigo_solicitante=codigoReceptor, fecha_solicitud_cambio=fechaCambio).exists():
        return Response({
             "success": False,
            "mensaje": f"El empleado {receptor.nombre} ya tiene una solicitud de cambio para la fecha {fechaCambio}"
        })
       
    if Cambios_de_turnos.objects.filter(codigo_receptor = codigoReceptor, fecha_solicitud_cambio=fechaCambio).exists():
        return Response({
             "success": False,
            "mensaje": f"El empleado {receptor.nombre} ya tiene una solicitud de cambio para la fecha {fechaCambio}"
        })
    

    if solicitante.cargo == "CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO" and receptor.cargo == "CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO":
        linea_B = ["SAB", "CIS", "SAM","EST","FLO","LUC","JAV"]
        if solicitante.formacion != receptor.formacion:
            if solicitante.formacion == "CAF": #Receptor MAN
                sucesiSoli = Sucesion.objects.filter(codigo = solicitante.codigo, fecha = fechaCambio).first()
                if sucesiSoli.estado_inicio not in linea_B: #LINEA B
                    return Response({"success":False, "message":f"El solicitante tiene formación CAF y no esta en LB"})
            elif receptor.formacion == "CAF": # Solicitante MAN
                sucesiRece = Sucesion.objects.filter(codigo = receptor.codigo, fecha = fechaCambio).first()
                if sucesiRece.estado_inicio not in linea_B:
                    return Response({"success":False, "message":f"El receptor tiene formación CAF y no esta en LB"})
                

    solicitante_siguiente = None
    receptor_siguiente = None
    comentarios = ""

    solicitante_anterior = get_object_or_404(Sucesion, codigo=codigoSolicitante, fecha=fechaAnterior)
    solicitante_dia = get_object_or_404(Sucesion, codigo=codigoSolicitante, fecha=fechaCambio)

    #Aca capturamos la exepcion en caso de que el turno siguiente sea None, esto ocurre cuando no hay sucesion siguiente cargada
    try:
        solicitante_siguiente = Sucesion.objects.get(codigo = codigoSolicitante, fecha = fechaSiguiente)
    except Sucesion.DoesNotExist:
        solicitante_siguiente = None

    receptor_anterior = get_object_or_404(Sucesion, codigo=codigoReceptor, fecha=fechaAnterior)
    receptor_dia = get_object_or_404(Sucesion, codigo=codigoReceptor, fecha=fechaCambio)
    
    try:
        receptor_siguiente = Sucesion.objects.get(codigo = codigoReceptor, fecha = fechaSiguiente)
    except Sucesion.DoesNotExist:
         receptor_siguiente = None

    # Impedir cambios en dias no validos
    estadosServicios = Estados_servicios.objects.all()
    turnosInvalidos = []
    for t in estadosServicios:
        turnosInvalidos.append(t.estado)

    if solicitante_dia.codigo_horario in turnosInvalidos:
        return Response({
            "success": False,
            "message": f"No se puede solicitar cambio cuando el solicitante tiene un turno: {solicitante_dia.codigo_horario} el día {fechaCambio.date()}."
        })

    if receptor_dia.codigo_horario in turnosInvalidos:
        return Response({
            "success": False,
            "message": f"No se puede solicitar cambio cuando el receptor tiene un turno: {receptor_dia.codigo_horario}: el día {fechaCambio.date()}."
        })

    if solicitante_dia.codigo_horario == "DISPO" and receptor_dia.codigo_horario == "DISPO":
        return Response({
            "success": False,
            "message": f"No se puede solicitar cambio cuando ambos empleados tienen turno:{solicitante_dia.codigo_horario} el día {fechaCambio.date()}."
        })


    solicitante_siguiente_codigo = solicitante_siguiente.codigo_horario if solicitante_siguiente else None
    receptor_siguiente_codigo = receptor_siguiente.codigo_horario if receptor_siguiente else None

    # Validar descanso mínimo para ambos
    descanso_solicitante_anterior, descanso_solicitante_posterior = validar_descanso(
        solicitante_anterior.codigo_horario, receptor_dia.codigo_horario,solicitante_siguiente_codigo,
        solicitante_dia.empleado.cargo, fechaCambio
    )

    descanso_receptor_anterior, descanso_receptor_posterior = validar_descanso(
        receptor_anterior.codigo_horario, solicitante_dia.codigo_horario, receptor_siguiente_codigo,
        receptor_dia.empleado.cargo, fechaCambio
    )

    print(f"Solicitante descanso minimo anterior {descanso_solicitante_anterior}, descanso minimo posteriror: {descanso_solicitante_posterior}")
    print(f"Recepor descanso minimo anterior {descanso_receptor_anterior}, descanso minimo posteriror: {descanso_receptor_posterior}")

    if not (descanso_solicitante_anterior and descanso_solicitante_posterior and descanso_receptor_anterior and descanso_receptor_posterior):
        return Response({
            "success": False,
            "message": "No se garantiza el descanso mínimo requerido entre turnos ambos empleados."
        })
    
    comentarios = "✅ Cumplen con el descanso minimo de 10 ó 8hrs antes y despues del dia de cambio"

    transportable_solicitante = False
    transportable_receptor =  False
    estadoCambio = ""
    madrugadaLinea = ["ORIENTE","OCCIDENTE","SUR"]
    madrugadaPatio = ["PBE"]

    if solicitante_dia.codigo_horario == "DISPO" or receptor_dia.codigo_horario == "DISPO":
        estadoCambio = "pendiente"
        comentarios = "El cambio queda a la espera de ser autorizado por el ADM"
        Cambios_de_turnos.objects.create(
            codigo_solicitante=codigoSolicitante,
            nombre_solicitante=solicitante_dia.nombre,
            cedula_solicitante = solicitante.cedula,
            turno_solicitante_original=solicitante_dia.codigo_horario,
            turno_solicitante_nuevo=receptor_dia.codigo_horario,
            cargo_solicitante=solicitante_dia.empleado.cargo,
            formacion_solicitante = solicitante.formacion,
            codigo_receptor=codigoReceptor,
            nombre_receptor=receptor_dia.nombre,
            cedula_receptor = receptor.cedula,
            turno_receptor_original=receptor_dia.codigo_horario,
            turno_receptor_nuevo=solicitante_dia.codigo_horario,
            cargo_receptor=receptor_dia.empleado.cargo,
            formacion_receptor = receptor.formacion, 
            fecha_solicitud_cambio=fechaCambio,
            estado_cambio_emp="pendiente",
            estado_cambio_admin = estadoCambio,
            comentarios = comentarios,
            zonaSolicitante = solicitante.zona,
            zonaReceptor = receptor.zona, 
            transportable_solicitante = transportable_solicitante,
            transportable_receptor = transportable_receptor
        )
        return Response({
            "success": True,
            "message": "Se registró correctamente la solicitud de cambio de turnos."
            })
        
    #Limites de madrugada y noche TRENES
    horaSemanaMadrugada = time.fromisoformat("05:00")
    horaSemanaNoche = time.fromisoformat("22:20")

    limiteMadrugada = datetime.combine(fechaCambio,horaSemanaMadrugada)
    limiteNoche = datetime.combine(fechaCambio,horaSemanaNoche)

    #Fin de semana
    horaFinSemanaMadrugada = time.fromisoformat("05:00")
    horaFinSemanaNoche = time.fromisoformat("22:20")

    limiteMadrugadaFin = datetime.combine(fechaCambio,horaSemanaMadrugada)
    limiteNocheFin = datetime.combine(fechaCambio,horaSemanaNoche)

    festivo_domingo = es_festivo_o_domingo(fechaCambio)

    if solicitante.cargo == "CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO" and receptor.cargo == "CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO":

        if  datetime.combine(fechaCambio, solicitante_dia.hora_inicio) < limiteMadrugada or  datetime.combine(fechaCambio,receptor_dia.hora_inicio) < limiteMadrugada:
            if solicitante.zona in madrugadaLinea and receptor.zona in madrugadaLinea:
                comentarios = f"{comentarios}\n✅ Ambos son transportables, zona: Madrugada Linea"
                transportable_solicitante = True
                transportable_receptor = True
                estadoCambio = "aprobado"
            elif solicitante.zona in madrugadaPatio and receptor.zona in madrugadaPatio:
                comentarios = f"{comentarios}\n✅ Ambos son transportables, zona: Madrugada PBE"
                transportable_solicitante = True
                transportable_receptor = True
                estadoCambio = "aprobado"
            else:
                comentarios = f"{comentarios}\n⛔ No se garantiza el servicio de transporte para uno ó ambos empleados, comunicarse con el area Gestión de Turnos si usted asume su transporte"
                transportable_solicitante = True
                transportable_receptor = True
                estadoCambio = "pendiente"
        elif datetime.combine(fechaCambio, solicitante_dia.hora_fin) < limiteNoche or  datetime.combine(fechaCambio,receptor_dia.hora_fin) < limiteNoche:
            comentarios = f"{comentarios}\n✅ Ambos cumplen, zona: No son transportables"
            transportable_solicitante = True
            transportable_receptor = True
            estadoCambio = "aprobado"
        else:
            comentarios = f"{comentarios}\n⛔ No se garantiza el servicio de transporte para uno ó ambos, comunicarse con el area Gestión de Turnos"
            transportable_solicitante = True
            transportable_receptor = True
            estadoCambio = "pendiente"

    #Crear solicitud de cambio
    Cambios_de_turnos.objects.create(

        codigo_solicitante=codigoSolicitante,
        nombre_solicitante=solicitante_dia.nombre,
        cedula_solicitante = solicitante.cedula,
        turno_solicitante_original=solicitante_dia.codigo_horario,
        turno_solicitante_nuevo=receptor_dia.codigo_horario,
        cargo_solicitante=solicitante_dia.empleado.cargo,
        formacion_solicitante = solicitante.formacion,
        codigo_receptor=codigoReceptor,
        nombre_receptor=receptor_dia.nombre,
        cedula_receptor = receptor.cedula,
        turno_receptor_original=receptor_dia.codigo_horario,
        turno_receptor_nuevo=solicitante_dia.codigo_horario,
        cargo_receptor=receptor_dia.empleado.cargo,
        formacion_receptor = receptor.formacion, 
        fecha_solicitud_cambio=fechaCambio,
        estado_cambio_emp="pendiente",
        estado_cambio_admin = estadoCambio,
        comentarios = comentarios,
        zonaSolicitante = solicitante.zona,
        zonaReceptor = receptor.zona, 
        transportable_solicitante = transportable_solicitante,
        transportable_receptor = transportable_receptor
    )

    #if noHaySucesionSiguienteSolicitante or noHaySucesionSiguienteReceptor:
     #   return Response({
      #      "success": True,
       #     "message": "Se registró correctamente la solicitud de cambio de turnos, sin embargo validar si hay conflicto con el siguiente turno una vez se cargue la sucesión"
        #})

    return Response({
        "success": True,
        "message": "Se registró correctamente la solicitud de cambio de turnos"
    })


@api_view(["POST"])
def aprobar_solicitudes_cambios_turnos(request):

    solicitudesAprobadas = []
    contadorSolicitudes = 0

    
    solicitudes = request.data.get('solicitudes')

    if solicitudes is not None:

        for solicitud in solicitudes:
            
            print(f"Solicitudes: fecha cambio : {solicitud['fechaCambio']} , codigo solicitante: {solicitud.get('codigoSolicitante')} , codigo receptor: {solicitud['codigoReceptor']}")
            print(f"Turno que el  solicitande necesita : {solicitud['turnoSolicitanteDiaDeseado']}, Turno que el receptor necesita: {solicitud['turnoReceptorDiaDeseado']}")

            peticion = solicitud.get("peticion")
            
            solicitudCambio =  Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud.get('fechaCambio'), codigo_solicitante = solicitud.get('codigoSolicitante'), 
                codigo_receptor = solicitud.get('codigoReceptor')).first()
            
            print(solicitudCambio)

            if peticion == "intranet":
                if solicitudCambio.estado_cambio_admin == "aprobado":
                    horario_relacion_solicitante = Horario.objects.filter(turno=solicitud['turnoSolicitanteDiaDeseado']).first()

                    if solicitud['turnoSolicitanteDiaDeseado'] == "DISPO": #RECEPTOR TIENE DISPO
                        print(f"El receptor tiene el DISPO: {solicitud['turnoSolicitanteDiaDeseado']}") # DISPO:DISPO
                        #Actualizar sucesión del solicitante
                        Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], fecha=solicitud['fechaCambio']).update(codigo_horario =solicitud['turnoSolicitanteDiaDeseado'],
                                                        horario = None, 
                                                        estado_inicio = None,
                                                        estado_fin = None ,
                                                        hora_inicio = None ,
                                                        hora_fin = None)
                        #Actualizar sucesión  del receptor                                 #SOLICITANTE TURNO:
                        if Horario.objects.filter(turno=solicitud['turnoReceptorDiaDeseado']).exists():
                            horario_relacion_receptor = Horario.objects.filter(turno=solicitud['turnoReceptorDiaDeseado']).first()
                        else:
                            horario_relacion_receptor = None

                        sucesionSolicitante = Sucesion.objects.filter(codigo_horario = solicitud['turnoReceptorDiaDeseado'], fecha = solicitud['fechaCambio']).first()

                        Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'],
                                                        horario = horario_relacion_receptor , 
                                                        estado_inicio = sucesionSolicitante.estado_inicio, 
                                                        estado_fin = sucesionSolicitante.estado_fin,
                                                        hora_inicio = sucesionSolicitante.hora_inicio, 
                                                        hora_fin = sucesionSolicitante.hora_fin)
                        
                        Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], codigo_solicitante = solicitud['codigoSolicitante'], 
                        codigo_receptor = solicitud['codigoReceptor'] ).update(estado_cambio_emp = "aprobado")

                    elif solicitud['turnoReceptorDiaDeseado'] == "DISPO": # Solicitante : DISPO
                        
                        print(f"El solicitante tiene el DISPO: {solicitud['turnoReceptorDiaDeseado']}") # DISPO:DISPO
                        #Actualizar sucesión  del receptor
                        
                        Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario =solicitud['turnoReceptorDiaDeseado'],
                                                        horario = None, 
                                                        estado_inicio = None, 
                                                        estado_fin = None,
                                                        hora_inicio = None, 
                                                        hora_fin = None)
                        #Actualizar sucesión del solicitante.

                        if Horario.objects.filter(turno=solicitud['turnoSolicitanteDiaDeseado']).exists():
                            horario_relacion_solicitante = Horario.objects.filter(turno=solicitud['turnoSolicitanteDiaDeseado']).first()
                        else:
                            horario_relacion_solicitante = None

                        sucesionSolicitante = Sucesion.objects.filter(codigo_horario = solicitud['turnoReceptorDiaDeseado'], fecha=solicitud['fechaCambio']).first()
                        Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'], 
                                                        horario = horario_relacion_solicitante, 
                                                        estado_inicio = sucesionSolicitante.estado_inicio, 
                                                        estado_fin = sucesionSolicitante.estado_fin , 
                                                        hora_inicio = sucesionSolicitante.hora_inicio , 
                                                        hora_fin = sucesionSolicitante.hora_fin)
                        
                        Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], codigo_solicitante = solicitud['codigoSolicitante'], 
                        codigo_receptor = solicitud['codigoReceptor'] ).update(estado_cambio_emp = "aprobado")
                    else:
                        print(f"NINGUNO DE LOS DOS TIENE DISPO")
                        
                        if Horario.objects.filter(turno = solicitud['turnoSolicitanteDiaDeseado']).exists():
                            horario_relacion_receptor = Horario.objects.filter(turno = solicitud['turnoSolicitanteDiaDeseado']).first()
                        else:
                            horario_relacion_receptor = None

                        if Horario.objects.filter(turno = solicitud['turnoReceptorDiaDeseado']).exists():
                            horario_relacion_solicitante = Horario.objects.filter(turno = solicitud['turnoReceptorDiaDeseado']).first()
                        else:
                            horario_relacion_solicitante = None

                        sucesionSolicitante = Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], codigo_horario = solicitud['turnoReceptorDiaDeseado'], fecha = solicitud['fechaCambio']).first()
                        sucesionReceptor = Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], codigo_horario = solicitud['turnoSolicitanteDiaDeseado'], fecha = solicitud['fechaCambio']).first()

                        Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], fecha= solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoSolicitanteDiaDeseado'],
                                                        horario = horario_relacion_receptor, 
                                                        estado_inicio = sucesionReceptor.estado_inicio, 
                                                        estado_fin = sucesionReceptor.estado_fin ,
                                                        hora_inicio = sucesionReceptor.hora_inicio, 
                                                        hora_fin = sucesionReceptor.hora_fin)
                        
                        print(f"Peticion codigoSolicitante: {solicitud['codigoSolicitante']} , turno:{solicitud['turnoReceptorDiaDeseado']}, fecha = {solicitud['fechaCambio']}")
                        
                        print(f"SUCESION SOLICITANTE:{Sucesion.objects.filter(codigo_horario = solicitud['turnoReceptorDiaDeseado'], fecha = solicitud['fechaCambio']).exists()}")
                        Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'], 
                                                        horario = horario_relacion_solicitante, 
                                                        estado_inicio = sucesionSolicitante.estado_inicio, 
                                                        estado_fin = sucesionSolicitante.estado_fin, 
                                                        hora_inicio = sucesionSolicitante.hora_inicio, 
                                                        hora_fin = sucesionSolicitante.hora_fin )

                        Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], codigo_solicitante = solicitud['codigoSolicitante'], 
                            codigo_receptor = solicitud['codigoReceptor'] ).update(estado_cambio_emp = "aprobado")
                    
                        empleadoSolicitante =  Empleado_Oddo.objects.filter(codigo = solicitud['codigoSolicitante'], estado = "Activo").first()
                        empleadoReceptor = Empleado_Oddo.objects.filter(codigo= solicitud['codigoReceptor'], estado = "Activo").first()

                        solicitudCambioTurno = Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], 
                                                    codigo_solicitante = solicitud['codigoSolicitante'], 
                                                    codigo_receptor = solicitud['codigoReceptor']).first()
                        
                        send_log(empleadoSolicitante.cedula, datetime.today(), "Aprobar solicitud",
                            f"Se aprobo la solicitud de cambio de turno entre: {empleadoSolicitante.nombre}, cod: {empleadoSolicitante.codigo} y {empleadoReceptor.nombre}, cod: {empleadoReceptor.codigo}, para la fecha: {solicitud['fechaCambio']}",
                            "AppGestionTurnos","Aprobar cambios", solicitudCambioTurno.id)      
                        
                elif solicitudCambio.estado_cambio_admin == "pendiente":
                        
                        Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], codigo_solicitante = solicitud['codigoSolicitante'], 
                        codigo_receptor = solicitud['codigoReceptor'] ).update(estado_cambio_emp = "aprobado")
                        return Response({
                            "success":True, "message": "Has aprobado correctamente el cambio de turno, debes esperar la aprobación por parte del Admin"
                            })
                elif solicitudCambio.estado_cambio_admin == "desaprobado":
                    return Response({
                            "success":True, "message": "El cambio de turno fue rechazado. Si consideras que debes discutir la solicitud, contacta al OC-SAA ó Gestión de turnos"
                            })
            elif peticion == "admin": 

                if solicitudCambio.estado_cambio_emp == "aprobado":

                    if Horario.objects.filter(turno=solicitud['turnoSolicitanteDiaDeseado']).exists():
                        horario_relacion_solicitante = Horario.objects.filter(turno=solicitud['turnoSolicitanteDiaDeseado']).first()
                    else:
                           horario_relacion_solicitante = None
                    
                    if solicitud['turnoSolicitanteDiaDeseado'] == "DISPO": #TURNO RECEPTOR == DISPO
                        
                        print(f"El receptor tiene el DISPO: {solicitud['turnoSolicitanteDiaDeseado']}") # DISPO:DISPO
                        #Actualizar sucesión del solicitante
                        Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], fecha=solicitud['fechaCambio']).update(codigo_horario =solicitud['turnoSolicitanteDiaDeseado'],
                                                        horario = None, 
                                                        estado_inicio = None,
                                                        estado_fin = None ,
                                                        hora_inicio = None ,
                                                        hora_fin = None)
                        #Actualizar sucesión  del receptor                                 #SOLICITANTE TURNO:
                        if Horario.objects.filter(turno=solicitud['turnoReceptorDiaDeseado']).exists():
                            horario_relacion_receptor = Horario.objects.filter(turno=solicitud['turnoReceptorDiaDeseado']).first()    
                        else:
                            horario_relacion_receptor = None
                        sucesionSolicitante = Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], codigo_horario = solicitud['turnoReceptorDiaDeseado'], fecha = solicitud['fechaCambio']).first()
                    
                        Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'],
                                                        horario = horario_relacion_receptor , 
                                                        estado_inicio = sucesionSolicitante.estado_inicio, 
                                                        estado_fin = sucesionSolicitante.estado_fin,
                                                        hora_inicio = sucesionSolicitante.hora_inicio, 
                                                        hora_fin = sucesionSolicitante.hora_fin)
                        # aca acentamos la aprobación del empleado
                        Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], codigo_solicitante = solicitud['codigoSolicitante'], 
                            codigo_receptor = solicitud['codigoReceptor'] ).update(estado_cambio_admin = "aprobado")    
                    elif solicitud['turnoReceptorDiaDeseado'] == "DISPO": #El DISPO lo tiene el Solicitante
                        print(f"El solicitante tiene el DISPO: {solicitud['turnoReceptorDiaDeseado']}") 
                        #Actualizar sucesión  del receptor
                        Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'],
                                                        horario = None, 
                                                        estado_inicio = None, 
                                                        estado_fin = None,
                                                        hora_inicio = None, 
                                                        hora_fin = None)
                        #Actualizar sucesión del solicitante.
                        if Horario.objects.filter(turno=solicitud['turnoSolicitanteDiaDeseado']).exists():
                            horario_relacion_solicitante = Horario.objects.filter(turno=solicitud['turnoSolicitanteDiaDeseado']).first()
                        else:
                            horario_relacion_solicitante = None
                        sucesionReceptor = Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], codigo_horario = solicitud['turnoSolicitanteDiaDeseado'], fecha = solicitud['fechaCambio']).first()
                        Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoSolicitanteDiaDeseado'], 
                                                        horario = horario_relacion_solicitante, 
                                                        estado_inicio = sucesionReceptor.estado_inicio, 
                                                        estado_fin = sucesionReceptor.estado_fin , 
                                                        hora_inicio = sucesionReceptor.hora_inicio , 
                                                        hora_fin = sucesionReceptor.hora_fin)
                        
                        Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], codigo_solicitante = solicitud['codigoSolicitante'], 
                            codigo_receptor = solicitud['codigoReceptor'] ).update(estado_cambio_admin = "aprobado")
                    else:
                        print(f"NINGUNO DE LOS DOS TIENE DISPO")

                        if Horario.objects.filter(turno = solicitud['turnoSolicitanteDiaDeseado']).exists():
                            horario_relacion_receptor = Horario.objects.filter(turno = solicitud['turnoSolicitanteDiaDeseado']).first()
                        else:
                            horario_relacion_receptor = None
                        sucesionReceptor = Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], codigo_horario = solicitud['turnoSolicitanteDiaDeseado'], fecha = solicitud['fechaCambio']).first()

                        Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], fecha=solicitud['fechaCambio']).update(codigo_horario =solicitud['turnoSolicitanteDiaDeseado'],
                                                        horario = horario_relacion_receptor, 
                                                        estado_inicio = sucesionReceptor.estado_inicio, 
                                                        estado_fin = sucesionReceptor.estado_fin,
                                                        hora_inicio = sucesionReceptor.hora_inicio,
                                                        hora_fin = sucesionReceptor.hora_fin)
                        if Horario.objects.filter(turno = solicitud['turnoReceptorDiaDeseado']).exists():
                            horario_relacion_solicitante = Horario.objects.filter(turno = solicitud['turnoReceptorDiaDeseado']).first()
                        else:
                            horario_relacion_solicitante = None
                            
                        sucesionSolicitante = Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], codigo_horario = solicitud['turnoReceptorDiaDeseado'], fecha = solicitud['fechaCambio']).first()

                        Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'], 
                                                        horario = horario_relacion_solicitante, 
                                                        estado_inicio = sucesionSolicitante.estado_inicio , 
                                                        estado_fin = sucesionSolicitante.estado_fin, 
                                                        hora_inicio = sucesionSolicitante.hora_inicio, 
                                                        hora_fin = sucesionSolicitante.hora_fin)
                        
                        Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], codigo_solicitante = solicitud['codigoSolicitante'], 
                            codigo_receptor = solicitud['codigoReceptor'] ).update(estado_cambio_admin = "aprobado")
                    
                        empleadoSolicitante =  Empleado_Oddo.objects.filter(codigo = solicitud['codigoSolicitante'], estado = "Activo").first()
                        empleadoReceptor = Empleado_Oddo.objects.filter(codigo= solicitud['codigoReceptor'], estado = "Activo").first()

                        solicitudCambioTurno = Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], 
                                                    codigo_solicitante = solicitud['codigoSolicitante'], 
                                                    codigo_receptor = solicitud['codigoReceptor']).first()
                        send_log(empleadoSolicitante.cedula, datetime.today(), "Aprobar solicitud",
                            f"Se aprobo la solicitud de cambio de turno entre: {empleadoSolicitante.nombre}, cod: {empleadoSolicitante.codigo} y {empleadoReceptor.nombre}, cod: {empleadoReceptor.codigo}, para la fecha: {solicitud['fechaCambio']}",
                            "AppGestionTurnos","Aprobar cambios", solicitudCambioTurno.id)      
                else:
                     return Response({
                            "success":False,
                            "message": "El cambio no ha sido aprobado por el empleado"
                            })
            else:
                return Response({
                    "success":False,
                    "message": f"No se encontro un destino para la petición, valor actual: {peticion}"
                    })    
            contadorSolicitudes += 1
        return Response({
            "success":True,
            "message": f"Se aprobaron con exito: {contadorSolicitudes}, solicitudes de cambios de turnos"
            })

    return Response({
            "success":False, "message": "Solicitudes vacias"
            })
    

@api_view(["POST"])
def desaprobar_solicitudes_cambios(request):

    solicitudes = request.data.get('solicitudes')
    
    if solicitudes is not None: 
        for solicitud in solicitudes:

            if solicitud.get('codigoSolicitante') and solicitud.get('codigoReceptor'):

                empleadoSolicitante = Empleado_Oddo.objects.filter(codigo = solicitud['codigoSolicitante'], estado = "Activo").first()
                empleadoReceptor = Empleado_Oddo.objects.filter(codigo = solicitud['codigoReceptor'] , estado = "Activo").first()

                solicitudCambiosTurnos = get_object_or_404(Cambios_de_turnos, fecha_solicitud_cambio = solicitud['fechaCambio'], 
                                                codigo_solicitante = solicitud['codigoSolicitante'], 
                                                codigo_receptor = solicitud['codigoReceptor'])
                
                Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], 
                                                codigo_solicitante = solicitud['codigoSolicitante'], 
                                                codigo_receptor = solicitud['codigoReceptor']).update(estado_cambio_emp = "desaprobado")
                if solicitud['peticion'] == "intranet":
                    Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], 
                                                codigo_solicitante = solicitud['codigoSolicitante'], 
                                                codigo_receptor = solicitud['codigoReceptor']).update(estado_cambio_emp = "desaprobado")
                elif solicitud['peticion'] == "admin":
                    Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], 
                                                codigo_solicitante = solicitud['codigoSolicitante'], 
                                                codigo_receptor = solicitud['codigoReceptor']).update(estado_cambio_admin = "desaprobado")
                    
                send_log(empleadoSolicitante.cedula, datetime.today(), "Rechazar solicitud",
                        f"Se rechazo la solicitud de cambio entre: {empleadoSolicitante.nombre}, cod: {empleadoSolicitante.codigo} y {empleadoReceptor.nombre}, cod: {empleadoReceptor.codigo}, para la fecha: {solicitud['fechaCambio']}",
                        "AppGestionTurnos","Update:estadoSolicitud", solicitudCambiosTurnos.id)
                
                return Response({
                    "success":True,
                    "message":f"Se desaprobo el cambio de turno entre: {solicitud['codigoSolicitante']} y {solicitud['codigoReceptor']}, para la fecha: {solicitud['fechaCambio']}",
                }, status=200)
            else:
                return Response({
                    "success":False,
                    "message":f"Los codigos de solicitante o receptor llegaron vacios, S: {solicitud.get('codigoSolicitante')}, R: {solicitud.get('codigoReceptor')}"
                })
    else:
        return Response({
            "success":False,
            "message": f"Solicitudes vacias, contenido {solicitudes}"
        })


@api_view(["POST"])
def solicitud_gt(request):

    print("Content-Type:", request.content_type)
    print("FILES keys:", list(request.FILES.keys()))
    print("DATA  keys:", list(request.data.keys()))

    codigoSolicitante = request.data.get('codigoSolicitante')
    cedulaSolicitante = request.data.get('cedulaSolicitante')
    tipo_solicitud = request.data.get('tipoSolicitud')
    fecha_solicitud = request.data.get('fechaSolicitud')
    fecha_inicial = request.data.get('fechaInicial')
    fecha_final = request.data.get('fechaFinal')
    descripcion = request.data.get('descripcion')
    archivo = request.FILES.get('archivo')

    if codigoSolicitante is not None and cedulaSolicitante is not None:

        if Empleado_Oddo.objects.filter(codigo = codigoSolicitante, cedula = cedulaSolicitante, estado = "Activo").exists() == False:
            return Response({
            "success":False,
            "message":f"Usted no se encuentra activo para realizar este tipo de peticiones"})

        validarSolicitudExistente = Solicitudes_Gt.objects.filter(empleado__codigo = codigoSolicitante, empleado__cedula = cedulaSolicitante, tipo_solicitud = tipo_solicitud, fecha_inicial = fecha_inicial, fecha_final = fecha_final).exists()

        if validarSolicitudExistente:
            return Response({
                "success":False, 
                "message":f"Error, ya tienes un solicitud de: {tipo_solicitud}, entre estas fechas, fecha inicial: {fecha_inicial}, fecha final: {fecha_final}"})


        print(f"#%#$%&/%$%&/&%$% >>> ARCHIVO CARGADOOOOOOOOOOOOOOO::::::::::::::::: {archivo}")

        empleado = Empleado_Oddo.objects.filter(codigo = codigoSolicitante, cedula = cedulaSolicitante,  estado = "Activo").first()
        solicitud_gt = Solicitudes_Gt.objects.create( cargo = empleado.cargo, 
                                      tipo_solicitud = tipo_solicitud, fecha_solicitud = fecha_solicitud, 
                                      fecha_inicial = fecha_inicial , fecha_final = fecha_final, descripcion = descripcion, empleado = empleado)
        
        if archivo:
            nombreArchivo = archivo.name
            ext = Path(nombreArchivo).suffix.lower()
            nombreArchivoSolicitud = f"{solicitud_gt.tipo_solicitud}_{solicitud_gt.id}"
            urlArchivo = upload_to_azure_blob(archivo,nombreArchivoSolicitud,"solicitud_gt")
            solicitud_gt.urlArchivo = urlArchivo
            solicitud_gt.tipoArchivo = ext
            solicitud_gt.save()
            

        #mensajeGmail = f"Te queremos informar que la solicitud {tipo_solicitud} con fecha de registro: {fecha_solicitud}, quedo registrada de manera correcta en nuestro sistema, el area de Gestión de turnos evaluara la solicitud, muchas gracias"
        asunto = f"Solicitud de Gestión de turnos - solicitud: {tipo_solicitud}"

        #enviarCorreoGmail("sbastianpp@gmail.com",mensajeGmail, asunto)
        #def enviarCorreoGmailHTML(destinatario, nombre, solicitud, fecha_registro, asunto="Estado de tu solicitud"):

        estadoEnvioCorreo = enviarCorreoGmailHTML("sbastianpp@gmail.com", empleado.nombre, tipo_solicitud, fecha_solicitud, asunto, estado ="pendiente")
        fecha_notificacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if estadoEnvioCorreo:
            Notificaciones.objects.create(empleado = empleado, cargo = empleado.cargo, solicitudes_Gt = solicitud_gt,
                fecha_notificacion = fecha_notificacion, correo = "sbastianpp@gmail.com", medio = "E-mail", estado = "Notificado")
            return Response({"success":True, "message":f"Se registro exitosamente la solicitud con id: {solicitud_gt.id}, tipo solicitud: {tipo_solicitud} y con fecha de registro: {fecha_solicitud}"})
        else:
            Notificaciones.objects.create(empleado = empleado, cargo = empleado.cargo, solicitudes_Gt = solicitud_gt,
                fecha_notificacion = fecha_notificacion, correo = "sbastianpp@gmail.com", medio = "E-mail", estado = "No notificado")
            return Response({"success":False, "message":f"No se registro exitosamente la solicitud, {tipo_solicitud}, con fecha de reigstro:{fecha_solicitud}"}) 
    else:
        return Response({"success":False, "message":"Parametros de solicitud vacios"})
    

@api_view(["POST"])
def actualizar_parametros(request):

    horaInicio = request.data.get('horaInicio')
    horaFin = request.data.get('horaFin')
    diaInico = request.data.get('diaIncio')
    diaFin = request.data.get('diaFin')
    horaInicioSolicitudesGt = request.data.get('horaInicioSolicitudesGt')
    horaFinSolicitudesGt = request.data.get('horaFinalSolicitudesGt')

    parametros = Parametros.objects.all().first()

    Parametros.objects.filter(id = parametros.id).update(hora_inicio_permitida_cambios = horaInicio, 
                                                        hora_final_permitida_cambios = horaFin,
                                                        dia_inicio_permitida_cambios = diaInico,
                                                        dia_final_permitida_cambios = diaFin,
                                                        hora_inicio_solicitudesgt = horaInicioSolicitudesGt,
                                                        hora_final_solicitudesgt = horaFinSolicitudesGt
                                                        ) 
    send_log("Sebastian Rivera", datetime.today(), "Actualizar",
             f"Parametros actualizados, [ Cambios de turnos ] Hora incio: {horaInicio}, Hora final: {horaFin}, [ Solicitudes GT ] Día incial:  {diaInico}, Día final solicitudes : {diaFin}, Hora incio: {horaInicioSolicitudesGt}, Hora final: {horaFinSolicitudesGt}","AppGestionTurnos","Actulizar parametros",parametros.id)
       
    return Response({
        "success":True,
        "message":f"Parametros actualizados, [ Cambios de turnos ] Hora incio: {horaInicio}, Hora final: {horaFin}, [ Solicitudes GT ] Día incial:  {diaInico}, Día final solicitudes : {diaFin}, Hora incio: {horaInicioSolicitudesGt}, Hora final: {horaFinSolicitudesGt}"
    })

@api_view(["POST"])
def insertar_estado(request):

    estadoServicio = request.data.get('estadoServicio')
    accionBoton = request.data.get('accion')
    if estadoServicio and accionBoton:
        if accionBoton == "insertar":
            Estados_servicios.objects.create(estado = estadoServicio)
            return Response({
                "success":True,
                "message": f"Se inserto correctamente el estado de servicio: {estadoServicio}"
            })
        elif accionBoton == "eliminar":
            Estados_servicios.objects.filter(estado = estadoServicio).delete()
            return Response({
                "success":True,
                "message": f"Se elimino correctamente el estado de servicio: {estadoServicio}"
            })
    else:
        return Response({
            "success":False,
            "message":"Estado de servicio invalido, posiblemente esta llegando vacio"
        })

@api_view(["GET"])
def get_comunicados(request):

    codigo = request.GET.get('codigo')
    
    try:
        empleado = Empleado_Oddo.objects.get(codigo = codigo , estado = "Activo")
        cargo = empleado.cargo
    except Empleado_Oddo.DoesNotExist:
        return Response({"success":False,
                         "message": f"El codigo: {codigo} enviado no es valido o se encuentra inactivo"})

    print(f"codigo: {codigo}, cargo: {cargo}")
    #fechaVigencia= request.data.get('fechaVigencia')

    archivos = Archivos.objects.filter( Q(fechaVigencia__gte = datetime.today()) | Q(fechaVigencia__isnull=True))
    listaArchivos = []

    print(f"Cantidad de comunicados en la BD: {archivos.count()}")
    print(archivos)

    for filtro in archivos:
        if cargo in filtro.cargoVisualizacion:
            print("esta dentro de los cargos")
            if ConfirmacionLectura.objects.filter(codigo = codigo, archivos__id = filtro.id , confirmacionLectura = "leido").exists() == False:
                listaArchivos.append(f"titulo: {filtro.titulo}, id: {filtro.id}, url: {filtro.urlArchivo}, tipo de archivo: {filtro.tipoArchivo}")

    return Response({"success":True , "datos": listaArchivos})

@api_view(["POST"])
def get_datos_filtro_sucesion(request):

    codigo = request.data.get('codigo')
    estado = request.data.get('estado')
    fechaInicial = request.data.get('fechaInicial')
    fechaFinal = request.data.get('fechaFinal')

    print(f"codigo:{codigo}, estado: {estado}, fechainicial: {fechaInicial}, fechafinal: {fechaFinal}")

    if codigo and estado and fechaInicial and fechaFinal:
        sucesionFiltrada = Sucesion.objects.filter(Q(fecha__gte=fechaInicial, fecha__lte=fechaFinal),codigo=codigo,estado_sucesion=estado).select_related("horario").values(
            "nombre", "codigo", "codigo_horario", "cargo","fecha","estado_inicio","estado_fin","hora_inicio","hora_fin","horario__observaciones","estado_sucesion","usuario_carga"
        )

        #sucesionFiltrada =  Sucesion.objects.filter(Q(fecha__gte = fechaInicial, fecha__lte = fechaFinal ),codigo = codigo, estado_sucesion = estado).values(
         #   "nombre", "codigo", "codigo_horario", "cargo","fecha","estado_inicio","estado_fin","hora_inicio","hora_fin","horario__observaciones","estado_sucesion","usuario_carga"
        #)

        data = []
        for s in sucesionFiltrada:
            s["particularidades"] = s.pop("horario__observaciones", "")
            data.append(s)

        #data = list(sucesionFiltrada.values())
        return Response({"success": True, 
                         "message": f"Se cargaron correctamente: {sucesionFiltrada.count()}, resultados", 
                         "data":data})
    else:
        return Response({"success":False, 
                         "message": f"Alguno de los parametros llegaron sin datos, codigo: {codigo}, estado: {estado}, fecha incial: {fechaInicial}, fecha final: {fechaFinal}"})

    

@api_view(["POST"])
def reprogramar_turno(request):
    fechaTurno = request.data.get('fecha','').strip()
    codigoTurno = request.data.get('codigoTurno').strip()
    codigoConductor = request.data.get('codigo','').strip()
    estacionIni = request.data.get('estacionIni').strip()
    estacionFin = request.data.get('estacionFin').strip()
    horaIni = request.data.get('horaIni').strip()
    horaFin = request.data.get('horaFin').strip()
    particularidades = request.data.get('particularidades').strip()

    # vamos a filtar que en el modelo no exista alguien con este turno

    conductorReprogramado = get_object_or_404(Sucesion,codigo=codigoTurno)
    if Sucesion.objects.filter(fecha=fechaTurno, codigo_horario= codigoTurno).exists():
        TurnoAsignado_enConflicto = get_object_or_404(fecha=fechaTurno, codigo_horario= codigoTurno)
        conductorReprogramado
        return Response (f"Este turno: {codigoTurno}, para la fecha: {fechaTurno}, ya lo tiene asignado:{TurnoAsignado_enConflicto.nombre}")
    else: 
        return Response (f"Turno disponible")


@api_view(["GET"])
def cabeceras_turnos(request):

    codigo = request.GET.get("codigo")
    peticion = request.GET.get('peticion', None)

    try:
        empleado = Empleado_Oddo.objects.filter(codigo = codigo, estado = "Activo").first()
    except Empleado_Oddo.DoesNotExist:
        return Response({"success":False, "message": f"No existe un empleado activo con ese codigo:{codigo}"})

    if not codigo:
        return Response({"success": False, "message": "El parámetro 'codigo' es requerido"})

    cargosSabadoViernes = ["CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO"]
    cargosLunesDomingos = ["CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO TRANVIA",
                           "OPERADOR(A) DE CONDUCCION","MANIOBRISTA TRENES","MANIOBRISTA TRANVIA",]

    # fecha (DateField) → DateTime para poder sumar/restar en DB
    fecha_dt = Cast(F("fecha"), DateTimeField())

    if empleado.cargo in cargosSabadoViernes:

        if peticion == None:
            # Duraciones tipadas
            plus_2d = Value(timedelta(days=2), output_field=DurationField())
            plus_6d = Value(timedelta(days=6), output_field=DurationField())

            base_trunc   = TruncWeek(ExpressionWrapper(fecha_dt + plus_2d, output_field=DateTimeField()))
            wk_start_dt  = ExpressionWrapper(base_trunc - plus_2d, output_field=DateTimeField())
            wk_start     = Cast(wk_start_dt, DateField())
            wk_end       = Cast(ExpressionWrapper(wk_start_dt + plus_6d, output_field=DateTimeField()), DateField())

            qs = (Sucesion.objects
                .filter(codigo=codigo, cargo = empleado.cargo, estado_sucesion = "publicado")
                .annotate(week_start=wk_start, week_end=wk_end)
                .values("week_start", "week_end")
                .distinct()
                .order_by("week_start"))
            
            encabezados = [{
                "titulo": f"Semana del {e['week_start']:%d/%m/%Y} al {e['week_end']:%d/%m/%Y}",
                "inicio": e["week_start"].isoformat(),
                "fin": e["week_end"].isoformat(),
            } for e in qs]

            return Response({"success": True, "encabezados": encabezados})
        elif peticion == "todo":
            
            plus_2d = Value(timedelta(days=2), output_field=DurationField())
            plus_6d = Value(timedelta(days=6), output_field=DurationField())

            base_trunc   = TruncWeek(ExpressionWrapper(fecha_dt + plus_2d, output_field=DateTimeField()))
            wk_start_dt  = ExpressionWrapper(base_trunc - plus_2d, output_field=DateTimeField())
            wk_start     = Cast(wk_start_dt, DateField())
            wk_end       = Cast(ExpressionWrapper(wk_start_dt + plus_6d, output_field=DateTimeField()), DateField())

            qsTodaSucesion = (Sucesion.objects
                .filter(cargo = empleado.cargo, estado_sucesion = "publicado")
                .annotate(week_start=wk_start, week_end=wk_end)
                .values("week_start", "week_end")
                .distinct()
                .order_by("week_start"))
            
            encabezados = [{
                "titulo": f"Semana del {e['week_start']:%d/%m/%Y} al {e['week_end']:%d/%m/%Y}",
                "inicio": e["week_start"].isoformat(),
                "fin": e["week_end"].isoformat(),
            } for e in qsTodaSucesion]

            return Response({"success": True, "encabezados": encabezados})
        else:
            return Response({"success": False,"message":f"La peticion llego con valores no definidos {peticion}"})
    elif empleado.cargo in cargosLunesDomingos:
        plus_6d    = Value(timedelta(days=6), output_field=DurationField())
        # 3) Semana LUN→DOM
        base_trunc = TruncWeek(fecha_dt)  # lunes 00:00
        wk_start_dt = base_trunc          # inicio (lunes)
        wk_end_dt   = ExpressionWrapper(base_trunc + plus_6d, output_field=DateTimeField())

        # 4) Opcional: como Date “limpio”
        wk_start = Cast(wk_start_dt, DateField())
        wk_end   = Cast(wk_end_dt,   DateField())

        # 5) Uso en queryset
        qs = (Sucesion.objects
            .filter(codigo=codigo, cargo = empleado.cargo, estado_sucesion = "publicado")
            .annotate(
                fecha_dt=fecha_dt,
                plus_6d=plus_6d,
                base_trunc=base_trunc,
                wk_start_dt=wk_start_dt,
                wk_end_dt=wk_end_dt,
                wk_start=wk_start,
                wk_end=wk_end,
            )).values('wk_start','wk_end').distinct().order_by('-wk_start')
        
        encabezados = [{
            "titulo": f"Semana del {e['wk_start']:%d/%m/%Y} al {e['wk_end']:%d/%m/%Y}",
            "inicio": e["wk_start"].isoformat(),
            "fin": e["wk_end"].isoformat(),
        } for e in qs]
        return Response({"success": True, "encabezados": encabezados})
    elif peticion == "todo":

        plus_2d = Value(timedelta(days=2), output_field=DurationField())
        plus_6d = Value(timedelta(days=6), output_field=DurationField())

        base_trunc   = TruncWeek(ExpressionWrapper(fecha_dt + plus_2d, output_field=DateTimeField()))
        wk_start_dt  = ExpressionWrapper(base_trunc - plus_2d, output_field=DateTimeField())
        wk_start     = Cast(wk_start_dt, DateField())
        wk_end       = Cast(ExpressionWrapper(wk_start_dt + plus_6d, output_field=DateTimeField()), DateField())

        qsTodaSucesion = (Sucesion.objects
            .filter(cargo = empleado.cargo, estado_sucesion = "publicado")
            .annotate(week_start=wk_start, week_end=wk_end)
            .values("week_start", "week_end")
            .distinct()
            .order_by("week_start"))
            
        encabezados = [{
            "titulo": f"Semana del {e['week_start']:%d/%m/%Y} al {e['week_end']:%d/%m/%Y}",
            "inicio": e["week_start"].isoformat(),
            "fin": e["week_end"].isoformat(),
        } for e in qsTodaSucesion]

        return Response({"success": True, "encabezados": encabezados})
    else:
        return Response({"success": False,"message":f"La peticion llego con valores no definidos {peticion}"})

@api_view(["GET"])
def mis_solicitudes_cambios_turnos(request):
    codigoSolicitante = request.GET.get('codigoSolicitante')
    estado = request.GET.get("estado")
    print(codigoSolicitante)
    print(estado)

    if not codigoSolicitante and not estado : 
        solicitudesCambiosTurnos = Cambios_de_turnos.objects.filter((Q(codigo_solicitante= codigoSolicitante) | Q(codigo_receptor = codigoSolicitante )), estado_cambio_admin = estado ).only('codigo_solicitante', 'nombre_solicitante', 'cargo_solicitante',
            'turno_solicitante_original','turno_solicitante_nuevo','fecha_solicitud_cambio',
            'codigo_receptor','nombre_receptor','cargo_receptor','turno_receptor_original','turno_receptor_nuevo','estado_cambio_admin')
        data = []
        for s in solicitudesCambiosTurnos:
            data.append({
                'codigo_solicitante': s.codigo_solicitante,
                'nombre_solicitante': s.nombre_solicitante,
                'cargo_solicitante': s.cargo_solicitante,
                'turno_solicitante_original': s.turno_solicitante_original,
                'turno_solicitante_nuevo': s.turno_solicitante_nuevo,
                'fecha_solicitud_cambio': s.fecha_solicitud_cambio,
                'codigo_receptor': s.codigo_receptor,
                'nombre_receptor': s.nombre_receptor,
                'cargo_receptor': s.cargo_receptor,
                'turno_receptor_original': s.turno_receptor_original,
                'turno_receptor_nuevo': s.turno_receptor_nuevo,
                'estado_cambio_admin': s.estado_cambio_admin
            })

        return Response({
            "data":data
        })
    elif codigoSolicitante is not None and estado is None:
        solicitudesCambiosTurnos = Cambios_de_turnos.objects.filter((Q(codigo_solicitante= codigoSolicitante) | Q(codigo_receptor = codigoSolicitante ))).only('codigo_solicitante', 'nombre_solicitante', 'cargo_solicitante',
            'turno_solicitante_original','turno_solicitante_nuevo','fecha_solicitud_cambio',
            'codigo_receptor','nombre_receptor','cargo_receptor','turno_receptor_original','turno_receptor_nuevo','estado_cambio_admin')
        data = []
        for s in solicitudesCambiosTurnos:
            data.append({
                'codigo_solicitante': s.codigo_solicitante,
                'nombre_solicitante': s.nombre_solicitante,
                'cargo_solicitante': s.cargo_solicitante,
                'turno_solicitante_original': s.turno_solicitante_original,
                'turno_solicitante_nuevo': s.turno_solicitante_nuevo,
                'fecha_solicitud_cambio': s.fecha_solicitud_cambio,
                'codigo_receptor': s.codigo_receptor,
                'nombre_receptor': s.nombre_receptor,
                'cargo_receptor': s.cargo_receptor,
                'turno_receptor_original': s.turno_receptor_original,
                'turno_receptor_nuevo': s.turno_receptor_nuevo,
                'estado_cambio_admin': s.estado_cambio_admin
            })
    
        return Response({
            "data":data})
    else:
        return Response({
            "success":False,
            "message": f"Error de parametros, codigoSolicitante: {codigoSolicitante} - estado: {estado}"
        })

@api_view(["POST"])
def confirmacionLectura(request):
    codigo = request.data.get("codigo")
    idArchivo = request.data.get("idArchivo")

    hoy = datetime.now(ZoneInfo("America/Bogota"))

    if codigo and idArchivo :
        if Empleado_Oddo.objects.filter(codigo = codigo,  estado = "Activo").exists() and Archivos.objects.filter(id = idArchivo).exists():
            empleado = Empleado_Oddo.objects.filter(codigo = codigo,  estado = "Activo").first()
            comunicado = Archivos.objects.filter(id = idArchivo).first()

            ConfirmacionLectura.objects.create(fechaLectura = hoy , codigo = codigo, cedula =  empleado.cedula, 
                                               nombre = empleado.nombre, archivos = comunicado, empleado = empleado, confirmacionLectura = "leido")
            
            return Response({"success":True, "message": f"Comunicado con id: {idArchivo}, leido por: { empleado.nombre }"})
        else:
            return Response({"success":False, "message": f"No existe comunicado: {idArchivo} ó empleado con estos datos: {codigo}"})    
        
    else:
        return Response({"success":False, "message":f"Error de parametros, codigo: {codigo} - {idArchivo} "})
    

@api_view(["POST"])
def insertarRespuesta(request):

    idSolicitudGt = request.data.get("idSolicitudGt")
    respuesta = request.data.get("respuesta")
    fechaRespuesta = datetime.today().astimezone(ZoneInfo("America/Bogota"))

    print(fechaRespuesta)

    if idSolicitudGt and respuesta:

        solicitud = Solicitudes_Gt.objects.get(id = idSolicitudGt)
        solicitud.respuestas.create(respuesta = respuesta, fechaRespuesta = fechaRespuesta)

        #Respuesta_Solicitudes_Gt.objects.create(idSolicitud = idSolicitudGt, respuesta = respuesta, fechaRespuesta = fechaRespuesta)
        return Response({"success": True, "message":f"Se registro correctamente la respuesta a la solicitud con id: {idSolicitudGt}"})
    else:
        return Response({"success":True, "message":f"Error de parametros, id enviado: {idSolicitudGt}, respuesta: {respuesta}"})
    

@api_view(["GET"])
def getRespuesta(request):

    idSolicitudGt = request.GET.get("idSolicitudGt")
    bogota = ZoneInfo('America/Bogota')
    data = []

    if idSolicitudGt is not None:
       if Respuesta_Solicitudes_Gt.objects.filter(solicitud_id = idSolicitudGt).exists():
        respuestas =  Respuesta_Solicitudes_Gt.objects.filter(solicitud_id = idSolicitudGt).order_by('-fechaRespuesta')

        for r in respuestas:
            data.append({
                "idSolicitud":r.solicitud.id,
                "fechaRespuesta": timezone.localtime( r.fechaRespuesta, bogota).strftime('%Y-%m-%d %H:%M'),
                "respuesta": r.respuesta
            })
            

        return Response(data)
       
    return Response(data)

CONTENT_TYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
@api_view(["GET"])
def descargarInformeGt(request):

    fechaInicial  = request.GET.get("fechaInicialFormateada")
    fechaFinal = request.GET.get("fechaFinalFormateada")
    estado = request.GET.get("opcionSeleccionada")
    tipoSolicitud = request.GET.get("opcionTipoSolicitud")

    print(f"Fecha inicial:{fechaInicial}, fecha final:{fechaFinal}, tipo solicitud:{tipoSolicitud}, estado:{estado}")
    data = []

    if fechaInicial and fechaFinal and estado and tipoSolicitud:

        fechaInicialFormateada = datetime.strptime(fechaInicial,"%Y/%m/%d").date()
        fechaFinalFormateada = datetime.strptime(fechaFinal, "%Y/%m/%d").date()
        solicitudes = None
        

        if estado in ["aprobado","desaprobado","pendiente"] and tipoSolicitud in ["PERMISO ACADEMICO","PERMISO PERSONAL"]:
            print("caso 1")
            solicitudes = Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicialFormateada, fecha_final__lte = fechaFinalFormateada, estado = estado, tipo_solicitud = tipoSolicitud).values('empleado__nombre','empleado__codigo','cargo',                                                                                                 
                'tipo_solicitud','fecha_solicitud','fecha_inicial','fecha_final','estado','descripcion')
            print(solicitudes)
        elif tipoSolicitud in ["PERMISO ACADEMICO","PERMISO PERSONAL"] and estado == "todo":
            solicitudes = Solicitudes_Gt.objects.select_related("empleado").filter(fecha_inicial__gte = fechaInicialFormateada, fecha_final__lte = fechaFinalFormateada, tipo_solicitud = tipoSolicitud).values('empleado__nombre','empleado__codigo','cargo',                                                                                                 
                'tipo_solicitud','fecha_solicitud','fecha_inicial','fecha_final','estado','descripcion')
        elif estado == "todo" and tipoSolicitud == "todo":
            solicitudes = Solicitudes_Gt.objects.select_related("empleado").filter(fecha_inicial__gte = fechaInicialFormateada, fecha_final__lte = fechaFinalFormateada).values('empleado__nombre','empleado__codigo','cargo',
                'tipo_solicitud','fecha_solicitud','fecha_inicial','fecha_final','estado','descripcion')
        elif tipoSolicitud == "todo" and estado in ["aprobado","desaprobado","pendiente"]:
            solicitudes = Solicitudes_Gt.objects.select_related("empleado").filter(fecha_inicial__gte = fechaInicialFormateada, fecha_final__lte = fechaFinalFormateada, estado = estado).values('empleado__nombre','empleado__codigo','cargo',
                'tipo_solicitud','fecha_solicitud','fecha_inicial','fecha_final','estado','descripcion')
        else:
            return Response({"success":False})

        if solicitudes is not None:
            for s in solicitudes:
                data.append({
                    "nombre": s.get("empleado__nombre"),
                    "codigo":s.get("empleado__codigo"),
                    "cargo":s.get("cargo"),
                    "tipo_solicitud": s.get("tipo_solicitud"),
                    "fecha_solicitud":s.get("fecha_solicitud"),
                    "fecha_inicial": s.get("fecha_inicial"),
                    "fecha_final": s.get("fecha_final"),
                    "estado": s.get("estado"),
                    "descripcion": s.get("descripcion") 
                })
        
            if len(data)> 0:
                #cols = ["Nombre", "Codigo","Cargo","Tipo_solicitud","Fecha_solicitud","Fecha_inicial","Fecha_final","Estado","Descripcion"]
                df = pd.DataFrame(data)
                #df = df.reindex(columns=cols)

                buf = BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Solicitudes")
                    ws = writer.book["Solicitudes"]
                    ws.auto_filter.ref = ws.dimensions
                    ws.freeze_panes = "A2"

                buf.seek(0)
                resp = HttpResponse(buf.read(), content_type=CONTENT_TYPE_XLSX)
                resp["Content-Disposition"] = f'attachment; filename="solicitudesGT-{fechaInicial}-{fechaFinal}.xlsx"'
                # Para que el front pueda leer el nombre de archivo vía JS en CORS:
                resp["Access-Control-Expose-Headers"] = "Content-Disposition"
                
                return resp
            else:
                return Response({"success": False, "detail": "Sin datos para el rango/estado/tipo."})
        else:
            return Response({"success":False})
    else:
        return Response({"success":False})

        
@api_view(["GET"])
def misSolicitudesGT(request):

    codigo = request.GET.get("codigo")
    idSolicitud = request.GET.get("id")
    cedula = request.GET.get("cedula")

    data = []
    if codigo is not None and cedula is not None and idSolicitud is None:
        solicitudes =  Solicitudes_Gt.objects.filter(empleado__codigo = codigo, empleado__cedula = cedula)
        for s in solicitudes:
            data.append({
                "idSolicitud": s.id,
                "nombre": s.empleado.nombre,
                "codigo":s.empleado.codigo,
                "cargo": s.cargo,
                "tipo_solicitud": s.tipo_solicitud,
                "fecha_solicitud": s.fecha_solicitud,
                "fecha_inicial": s.fecha_inicial,
                "fecha_final": s.fecha_final,
                "estado": s.estado,
                "descripcion": s.descripcion,
                "urlArchivo": s.urlArchivo,
            })
        return Response(data)
    elif idSolicitud is not None and codigo is None:
        solicitudes =  Solicitudes_Gt.objects.filter(id = idSolicitud)
        for s in solicitudes:
            data.append({
                "idSolicitud": s.id,
                "nombre": s.empleado.nombre,
                "codigo":s.empleado.codigo,
                "cargo": s.cargo,
                "tipo_solicitud": s.tipo_solicitud,
                "fecha_solicitud": s.fecha_solicitud,
                "fecha_inicial": s.fecha_inicial,
                "fecha_final": s.fecha_final,
                "estado": s.estado,
                "descripcion": s.descripcion
            })
        return Response(data)
    else:
        return Response({"success":True, "message":f"Codigo: {codigo} Y id: {idSolicitud} vacios"})
    

@api_view(["GET"])
def getTodosComunicados(request):

    if request.method == "GET":

        try:
            archivos = Archivos.objects.all().order_by('-fechaCarga')[:30]
        except:
            return Response({"success":False, "message": "No existen comunicados"})

        data = []
        for a in archivos:
            data.append({
                "id": a.id,
                "titulo": a.titulo,
                "usuarioCarga": a.usuarioCarga,
                "tipoComunicado": a.tipoComunicado,
                "fechaVigencia":a.fechaVigencia,
                "fechaCarga":a.fechaCarga,
                "cargoVisualizacion": a.cargoVisualizacion,
                "urlArchivo":a.urlArchivo,
                "tipoArchivo":a.tipoArchivo,
                "vistos": ConfirmacionLectura.objects.filter(archivos_id = a.id, confirmacionLectura = "leido").count()
            })
        return Response({"success":True, "comunicados": data})
    else:
        return Response({"success":False, "comunicados": "error"})

@api_view(["GET"])   
def getSolicitudesCambiosTurnos(request):

    codigo = request.GET.get("codigo")
    fecha_solicitud_cambio = request.GET.get("fechaCambio")
    rol = None
    solicitudes = None

    print(f"codigo: {codigo}, fecha cambio: {fecha_solicitud_cambio}")

    if codigo is None and fecha_solicitud_cambio is None:
        return Response({"success":False, "message":"Parametros vacios"})
    
    if Cambios_de_turnos.objects.filter(codigo_solicitante = codigo, fecha_solicitud_cambio = fecha_solicitud_cambio).exists():
        rol = "solicitante"
        solicitudes = Cambios_de_turnos.objects.filter(codigo_solicitante = codigo, fecha_solicitud_cambio = fecha_solicitud_cambio)
    elif Cambios_de_turnos.objects.filter(codigo_receptor = codigo, fecha_solicitud_cambio = fecha_solicitud_cambio).exists():
        rol ="receptor"
        solicitudes = Cambios_de_turnos.objects.filter(codigo_receptor = codigo, fecha_solicitud_cambio = fecha_solicitud_cambio)
    else:
        rol = None

    if rol == None:
        return Response({"success":False, "message":f"No tienes solicitudes de cambios de turnos para esta fecha: {fecha_solicitud_cambio}"})

    datos = []

    for s in solicitudes:
        datos.append({
            "codigo_solicitante": s.codigo_solicitante,
            "nombre_solicitante": s.nombre_solicitante,
            "cargo_solicitante": s.cargo_solicitante,
            "formacion_solicitante": s.formacion_solicitante,
            "turno_solicitante_original": s.turno_solicitante_original,
            "turno_solicitante_nuevo": s.turno_solicitante_nuevo,
            "codigo_receptor": s.codigo_receptor,
            "nombre_receptor": s.nombre_receptor,
            "cargo_receptor": s.cargo_receptor,
            "formacion_receptor": s.formacion_receptor,
            "turno_receptor_original": s.turno_receptor_original,
            "turno_receptor_nuevo": s.turno_receptor_nuevo,
            "estado_cambio_emp": s.estado_cambio_emp,
            "estado_cambio_admin": s.estado_cambio_admin,
            "fecha_solicitud_cambio": s.fecha_solicitud_cambio,
            "comentarios": s.comentarios,
            "zonaSolicitante": s.zonaSolicitante,
            "zonaReceptor": s.zonaReceptor,
        })
        
    return Response({"success":True, "data":datos, "rol":rol})

@api_view(["POST"])
def cancelarSolicitudGt(request):
    idSolicitud = request.data.get("idSolicitud")
    if idSolicitud:
        if Solicitudes_Gt.objects.filter(id = idSolicitud).exists():
            Solicitudes_Gt.objects.filter(id = idSolicitud).delete()
        return Response({"success":True, "message": f"Se elimino correctamente la solicitud con id: {idSolicitud}"})
    else:
        return Response({"success":True, "message": f"El id de la solicitud esta vacio: {idSolicitud}"})
    


@api_view(["GET"])
def misSolicitudesCambiosTurnos(request):
    cedula = request.GET.get('cedula')
    if cedula:
        if Cambios_de_turnos.objects.filter(Q(cedula_solicitante = cedula) | Q(cedula_receptor = cedula)).exists():
            solicitudesCambios = []
            solicitudes = Cambios_de_turnos.objects.filter(Q(cedula_solicitante = cedula) | Q(cedula_receptor = cedula)).order_by('-fechaCambio')
            for c in solicitudes:
                solicitudesCambios.append({
                    "codigo_solicitante": c.codigo_solicitante,
                    "nombre_solicitante": c.nombre_solicitante,
                    "cedula_solicitante": c.cedula_solicitante,
                    "cargo_solicitante": c.cargo_solicitante,
                    "formacion_solicitante": c.formacion_solicitante,
                    "turno_solicitante_original": c.turno_solicitante_original,
                    "turno_solicitante_nuevo": c.turno_solicitante_nuevo,
                    "codigo_receptor": c.codigo_receptor,
                    "nombre_receptor": c.nombre_receptor,
                    "cedula_receptor": c.cedula_receptor,
                    "cargo_receptor": c.cargo_receptor,
                    "formacion_receptor": c.formacion_receptor,
                    "turno_receptor_original": c.turno_receptor_original,
                    "turno_receptor_nuevo": c.turno_receptor_nuevo,
                    "estado_cambio_emp": c.estado_cambio_emp,
                    "estado_cambio_admin": c.estado_cambio_admin,
                    "fecha_solicitud_cambio": c.fecha_solicitud_cambio,
                    "comentarios": c.comentarios,
                    "zonaSolicitante": c.zonaSolicitante,
                    "zonaReceptor": c.zonaReceptor,
                    "transportable_solicitante": c.transportable_solicitante,
                    "transportable_receptor": c.transportable_receptor
                })
            return Response({
                "success":True,
                "message": "Se cargaron correctamente las solicitudes"
            })
        else:
            return Response({
                "success":False,
                "message": "No tienes cambios de turnos por ahora"
            })
    else:
         return Response({
                "success":False,
                "message": f"Parametro vacio, cedula: {cedula}"
            })

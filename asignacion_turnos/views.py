from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CargarDocumentosForm, CargarSucesionOperadoresForm,CargarDatosProno
from django.contrib.auth import authenticate , login
from django.http import HttpResponse
from .resources import peticion_Oddo
from .resources.cargarSucesion import procesar_sucesion_multifila
from .resources.cargarCuadroTunos import procesar_cuadro_turnos
from .resources.validarExtension import validarExcel
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime
from django.conf import settings
from pathlib import Path



from datetime import datetime, timedelta, date
from django.utils import timezone

from django.db.models import Count
from rest_framework.decorators import api_view
from rest_framework.response import Response
from asignacion_turnos.models import Sucesion
from asignacion_turnos.models import Horario , Cambios_de_turnos, Estados_servicios,Empleado_Oddo, Parametros, Archivos, Solicitudes_Gt, Notificaciones, ConfirmacionLectura
from .resources.validarDescanso import validar_descanso
from .resources.registrarLog import send_log
from .resources.cargarArchivosBlob import upload_to_azure_blob
from .resources.enviarCorreoGmail import enviarCorreoGmail, enviarCorreoGmailHTML
from .resources.buscarErrores import leer_y_filtrar_excel
from .resources.peticion_Oddo import sincronizarDbEmpleados




@settings.AUTH.login_required
def vista_home(request,*, context):
    data = sincronizarDbEmpleados()
    return render(request,'account/home.html',{
        "success": data.get('success'),
        "recibidos": data.get('recibidos'),
        "validos": data.get('validos'),
        "sin_cedula": data.get('sin_cedula'),
        "creados": data.get('creados'),
        "actualizados": data.get('creados'),
        "tiempo_s": data.get('tiempo')
    })


@settings.AUTH.login_required
def vista_cargarSucesionOperador(request,*, context):

    usuarioLogeado = str(request.user).upper()
    sucesionOperadores = Sucesion.objects.all()
    resultadosCargarSucesion = None
    errores = []

    if request.method == "POST":
        form = CargarSucesionOperadoresForm(request.POST, request.FILES)
        accion = request.POST.get('action')
        if accion == "cargar":
            if form.is_valid():
                file_sucesion = form.cleaned_data.get('file_sucesion')
                if file_sucesion and validarExcel(file_sucesion):
                    total_sucesion, errores = procesar_sucesion_multifila(file_sucesion, request.user)
                    resultadosCargarSucesion = f"Se cargaron correctamente {total_sucesion} registros."
                    sucesionOperadores = Sucesion.objects.all()
                else:
                    form.add_error(None,"No se cargo ningun archivo o documento con extension invalida")
        elif accion == "publicar":
            Sucesion.objects.filter(estado_sucesion='revision').update(estado_sucesion='publicado')
            return redirect('sucesion_operadores')
    else:
        form = CargarSucesionOperadoresForm()
    
    return render(request,'account/cargar_sucesion_operadores.html',{
        'resultadosSucesion':resultadosCargarSucesion,
        'errores': errores,
        'datos_sucesion':sucesionOperadores,
        'usuarioLogeado': usuarioLogeado
        
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
    user_claims = context["user"]               
    usuarioLogeado = user_claims.get("name") or user_claims.get("preferred_username")
    if request.method == "GET":                                       #fecha_solicitud_cambio // datetime.date.today()
       cargarDatosSolicitudes =  Cambios_de_turnos.objects.all()
    return render(request,'account/cambios_turnos.html',{
        'resultadosCambiosTurnos':cargarDatosSolicitudes,
        'usuarioLogeado':usuarioLogeado
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
    
    if request.method == "GET":

        print("GET completo:", request.GET)

        fechaInicial_peticion = request.GET.get('fecha_inicio')
        fechaFinal_peticion = request.GET.get('fecha_fin')

        fechaInicial = None
        fechaFinal = None
    

        if fechaInicial_peticion and fechaFinal_peticion:

            #Formateamos las fechas para que evitar error de formato ---> Datetime
            fechaInicial = datetime.strptime(fechaInicial_peticion, "%Y-%m-%d").date()
            fechaFinal = datetime.strptime(fechaFinal_peticion, "%Y-%m-%d").date()

            print(f"fecha inicial {fechaInicial} fecha final: {fechaFinal}")

            solicitudesGt = Solicitudes_Gt.objects.filter(fecha_inicial__gte = fechaInicial, fecha_final__lte = fechaFinal)
         
            if solicitudesGt.exists():
                print("Si existen solicitudes entre estas fechas")
                return render(request,"account/solicitudes_gestion_turnos.html",{
                    "mensaje":f"Se cargaron {solicitudesGt.count()} solicitudes entre este rango de fechas: {fechaInicial}, {fechaFinal}",
                    "solicitudesGt":solicitudesGt
                })
            else: # Si no ingresa un rango de fechas donde existan solicitudes, se devuelven todas las solicitudes pendientes
                print("No existen solicitudes entre estas fechas")
                solicitudesGt = Solicitudes_Gt.objects.filter(estado = "pendiente")
                return render(request, "account/solicitudes_gestion_turnos.html",{
                    "mensaje:":f"No hay solicitudes para este rango de fechas: {fechaInicial} , {fechaFinal}",
                    "solicitudesGt": solicitudesGt
                })
        else:
            solicitudesGt = Solicitudes_Gt.objects.filter(estado = "pendiente")
            return render(request,"account/solicitudes_gestion_turnos.html",{
                "mensaje:":f"No hay solicitudes para este rango de fechas: {fechaInicial} , {fechaFinal}",
                "solicitudesGt":solicitudesGt
            })
    else:
        return Response("error de peticion") # Corregir esto
    
@settings.AUTH.login_required
def vista_notificaciones(request,*, context):
    if request.method == "GET":
        notificaciones = Notificaciones.objects.all()
        return render(request,"account/notificaciones.html",{
            "notificaciones": notificaciones
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

    filas = leer_y_filtrar_excel(f)  

    return render(request, "account/preCarga.html", {
        "form": form,
        "dfresultado": filas,
        "usuarioLogeado": usuarioLogeado
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
    idSolicitud = request.data.get("idSolicitud")
    estadoSolicitud = request.data.get("estadoSolicitud")
    if idSolicitud and estadoSolicitud:
        Solicitudes_Gt.objects.filter(id = idSolicitud).update(estado=estadoSolicitud)
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
    if not codigo:
        return Response({"error": "Se requiere el parámetro 'codigo'"}, status=400)
    
    turnos  = Sucesion.objects.filter(codigo = codigo).order_by('fecha')
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
    return Response(data)


#Devulve todos lo empleados con cargo: Conductor de trenes
#Consulta: http://localhost:8000/account/api/sucesion/?cargo=CONDUCTOR DE VEHICULOS DE PASAJEROS TIPO METRO
@api_view(["GET"])
def get_sucesion_cargo(request):
    
    cargo = request.GET.get('cargo','').strip() 

    if not cargo:
        return Response({"Error":"Parametro cargo es requerido"}, status=400)
    
    turnos = Sucesion.objects.filter(empleado__cargo=cargo, empleado__estado = "Activo")
    data = []
    for t in turnos:
        data.append({
            "nombre":t.nombre,
            "codigo":t.codigo,
            "fecha":t.fecha,
            "turno":t.codigo_horario,
            "estacion_ini":t.estado_inicio if t.estado_inicio  else  'Sin estación',
            "estacion_fin":t.estado_fin if t.estado_fin else 'Sin estación',
            "hora_ini":t.hora_inicio if t.hora_inicio else  'Sin hora',
            "hora_fin":t.hora_fin if t.hora_fin else  'Sin hora',
            "particularidades": t.horario.observaciones if t.horario and t.horario.observaciones else "Sin observaciones",
            "duracion":t.horario.duracion if t.horario and t.horario.duracion else "" 
        })
    return Response(data)

#Esta vista actualiza los detalles de un turno en el modelo Horario, por ejemplo: COD SRM548 -> modifica hora de inicio, final, estacion inicial, final y particularidades
@api_view(["POST"])
def actualizar_turno(request):

    turno = request.data.get('turno','').strip()
    data = request.data
    peticion = request.data.get('peticion')

    if not turno:
        return Response({"Success":False,
                         "message":f"No se encontro codigo"}, status=400)
    
    if peticion == "accesoRapido":
        print(peticion)

        horario = get_object_or_404(Horario, turno=turno) 
        horario.inilugar = data.get('inilugar') 
        horario.finallugar = data.get('finallugar')
        horario.inihora = data.get('inihora')
        horario.finalhora = data.get('finalhora')
        #horario.inicir = data.get('circulacionIni')
        #horario.finbalcir =  data.get('circulacionFin')
        #horario.duracion = data.get('duracion')
        horario.observaciones = data.get('observaciones')
        horario.save()

        # actulizamos la suce tambien
        Sucesion.objects.filter(codigo_horario = turno).update(estado_inicio = data.get('inilugar'), estado_fin = data.get('finallugar'), hora_inicio = data.get('inihora'), hora_fin = data.get('finalhora'))
        
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

    horaActual = datetime.now().time()
    parametros = Parametros.objects.first()

    horaInicial = parametros.hora_inicio_permitida_cambios
    horaFinal = parametros.hora_final_permitida_cambios

    print(f"Hora actual: {horaActual}, hora incial: {horaInicial} , hora final: {horaFinal}")

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

    empleado = Empleado_Oddo.objects.filter(codigo=codigoSolicitante , estado = "Activo").first()

    
    cargos10HorasDescanso = ["CONDUCTOR DE VEHICULOS DE PASAJEROS TIPO METRO","CONDUCTOR DE VEHICULOS DE PASAJEROS TIPO TRANVIA"]
    cargos8HorasDescanso = ["OPERADOR DE CONDUCCION","MANIOBRISTA TRENES","MANIOBRISTA TRANVIA"]

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
             "error": f"{sucesionSolicitanteDiaCambio.nombre} ,No es posible cambiar dias LIBRE, COMPE, CP, INCAPACI, SUSPENSI , CAFTA , MAN , FUNDA, VACACION"
        })
    
    SusecionEmpleado = Sucesion.objects.filter(codigo = codigoSolicitante , fecha = fechaAnterior).first()
    print(SusecionEmpleado.codigo_horario)

    if SusecionEmpleado.codigo_horario not in ["DISPO", "LIBRE","COMPE","CP"] and SusecionEmpleado.codigo_horario not in turnosInvalidados: #Turnos con codigo de horario = None
        print("Esta calculando las horas")
        horaFinalTurnoAnterior = datetime.combine(fechaAnterior, SusecionEmpleado.hora_fin) # Aca tenemos tanto la fecha, como la hora para calular las 10 despues
        #Creamos los filtros para comparar con los turnos en la sucesion siguiente
        filtroTurnos10Horas = horaFinalTurnoAnterior + timedelta(hours=10)
        filtroTurnos8Horas = horaFinalTurnoAnterior + timedelta(hours=8)

        sucesionDiaCambio = Sucesion.objects.filter(~Q(codigo_horario__in = turnosInvalidados) & ~Q(codigo = codigoSolicitante ), fecha= fechaCambio, empleado__cargo = empleado.cargo)
        sucesionFiltrada = []

        print(f"Filtro 10 horas inicia desde: {filtroTurnos10Horas} - filtro 8 horas inicia desde: {filtroTurnos8Horas}")
        
        if empleado.cargo in cargos10HorasDescanso:
            for t in sucesionDiaCambio:
                if t.hora_inicio is None: #Si es None en este caso es por que el turno es DISPO
                    print(t.codigo_horario)
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
                elif datetime.combine(fechaCambio, t.hora_inicio) >= filtroTurnos10Horas:
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
            
        elif empleado.cargo in cargos8HorasDescanso:
            for t in sucesionDiaCambio:
                if t.hora_inicio is None:
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
                elif datetime.combine(fechaCambio, t.hora_inicio) >= filtroTurnos8Horas:
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
            return Response({"success": False, "message": "Cargo no valido"})
    else: 
        print("el dia de ayer tiene un turno con horas none")
        sucesionDiaCambio = Sucesion.objects.filter(~Q(codigo_horario__in = turnosInvalidados) & ~Q(codigo = codigoSolicitante ), fecha= fechaCambio, empleado__cargo = empleado.cargo)
        sucesionFiltrada = []
        for s in sucesionDiaCambio:
            sucesionFiltrada.append({
                    "nombre":s.nombre,
                    "codigo":s.codigo,
                    "cargo":s.empleado.cargo,
                    "fecha":s.fecha,
                    "turno":s.codigo_horario,
                    "estacion_ini":s.estado_inicio if s.estado_inicio  else  'Sin estación',
                    "estacion_fin":s.estado_fin if s.estado_fin else 'Sin estación',
                    "hora_ini":s.hora_inicio if s.hora_inicio else  'Sin hora',
                    "hora_fin":s.hora_fin if s.hora_fin else  'Sin hora',
                    "particularidades": s.horario.observaciones if s.horario and s.horario.observaciones else "Sin observaciones",
                    "duracion":s.horario.duracion if s.horario and s.horario.duracion else "Sin duración" 
                    })
        
        return Response(sucesionFiltrada)
            
        



@api_view(["POST"])
def solicitar_cambio_turno(request):

    codigoSolicitante = request.data.get('codigoSolicitante')
    codigoReceptor = request.data.get('codigoReceptor')
    
    fechaCambio = datetime.strptime(request.data.get('fechaCambio'), "%Y/%m/%d")
    fechaAnterior = fechaCambio - timedelta(days=1)
    fechaSiguiente = fechaCambio + timedelta(days=1)

    #Modelo Empleado // validar que los empleados existen
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
        errores.append({
            "success": False,
            "mensaje": f"El empleado {solicitante.nombre} ya tiene una solicitud de cambio para la fecha {fechaCambio}"
        })

    if Cambios_de_turnos.objects.filter(codigo_receptor = codigoSolicitante, fecha_solicitud_cambio=fechaCambio).exists():
        errores.append({
            "success": False,
            "mensaje": f"El empleado {solicitante.nombre} ya tiene una solicitud de cambio para la fecha {fechaCambio}"
        })

    if Cambios_de_turnos.objects.filter(codigo_solicitante=codigoReceptor, fecha_solicitud_cambio=fechaCambio).exists():
        errores.append({
            "success": False,
            "mensaje": f"El empleado {receptor.nombre} ya tiene una solicitud de cambio para la fecha {fechaCambio}"
        })

    if Cambios_de_turnos.objects.filter(codigo_receptor = codigoReceptor, fecha_solicitud_cambio=fechaCambio).exists():
        errores.append({
            "success": False,
            "mensaje": f"El empleado {receptor.nombre} ya tiene una solicitud de cambio para la fecha {fechaCambio}"
        })

    if errores:
        return Response({
            "success": False,
            "errores": errores
        })


    solicitante_siguiente = None
    receptor_siguiente = None

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

    # Crear solicitud de cambio
    Cambios_de_turnos.objects.create(

        codigo_solicitante=codigoSolicitante,
        nombre_solicitante=solicitante_dia.nombre,
        turno_solicitante_original=solicitante_dia.codigo_horario,
        turno_solicitante_nuevo=receptor_dia.codigo_horario,
        cargo_solicitante=solicitante_dia.empleado.cargo,
        formacion_solicitante = solicitante.formacion,
        codigo_receptor=codigoReceptor,
        nombre_receptor=receptor_dia.nombre,
        turno_receptor_original=receptor_dia.codigo_horario,
        turno_receptor_nuevo=solicitante_dia.codigo_horario,
        cargo_receptor=receptor_dia.empleado.cargo,
        formacion_receptor = receptor.formacion, 
        fecha_solicitud_cambio=fechaCambio,
        estado_cambio_emp="pendiente"
    )

    
    #if noHaySucesionSiguienteSolicitante or noHaySucesionSiguienteReceptor:
     #   return Response({
      #      "success": True,
       #     "message": "Se registró correctamente la solicitud de cambio de turnos, sin embargo validar si hay conflicto con el siguiente turno una vez se cargue la sucesión"
        #})

    return Response({
        "success": True,
        "message": "Se registró correctamente la solicitud de cambio de turnos."
    })


@api_view(["POST"])
def aprobar_solicitudes_cambios_turnos(request):

    solicitudesAprobadas = []
    contadorSolicitudes = 0
    
    solicitudes = request.data.get('solicitudes')

    if solicitudes is not None:

        for solicitud in solicitudes:

            print(f"Solicitudes: fecha cambio : {solicitud['fechaCambio']} , codigo solicitante: {solicitud['codigoSolicitante']} , codigo receptor: {solicitud['codigoReceptor']}")

            print(f"Turno que el  solicitande necesita : {solicitud['turnoSolicitanteDiaDeseado']}, Turno que el receptor necesita: {solicitud['turnoReceptorDiaDeseado']} " )

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
                horario_relacion_receptor = Horario.objects.filter(turno=solicitud['turnoReceptorDiaDeseado']).first()
                Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'],
                                                horario = horario_relacion_receptor , estado_inicio = horario_relacion_receptor.inilugar, 
                                                estado_fin = horario_relacion_receptor.finallugar,
                                                hora_inicio = horario_relacion_receptor.inihora, hora_fin = horario_relacion_receptor.finalhora)
                
                Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], codigo_solicitante = solicitud['codigoSolicitante'], 
                codigo_receptor = solicitud['codigoReceptor'] ).update(estado_cambio_admin = "aprobado")
                
            elif solicitud['turnoReceptorDiaDeseado'] == "DISPO":
                print(f"El solicitante tiene el DISPO: {solicitud['turnoReceptorDiaDeseado']}") # DISPO:DISPO
                #Actualizar sucesión  del receptor
                Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario =solicitud['turnoReceptorDiaDeseado'],
                                                horario = None, 
                                                estado_inicio = None, 
                                                estado_fin = None,
                                                hora_inicio = None, 
                                                hora_fin = None)
                #Actualizar sucesión del solicitante.
                horario_relacion_solicitante = Horario.objects.filter(turno=solicitud['turnoSolicitanteDiaDeseado']).first()
                Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'], 
                                                horario = horario_relacion_solicitante, 
                                                estado_inicio = horario_relacion_solicitante.inilugar, 
                                                estado_fin = horario_relacion_solicitante.finallugar , 
                                                hora_inicio = horario_relacion_solicitante.inihora , 
                                                hora_fin = horario_relacion_solicitante.finalhora)
            else:
                print(f"NINGUNO DE LOS DOS TIENE DISPO")

                horario_relacion_receptor = Horario.objects.filter(turno = solicitud['turnoSolicitanteDiaDeseado'] ).first()
                Sucesion.objects.filter(codigo = solicitud['codigoSolicitante'], fecha=solicitud['fechaCambio']).update(codigo_horario =solicitud['turnoSolicitanteDiaDeseado'],
                                                horario = horario_relacion_receptor, estado_inicio = horario_relacion_receptor.inilugar , 
                                                estado_fin = horario_relacion_receptor.finallugar,hora_inicio = horario_relacion_receptor.inihora, hora_fin = horario_relacion_receptor.finalhora)
                
                horario_relacion_solicitante = Horario.objects.filter(turno = solicitud['turnoReceptorDiaDeseado']).first()
                Sucesion.objects.filter(codigo = solicitud['codigoReceptor'], fecha=solicitud['fechaCambio']).update(codigo_horario = solicitud['turnoReceptorDiaDeseado'], 
                                                horario = horario_relacion_solicitante, 
                                                estado_inicio = horario_relacion_solicitante.inilugar , 
                                                estado_fin = horario_relacion_solicitante.finallugar , 
                                                hora_inicio = horario_relacion_solicitante.inihora , 
                                                hora_fin = horario_relacion_solicitante.finalhora )
                
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

                contadorSolicitudes += 1

            return Response({
                "success":True,
                "message": f"Se aprobaron con exito: {contadorSolicitudes}, solicitudes de cambios de turnos"
            })

    return Response({
        "Error":"No se cargo ninguna solicitud"
        })
    

@api_view(["POST"])
def desaprobar_solicitudes_cambios(request):

    solicitudes = request.data.get('solicitudes') 
    
    if solicitudes: 
        for solicitud in solicitudes:

            empleadoSolicitante = Empleado_Oddo.objects.filter(codigo = solicitud['codigoSolicitante'], estado = "Activo").first()
            empleadoReceptor = Empleado_Oddo.objects.filter(codigo = solicitud['codigoReceptor'] , estado = "Activo").first()

            solicitudCambioTurno = get_object_or_404(Cambios_de_turnos, fecha_solicitud_cambio = solicitud['fechaCambio'], 
                                             codigo_solicitante = solicitud['codigoSolicitante'], 
                                             codigo_receptor = solicitud['codigoReceptor'])
            
            Cambios_de_turnos.objects.filter(fecha_solicitud_cambio = solicitud['fechaCambio'], 
                                             codigo_solicitante = solicitud['codigoSolicitante'], 
                                             codigo_receptor = solicitud['codigoReceptor'],
                                             ).update(estado_cambio_admin = "desaprobado")
            
            send_log(empleadoSolicitante.cedula, datetime.today(), "Rechazar solicitud",
                     f"Se rechazo la solicitud de cambio entre: {empleadoSolicitante.nombre}, cod: {empleadoSolicitante.codigo} y {empleadoReceptor.nombre}, cod: {empleadoReceptor.codigo}, para la fecha: {solicitud['fechaCambio']}",
                      "AppGestionTurnos","Update:estadoSolicitud", solicitudCambioTurno.id)
            
            return Response({
                "success":True,
                "message":f"Se desaprobo el cambio de turno entre: {solicitud['codigoSolicitante']} y {solicitud['codigoReceptor']}, para la fecha: {solicitud['fechaCambio']}",
            }, status=200)



@api_view(["POST"])
def solicitud_gt(request):

    print("Content-Type:", request.content_type)
    print("FILES keys:", list(request.FILES.keys()))
    print("DATA  keys:", list(request.data.keys()))

    codigoSolicitante = request.data.get('codigoSolicitante')
    tipo_solicitud = request.data.get('tipoSolicitud')
    fecha_solicitud = request.data.get('fechaSolicitud')
    fecha_inicial = request.data.get('fechaInicial')
    fecha_final = request.data.get('fechaFinal')
    descripcion = request.data.get('descripcion')
    archivo = request.FILES.get('archivo')

    validarSolicitudExistente = Solicitudes_Gt.objects.filter(codigo = codigoSolicitante, tipo_solicitud = tipo_solicitud, fecha_inicial = fecha_inicial, fecha_final = fecha_final).exists()

    #Aca validamos que no tenga solicitudes exactamente iguales
    if validarSolicitudExistente:
        return Response({"success":False, "message":f"Error, ya tienes un solicitud de: {tipo_solicitud}, entre estas fechas, inicial: {fecha_inicial}, fecha final: {fecha_final}"})
    
    #ACa validamos que el empleado este activo para generar la solicitud
    if Empleado_Oddo.objects.filter(codigo = codigoSolicitante,  estado = "Activo").exists() == False:
        return Response({
            "success":False,
            "message":f"Usted no se encuentra activo para realizar este tipo de peticiones"})
    
    if codigoSolicitante is not None:

        empleado = Empleado_Oddo.objects.filter(codigo = codigoSolicitante,  estado = "Activo").first()
        
        solicitud_gt = Solicitudes_Gt.objects.create(nombre = empleado.nombre, codigo = empleado.codigo, cargo = empleado.cargo, 
                                      tipo_solicitud = tipo_solicitud, fecha_solicitud = fecha_solicitud, 
                                      fecha_inicial = fecha_inicial , fecha_final = fecha_final, descripcion = descripcion)
        
    
        if archivo:
            nombreArchivo = archivo.name
            ext = Path(nombreArchivo).suffix.lower()
            nombreArchivoSolicitud = f"{solicitud_gt.tipo_solicitud}_{solicitud_gt.id}"
            urlArchivo = upload_to_azure_blob(archivo,nombreArchivoSolicitud,"solicitud_gt")
            solicitud_gt.urlArchivo = urlArchivo
            solicitud_gt.tipoArchivo = ext
            solicitud_gt.save()
            

        mensajeGmail = f"Te queremos informar que la solicitud {tipo_solicitud} con fecha de registro: {fecha_solicitud}, quedo registrada de manera correcta en nuestro sistema, el area de Gestión de turnos evaluara la solicitud, muchas gracias"
        asunto = f"Solicitud de Gestión de turnos - solicitud: {tipo_solicitud}"

        #enviarCorreoGmail("sbastianpp@gmail.com",mensajeGmail, asunto)
        #def enviarCorreoGmailHTML(destinatario, nombre, solicitud, fecha_registro, asunto="Estado de tu solicitud"):

        estadoEnvioCorreo = enviarCorreoGmailHTML("sbastianpp@gmail.com", empleado.nombre, tipo_solicitud, fecha_solicitud, asunto)
        fecha_notificacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if estadoEnvioCorreo:
            Notificaciones.objects.create(nombre = empleado.nombre, codigo = empleado.codigo, cargo = empleado.cargo, tipo_solicitud = tipo_solicitud,
                                      fecha_solicitud = fecha_solicitud, fecha_notificacion = fecha_notificacion, correo = "sbastianpp@gmail.com", medio = "Correo Electronico", estado = "Notificado")
            return Response({"success":True, "message":f"Se registro exitosamente la solicitud, {tipo_solicitud}, con fecha de reigstro:{fecha_solicitud}"})
        else:
            Notificaciones.objects.create(nombre = empleado.nombre, codigo = empleado.codigo, cargo = empleado.cargo, tipo_solicitud = tipo_solicitud,
                                      fecha_solicitud = fecha_solicitud, fecha_notificacion = fecha_notificacion, correo = "sbastianpp@gmail.com", medio = "Correo Electronico", estado = "No notificado")
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
    cargo = request.GET.get('cargo')

    print(f"codigo: {codigo}, cargo: {cargo}")
    #fechaVigencia= request.data.get('fechaVigencia')

    archivos = Archivos.objects.filter( Q(fechaVigencia__gte = datetime.today()) | Q(fechaVigencia__isnull=True))
    listaArchivos = []
    print(f"Cantidad de comunicados en la BD: {archivos.count()}")
    print(archivos)

    for filtro in archivos:
        if cargo in filtro.cargoVisualizacion:
            if not ConfirmacionLectura.objects.filter(codigo = codigo, archivos = filtro.id).exists():
                listaArchivos.append(f"id: {filtro.id}, url: {filtro.urlArchivo}, tipo de archivo: {filtro.tipoArchivo}")

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
    

    
#Cambio de turnos
#@api_view(["POST"])
#def cambio_turno(request):

    #codigoSolicitante = request.POST.get('codigoSolicante')
    #codigoReceptor = request.POST.get('codigoReceptor')
    #codigoTurnoSolicante = request.POST.get('codigoTurnoSolicitante')
    #codigoTurnoReceptor = request.POST.get('codigoTurnoReceptor')
    #fechaCambio = request.POST.get('fechaCambio')

    #Cambiar turno solicitante x receptor
    #Sucesion.objects.filter(codigo=codigoSolicitante).filter(fecha=fechaCambio).update(codigo_horario = codigoTurnoReceptor)
    #Cambiar turno receptor x solicitante
    #Sucesion.objects.filter(codigo=codigoReceptor).filter(fecha=fechaCambio).update(codigo_horario = codigoTurnoSolicante)

    





from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CargarDocumentosForm, CargarSucesionOperadoresForm
from django.contrib.auth import authenticate , login
from django.http import HttpResponse
from .resources.cargarSucesion import procesar_sucesion_multifila
from .resources.cargarCuadroTunos import procesar_cuadro_turnos
from .resources.validarExtension import validarExcel
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db.models import Q

from datetime import datetime, timedelta, date
from django.utils import timezone

from django.db.models import Count
from rest_framework.decorators import api_view
from rest_framework.response import Response
from asignacion_turnos.models import Sucesion
from asignacion_turnos.models import Horario , Cambios_de_turnos, Estados_servicios,Empleado_Oddo, Parametros
from .resources.validarDescanso import validar_descanso
from .resources.registrarLog import send_log


def vista_principal(request):
    return render(request, 'registration/login.html/')

@login_required
def vista_home(request):
    return render(request,'account/home.html')


@login_required
def vista_cargarSucesionOperador(request):

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

@login_required
def vista_cargarSucesionTrenes(request):

    resultadosCargarCuadro= None
    resultadosCargarSucesion= None
    sucesion_mas_particularidades = Sucesion.objects.select_related('horario').all()
    total_cuadroServicios = total_cuadroServiciosSabado = total_cuadroServiciosDomingo = total_cuadroServiciosEspecial = None
    erroresSabados = None
    erroresSemana =None
    erroresDomingos = None
    erroresEspecial = None

    
    errores =  []
    usuarioLogeado = str(request.user).upper()

    if request.method == 'POST':
        form = CargarDocumentosForm(request.POST, request.FILES)
        accion = request.POST.get('action')
        if accion == "cargar": 
            if form.is_valid():
                #Leer los cuadros de turnos y sucesión:
                file_cuadro = form.cleaned_data.get('file_cuadroServicios')
                file_cuadroServiciosSabado = form.cleaned_data.get('file_cuadroServiciosSabado')
                file_cuadroServiciosDomingo = form.cleaned_data.get('file_cuadroServiciosDomingo')
                file_cuadroServiciosEspecial = form.cleaned_data.get('file_cuadroServiciosEspecial') 
                file_sucesion = form.cleaned_data.get('file_sucesion')
                if not any((file_cuadro, file_cuadroServiciosSabado, file_cuadroServiciosDomingo, file_cuadroServiciosEspecial, file_sucesion)):
                    form.add_error(None,"Debe cargar al menos un archivo para procesar.")
                else:
                    if file_cuadro:
                        if validarExcel(file_cuadro):   
                            total_cuadroServicios,erroresSemana = procesar_cuadro_turnos(file_cuadro,request.user)

                    if file_cuadroServiciosSabado:
                        if validarExcel(file_cuadroServiciosSabado):
                            total_cuadroServiciosSabado,erroresSabados = procesar_cuadro_turnos(file_cuadroServiciosSabado,request.user)

                    if file_cuadroServiciosDomingo:
                        if validarExcel(file_cuadroServiciosDomingo):
                            total_cuadroServiciosDomingo,erroresDomingos = procesar_cuadro_turnos(file_cuadroServiciosDomingo,request.user)

                    if file_cuadroServiciosEspecial: 
                        if validarExcel(file_cuadroServiciosEspecial):
                            total_cuadroServiciosEspecial,erroresEspecial = procesar_cuadro_turnos(file_cuadroServiciosEspecial,request.user)
                            
                    if file_sucesion:
                        if validarExcel(file_sucesion):
                            total_sucesion, errores = procesar_sucesion_multifila(file_sucesion, request.user)
                            resultadosCargarSucesion = f"Se cargaron correctamente {total_sucesion} registros."
                            sucesion_mas_particularidades = Sucesion.objects.select_related('horario').all()

        elif accion == "publicar":
            Sucesion.objects.all().update(estado_sucesion = 'publicado') 
            print("Se realizaron los cambios en sucesion")
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
        'resultadosSucesion':resultadosCargarSucesion,
        'erroresSemana': erroresSemana,
        'erroresSabados': erroresSabados,
        "erroresDomingo": erroresDomingos,
        "erroresEspecial":erroresEspecial,
        'usuarioLogeado': usuarioLogeado,
        'datos_sucesion':sucesion_mas_particularidades
    })

@login_required
def vista_configuraciones(request):

    if request.method == "GET":
        if Parametros.objects.all() is not None and Estados_servicios is not None:
            parametrosGestionTurnos = Parametros.objects.all()
            estadosServicios = Estados_servicios.objects.all()
        return render(request, 'account/configuraciones.html/',{
            "parametrosGestionTurnos": parametrosGestionTurnos,
            "estadosServicios": estadosServicios
        })
    else:
        return Response({"success":False , "message":"Error de peticion"})
        

@login_required
def get_solicitudes_cambios_turnos(request):
    usuarioLogeado = str(request.user).upper()
    if request.method == "GET":
       cargarDatosSolicitudes =  Cambios_de_turnos.objects.all()
    return render(request,'account/cambios_turnos.html',{
        'resultadosCambiosTurnos':cargarDatosSolicitudes,
        'usuarioLogeado':usuarioLogeado
        })
    
@login_required
def editar_horario(request):

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


@login_required
def vista_cargarIo(request):
    if request.method == "GET":
        usuarioLogeado = str(request.user).upper()
        return render(request,'account/cargarInstruccionesOperacionales.html',{
            "usuarioLogeado": usuarioLogeado
        })
        
# [ ------ API ------]

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
            "cargo":t.empleado.cargo,
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

    if not turno:
        return Response({"Success":False,
                         "message":f"No se encontro codigo"}, status=400)
    
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

    return Response({
        "success":True,
        "message": f"Turno: {turno}, actualizado correctamente"
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

    





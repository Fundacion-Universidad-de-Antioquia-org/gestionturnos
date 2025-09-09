from datetime import datetime , timedelta 
from asignacion_turnos.models import Horario, Estados_servicios, Sucesion
from django.http import HttpResponse
from django.http import JsonResponse 


# Estamos enviando los codigos de los turnos
def validar_descanso(anterior, cambio, posterior, cargo, fechaCambio):

    print(anterior , cambio , posterior , cargo , fechaCambio)

    fechaAnterior = fechaCambio - timedelta(days=1)
    fechaPosterior = fechaCambio + timedelta(days=1)

    cargos10HorasDescanso = ["CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO","CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO TRANVIA"]
    cargos8HorasDescanso = ["OPERADOR(A) DE CONDUCCION","MANIOBRISTA TRENES","MANIOBRISTA TRANVIA"]

    minimoDescanso10Horas = timedelta(hours=10)
    minimoDescanso8Horas = timedelta(hours=8)
    
    turnosSinValidacion = ["DISPO"]
    serviciosInvalidos = Estados_servicios.objects.all()
    for s in serviciosInvalidos:
        turnosSinValidacion.append(s.estado)  

    anteriorCumple = False
    posteriorCumple =False

    if anterior in turnosSinValidacion and posterior in turnosSinValidacion: # Aca no se valida ya que tanto el turno anterior como el siguiente no tienen hora ini u hora final
        anteriorCumple = True
        posteriorCumple = True
    
    elif anterior in turnosSinValidacion and posterior is None:
        anteriorCumple = True 
        posteriorCumple = True

    elif cambio == "DISPO":
        
        anteriorCumple = True
        posteriorCumple = True

    elif anterior not in turnosSinValidacion and posterior is None: 

        turnoAnterior = Sucesion.objects.filter(codigo_horario = anterior).first()
        turnoCambio = Sucesion.objects.filter(codigo_horario = cambio).first()

        dt1 = datetime.combine(fechaAnterior,turnoAnterior.hora_fin)
        dt2 = datetime.combine(fechaCambio,turnoCambio.hora_inicio)

        diferenciaAnteriorCambio = dt2 - dt1
        
        if cargo in cargos10HorasDescanso:
            if diferenciaAnteriorCambio >= minimoDescanso10Horas:
                anteriorCumple =True
                posteriorCumple = True
            else:
                anteriorCumple = False
                posteriorCumple = False
        elif cargo in cargos8HorasDescanso:
            if diferenciaAnteriorCambio >= minimoDescanso8Horas:
                    anteriorCumple =True
                    posteriorCumple = True
            else:
                anteriorCumple = False
                posteriorCumple = False
        else:
            return anteriorCumple, posteriorCumple
    
    elif anterior not in turnosSinValidacion and posterior in turnosSinValidacion: 

        turnoAnterior = Sucesion.objects.filter(codigo_horario = anterior).first()
        turnoCambio = Sucesion.objects.filter(codigo_horario = cambio).first()

        dt1 = datetime.combine(fechaAnterior,turnoAnterior.hora_fin)
        dt2 = datetime.combine(fechaCambio,turnoCambio.hora_inicio)

        diferenciaAnteriorCambio = dt2 - dt1
        
        if cargo in cargos10HorasDescanso:
            if diferenciaAnteriorCambio >= minimoDescanso10Horas:
                anteriorCumple =True
                posteriorCumple = True
            else:
                anteriorCumple = False
                posteriorCumple = False
        elif cargo in cargos8HorasDescanso:
            if diferenciaAnteriorCambio >= minimoDescanso8Horas:
                    anteriorCumple =True
                    posteriorCumple = True
            else:
                anteriorCumple = False
                posteriorCumple = False
        else:
            return anteriorCumple, posteriorCumple
        
    elif anterior not in turnosSinValidacion and posterior not in turnosSinValidacion:

        #diferencia de tiempo entre el anteriror y el de cambio:

        turnoAnterior = Sucesion.objects.filter(codigo_horario = anterior).first()
        turnoCambio = Sucesion.objects.filter(codigo_horario = cambio).first()
        turnoPosterior = Sucesion.objects.filter(codigo_horario = posterior).first()

        dt1 = datetime.combine(fechaAnterior,turnoAnterior.hora_fin)
        dt2 = datetime.combine(fechaCambio,turnoCambio.hora_inicio)
        diferenciaAnteriorCambio = dt2 - dt1

        #diferencia de tiempo entre el cambio y el posteriror.

        dt3 = datetime.combine(fechaCambio,turnoCambio.hora_fin)
        dt4 = datetime.combine(fechaPosterior, turnoPosterior.hora_inicio)
        diferenciaCambioPosteriror = dt4 - dt3
        
        if cargo in cargos10HorasDescanso:

            if diferenciaAnteriorCambio >= minimoDescanso10Horas and diferenciaCambioPosteriror >= minimoDescanso10Horas:
                anteriorCumple =True
                posteriorCumple = True
            else:
                anteriorCumple = False
                posteriorCumple = False

        elif cargo in cargos8HorasDescanso:
                
                if diferenciaAnteriorCambio >= minimoDescanso8Horas and diferenciaCambioPosteriror >= minimoDescanso8Horas:
                    anteriorCumple =True
                    posteriorCumple = True
                else:
                    anteriorCumple = False
                    posteriorCumple = False
        else:
            return anteriorCumple, posteriorCumple
    elif anterior in turnosSinValidacion and (posterior is not None and posterior not in turnosSinValidacion): #Anterior es DISPO, etc -> Posterior turno XXDF-457 - Solo calculamos posteriror
        
        turnoCambio = Sucesion.objects.filter(codigo_horario = cambio).first()
        turnoPosterior = Sucesion.objects.filter(codigo_horario = posterior).first()

        dt1 = datetime.combine(fechaCambio, turnoCambio.hora_fin)
        dt2 = datetime.combine(fechaPosterior, turnoPosterior.hora_inicio)

        diferenciaCambioPosteriror = dt2 - dt1

        if cargo in cargos10HorasDescanso:
            if diferenciaCambioPosteriror >= minimoDescanso10Horas:
                anteriorCumple = True
                posteriorCumple = True
            else:
                anteriorCumple = False
                posteriorCumple = False
        elif cargo in cargos8HorasDescanso:
            if diferenciaCambioPosteriror >= minimoDescanso8Horas:
                anteriorCumple = True
                posteriorCumple = True
            else:
                anteriorCumple = False
                posteriorCumple = False
        else: 
            anteriorCumple = False
            posteriorCumple = False
    else:
         return anteriorCumple , posteriorCumple

    print("Descanso dia anterior cumple:", anteriorCumple)
    print("Descanso dia Posterior cumple:", posteriorCumple)

    return anteriorCumple, posteriorCumple







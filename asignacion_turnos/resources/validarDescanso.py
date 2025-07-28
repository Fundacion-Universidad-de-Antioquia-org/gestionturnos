from datetime import datetime , timedelta
from asignacion_turnos.models import Horario
from django.http import HttpResponse
from django.http import JsonResponse 


# Estamos enviando los codigos de los turnos
def validar_descanso(anterior, cambio, posterior, cargo, fechaCambio):

    print(anterior , cambio , posterior , cargo , fechaCambio)

    fechaAnterior = fechaCambio - timedelta(days=1)
    fechaPosterior = fechaCambio + timedelta(days=1)

    cargos10HorasDescanso = ["CONDUCTOR DE VEHICULOS DE PASAJEROS TIPO METRO","CONDUCTOR DE VEHICULOS DE PASAJEROS TIPO TRANVIA"]
    cargos8HorasDescanso = ["OPERADOR DE CONDUCCION","MANIOBRISTA TRENES","MANIOBRISTA TRANVIA"]

    minimoDescanso10Horas = timedelta(hours=10)
    minimoDescanso8Horas = timedelta(hours=8)
    turnosSinValidacion = ["LIBRE","COMPE","CP","DISPO"]

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

    elif anterior not in turnosSinValidacion and posterior is None: # Aca solo calculamos el dia anteriro ya que el posterior es None y no tiene hora ini u hora final

        turnoAnterior = Horario.objects.filter(turno = anterior).first()
        turnoCambio = Horario.objects.filter(turno = cambio).first()

        dt1 = datetime.combine(fechaAnterior,turnoAnterior.finalhora)
        dt2 = datetime.combine(fechaCambio,turnoCambio.inihora)

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
            return JsonResponse({
                "success":False,
                "message": "No se encontro cargo o cargo invalido"
            })
        #Si no hay turno siguiente, posterior = None, entonces permitimos el valor para permitir el cambio ya que ho hay sucesion
    elif anterior not in turnosSinValidacion and posterior not in turnosSinValidacion and posterior != None:

        #diferencia de tiempo entre el anteriror y el de cambio:

        turnoAnterior = Horario.objects.filter(turno = anterior).first()
        turnoCambio = Horario.objects.filter(turno = cambio).first()
        turnoPosterior = Horario.objects.filter(turno = posterior).first()

        dt1 = datetime.combine(fechaAnterior,turnoAnterior.finalhora)
        dt2 = datetime.combine(fechaCambio,turnoCambio.inihora)
        diferenciaAnteriorCambio = dt2 - dt1

        #diferencia de tiempo entre el cambio y el posteriror.

        dt3 = datetime.combine(fechaCambio,turnoCambio.finalhora)
        dt4 = datetime.combine(fechaPosterior, turnoPosterior.inihora)
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
            return False, False
    else:
         return False , False

    print("Descanso dia anterior cumple:", anteriorCumple)
    print("Descanso dia Posterior cumple:", posteriorCumple)

    return anteriorCumple, posteriorCumple







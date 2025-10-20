import requests
from asignacion_turnos.models import Empleado_Oddo
import os
from dotenv import load_dotenv
from datetime import datetime
from django.conf import settings
from django.db import transaction


load_dotenv()
def autenticacionJwt():

    url = os.getenv("URL_SOLICITAR_TOKEN")
    data = {
        "username": os.getenv("USERNAME_LOGIN_TOKEN"),
        "password": os.getenv("PASSWORD_LOGIN_TOKEN")
    }
    response = requests.post(url,json = data)
    response.raise_for_status()
    tokens = response.json()

    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    return tokens["access"]

load_dotenv()
def _s(v):  # str seguro
    return "" if v is None else str(v).strip()

def sincronizarDbEmpleados():
   
    url_erp = os.getenv("URLERP")
    if not url_erp:
        return {"ok": False, "error": "Falta URLERP"}

    token = autenticacionJwt()
    resp = requests.get(url_erp, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    try:
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"ok": False, "error": f"HTTP {resp.status_code if resp else ''}: {e}"}

    data = resp.json() if resp.status_code == 200 else {}
    empleados = data.get("empleados", [])


    if not isinstance(empleados, list):
        return {"ok": False, "error": "La clave 'empleados' no es lista."}

    # Preparar objetos / update
    campos_upd = ["foto","nombre", "codigo", "estado", "cargo", "correo", "formacion","direccion","barrio","zona","fechaIngreso","universidad","carrera"]
    objs = []
    sin_cedula = 0
    for e in empleados:
      
        ced = _s(e.get("cedula"))
        if not ced:
            sin_cedula += 1
            continue
        objs.append(Empleado_Oddo(
            cedula=ced,
            foto = _s(e.get("foto_url")),
            nombre=_s(e.get("nombre")),
            codigo=_s(e.get("Codigo tripulante")),
            estado=_s(e.get("estado")),
            cargo=_s(e.get("job_title")),
            correo=_s(e.get("Correo personal")),
            formacion=_s(e.get("formacion_conduccion")),
            direccion = _s(e.get("address_home_id")),
            barrio = _s(e.get("Barrio")),
            municipio = _s(e.get("Municipio")),
            zona =_s(e.get("zona")),
            fechaIngreso = _s(e.get("x_studio_fecha_de_ingreso_1")),
            universidad = get_universidad(e),
            carrera = get_carrera(e)
        ))

    if not objs:
        return {"ok": True, "recibidos": len(empleados), "validos": 0, "sin_cedula": sin_cedula,
                "creados": 0, "actualizados": 0, "tiempo_s": 0.0}

    # Leer existentes una sola vez (conteo exacto)
    existentes_set = set(Empleado_Oddo.objects.values_list("cedula", flat=True))
    ya_existian = sum(1 for o in objs if o.cedula in existentes_set)
    creados_previstos = len(objs) - ya_existian  # exacto salvo concurrencia simultánea

    t0 = datetime.now()
    batch = 2000

    with transaction.atomic():
        for i in range(0, len(objs), batch):
            Empleado_Oddo.objects.bulk_create(
                objs[i:i+batch],
                update_conflicts=True,          # UPSERT
                unique_fields=["cedula"],       # campo único para conflicto
                update_fields=campos_upd,       # qué actualizar si existe
            )
            
            # print(f"[UPSERT] {min(i+batch, len(objs))}/{len(objs)}")

    dt = (datetime.now() - t0).total_seconds()
    return {
        "success": True,
        "recibidos": len(empleados),
        "validos": len(objs),
        "sin_cedula": sin_cedula,
        "creados": max(0, creados_previstos),
        "actualizados": max(0, ya_existian),
        "tiempo_s": round(dt, 2),
        "via": "upsert_nativo_pg_django5"
    }

def get_Cargo_Estado(codigo_empleado):
    try:
        emp = Empleado_Oddo.objects.get(codigo=codigo_empleado)
        empleado = {'cargo':emp.cargo,'estado':emp.estado}
    except Empleado_Oddo.DoesNotExist:
        empleado = {'cargo': None, 'estado': None}
    return empleado



def getOddo_traerCargo_Estado(codigo):
    
    url = 'https://erp-apps.fundacionudea.net/tasks/empleados/conduccion_codigo?codigo=130' 
    params = {'codigo': codigo}
    
    empleado = {'cargo':'', 'estado':''}
    
    try:
        response = requests.get(url, params)

        if response.status_code == 200:
            data = response.json()
            empleados = data['empleados']

            if isinstance(empleados, list):
                for i, emp in enumerate(empleados):
                    empleado['cargo'] = str(emp['job_title']).strip()
                    empleado['estado'] = str(emp['estado']).strip()
                    
                    print(f"[{i+1}] Codigo: {codigo} - {empleado['cargo']} - {empleado['estado']} ")
                    return empleado
            else:
                print('Error: "empleados" no es una lista')
        else:
            print(f'Error HTTP: {response.status_code}')

    except Exception as e:
        print(f'Excepción: {e}')

    return empleado



def get_universidad(e, sanitizer=_s):
   
    estudios = e.get("estudios")

    # Normalizar: permitir dict o lista; cualquier otra cosa => sin datos
    if estudios is None:
        return None
    if isinstance(estudios, dict):
        estudios = [estudios]
    if not isinstance(estudios, list):
        return None

    for item in estudios:
        if isinstance(item, dict):
            uni = item.get("universidad")
            if uni:
                return sanitizer(uni) if sanitizer else uni
    return None

def get_carrera(e, sanitizer=_s):
    estudios = e.get("estudios")

    if estudios is None:
        return None
    if isinstance(estudios, dict):
        estudios = [estudios]
    if not isinstance(estudios, list):
        return None

    for item in estudios:
        if isinstance(item, dict):
            carrera = item.get("carrera")
            if carrera:
                return sanitizer(carrera) if sanitizer else carrera
    return None


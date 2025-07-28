import requests
from asignacion_turnos.models import Empleado_Oddo
import os
from dotenv import load_dotenv


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
def getOddo_datos_empleados():
    
    urlErp = os.getenv("URLERP")
    print(f"URL ERP:  {urlErp}")
    token = autenticacionJwt()
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(urlErp, headers=headers)
    response.raise_for_status()

    try:
        if response.status_code == 200:
            datos = response.json()
            empleados = datos['empleados']

            #Insertar datos al modelo:
            if isinstance(empleados, list):
                for i, emp in enumerate(empleados):
                    try:
                        Empleado_Oddo.objects.update_or_create(
                            cedula =  str(emp['cedula']).strip(), defaults={
                            "nombre" : str(emp['nombre']).strip(),
                            "codigo": str(emp['Codigo tripulante']).strip(),
                            "estado" :str(emp['estado']).strip(),
                            "cargo": str(emp['job_title']).strip(),
                            "estado": str(emp['estado']).strip(),
                            #"zona":str(emp['zona']).strip(),
                            "formacion" : str(emp['formacion_conduccion']).strip()
                            })
                        print(f"[{i+1}] Insertado: {emp['cedula']} - {emp['nombre']}")
                    except Exception as e:
                        print(f"Error en el registro {i+1}: {e}")
                        print(f"Datos: {emp}")
            else:
                print(" ERROR: La respuesta no es una lista. Detalle:")
                
        else:
            print(f"Error en la petición: {response.status_code}")
            print(response.text)

    except requests.RequestException as e:
        print("Error al hacer la petición HTTP:", e)







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

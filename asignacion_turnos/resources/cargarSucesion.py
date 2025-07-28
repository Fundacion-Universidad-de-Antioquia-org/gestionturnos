import pandas as pd
from datetime import datetime, timedelta
from asignacion_turnos.models import Sucesion
from asignacion_turnos.models import Horario, Empleado_Oddo
from  asignacion_turnos.resources.peticion_Oddo import getOddo_datos_empleados


MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
}

def convertir_fecha(texto):
    try:
        partes = texto.split()
        mes_ini = partes[2].lower()
        dia_y_anio_ini = partes[3]
        mes_fin = partes[5].lower()
        dia_y_anio_fin = partes[6]

        dia_ini, anio_ini = dia_y_anio_ini.split('/')
        dia_fin, anio_fin = dia_y_anio_fin.split('/')

        fecha_ini = datetime.strptime(f"{anio_ini}-{MESES[mes_ini]}-{dia_ini}", "%Y-%m-%d")
        fecha_fin = datetime.strptime(f"{anio_fin}-{MESES[mes_fin]}-{dia_fin}", "%Y-%m-%d")
        return fecha_ini, fecha_fin
    except Exception as e:
        raise ValueError(f"Formato de fecha no reconocido: '{texto}' ({e})")



def procesar_sucesion_multifila(file, usuario):
   
    getOddo_datos_empleados()

    df = pd.read_excel(file, header=None)
    
    fecha_inicio = None
    total_cargadas = 0
    errores = []

    fila_semana = None
    for i, val in enumerate(df.iloc[:, 0]):
        if isinstance(val, str) and "Semana de" in val:
            fila_semana = i
            fecha_inicio, _ = convertir_fecha(val)
            break

    if fila_semana is None:
        errores.append("No se encontró fila con 'Semana de...'")
        return 0, errores

    inicio_datos = fila_semana + 4
    filas = df.shape[0]

    i = inicio_datos

    while i < filas:

        # BUSCAR siguiente fila válida
        while i < filas:
            fila1 = df.iloc[i]
            pos = fila1[0]
            nombre = fila1[1]
            codigo = fila1[2]

            # Si es la fila de encabezado ("POS", "NOMBRE", "COD"), saltarla
            if isinstance(pos, str) and "pos" in pos.lower():
                #print(f"Saltando encabezado en i={i}")
                i += 1
                continue

            # Si la fila es vacía o incompleta, saltarla
            if pd.isna(pos) or pd.isna(nombre) or pd.isna(codigo):
                #print(f"Saltando fila vacía o incompleta en i={i}")
                i += 1
                continue

            # --------- > Hasta aca procesa correctamente todos los datos <-----------------
            
            break

        fila1 = df.iloc[i]
        fila2 = df.iloc[i + 1] if i + 1 < filas else pd.Series([None] * df.shape[1])
        fila3 = df.iloc[i + 2] if i + 2 < filas else pd.Series([None] * df.shape[1])

        #if i + 2 < filas:
            #fila1 = df.iloc[i]
            #fila2 = df.iloc[i + 1]
            #fila3 = df.iloc[i + 2]
        #else:
            #fila1 = df.iloc[i]
            #fila2 = pd.Series([None] * df.shape[1])  # Fila vacía
            #fila3 = pd.Series([None] * df.shape[1])  # Fila vacía
            #print(f"Procesando último empleado incompleto en i={i} (faltan fila2 o fila3)")
            


        pos = fila1[0]
        nombreFormateado = str(fila1[1]).strip().upper()
        codigoFormateado = str(fila1[2]).strip().upper()
        #consulta_por_codigo = getOddo_traerCargo_Estado(codigoFormateado)
        
        #print(f"Leyendo datos  -  pos={pos}, nombre={nombre}, codigo={codigo}")

        


        try:
            for dia in range(7):
                col_base = 3 + dia * 3
                estado_inicio = fila1[col_base] if pd.notna(fila1[col_base]) else None
                codigo_horario = fila2[col_base + 1] if pd.notna(fila2[col_base + 1]) else None
                estado_fin = fila1[col_base + 2] if pd.notna(fila1[col_base + 2]) else None
                hora_inicio = fila3[col_base] if pd.notna(fila3[col_base]) else None
                hora_fin = fila3[col_base + 2] if pd.notna(fila3[col_base + 2]) else None
                codigoTurnoFormateado = str(codigo_horario).strip()

                horario_relacion = Horario.objects.filter(turno=codigoTurnoFormateado).first()
                empleado_relacion = Empleado_Oddo.objects.filter(codigo=codigoFormateado, estado="Activo").first() 
                print(f"Código horario original: '{codigo_horario}'")
                
                

                if Sucesion.objects.filter(
                    nombre=nombreFormateado,
                    codigo=codigoFormateado,
                    fecha=(fecha_inicio + timedelta(days=dia)).date()
                ).exists():
                    continue
                
                Sucesion.objects.create(
                    pos=int(pos),
                    nombre=str(nombre).strip(),
                    codigo=str(codigo).strip(),
                    cedula = str(empleado_relacion.cedula),
                    cargo = str(empleado_relacion.cargo),
                    fecha=(fecha_inicio + timedelta(days=dia)).date(),
                    estado_inicio=estado_inicio,
                    codigo_horario=codigo_horario,
                    estado_fin=estado_fin,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    usuario_carga=usuario,
                    estado_sucesion = 'revision',
                    horario = horario_relacion,
                    empleado = empleado_relacion

                    
                )
                total_cargadas += 1

            i += 3

            
        except Exception as e:
            errores.append(f"Error en filas {i}-{i + 2}: {e}")
            i += 3

            

    return total_cargadas, errores

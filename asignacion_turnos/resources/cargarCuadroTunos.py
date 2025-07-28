import pandas as pd
from asignacion_turnos.models import Horario

def convertir_a_time(valor):
    import datetime
    import pandas as pd

    if pd.isna(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.time()
    if isinstance(valor, datetime.time):
        return valor
    if isinstance(valor, str):
        return pd.to_datetime(valor, format='%H:%M', errors='coerce').time()
    return None

def procesar_cuadro_turnos(file, usuario):
    df = pd.read_excel(file, header=None)

    arr = {}
    total_cargadas = 0
    errores = []

    try:
        for i, value in enumerate(df.values):
            # Saltar filas vacías o encabezado "TURNO HORAS"
            if pd.isna(value[0]) or str(value[0]).strip().upper() == "TURNO" or str(value[0]).strip().upper().startswith("TURNOS"):
                continue
            
            if i == 2:
                arr["horario"] = str(value[1]).strip()  # Columna B (index 1)
                print(f"Nombre horario: {arr['horario']}")

            elif i == 4:
                try:
                    d1 = str(value[2]).strip()          # Fecha vigencia
                    d2 = str(value[10]).strip()         # Fecha implementación (columna K)
                    version_val = str(value[6]).strip() # Valor de la versión (columna G)

                    # Procesar fecha de vigencia
                    arr["fechavigencia"] = pd.to_datetime(d1, dayfirst=True, errors='raise').date()

                    # Procesar fecha de implementación
                    if d2:
                        fecha_impl = pd.to_datetime(d2, dayfirst=True, errors='coerce')
                        if pd.isna(fecha_impl):
                            errores.append("Fecha implementación no válida.")
                            arr["fechaimplementacion"] = None
                        else:
                            arr["fechaimplementacion"] = fecha_impl.date()
                    else:
                        errores.append("Fecha implementación vacía.")
                        arr["fechaimplementacion"] = None

                    # Procesar versión
                    arr["version"] = version_val

                    print(f"Fecha vigencia: {arr['fechavigencia']} - Fecha implementación: {arr['fechaimplementacion']} - Versión: {arr['version']}")

                    # Actualizar horario, eliminando el anteriror usando la el nombre horario, fecha vigencia y version
                    Horario.objects.filter(horario= arr["horario"], fechavigencia=arr["fechavigencia"], version=arr["version"]).delete()
                    print(f"Borrando registros para Horario: {arr['horario']}, {arr['fechavigencia']}, versión {arr['version']}")

                except Exception as e:
                    errores.append(f"Error leyendo fechas en fila 4: {e}")


            elif i >= 10:  
                #print(f"Intentando procesar fila i={i}, value[0]={value[0]}")
                try:
                    horario_obj = Horario(
                        horario=arr.get("horario"),
                        fechavigencia=arr.get("fechavigencia"),
                        fechaimplementacion=arr.get("fechaimplementacion"),
                        version=arr.get("version"),
                        turno=str(value[0]).strip(),
                        inihora=convertir_a_time(value[1]),
                        inilugar=str(value[2]).strip() if not pd.isna(value[2]) else None,
                        inicir=str(value[3]).strip() if not pd.isna(value[3]) else None,
                        deshora=convertir_a_time(value[4]),
                        deslugar=str(value[5]).strip() if not pd.isna(value[5]) else None,
                        desrelevo=str(value[6]).strip() if not pd.isna(value[6]) else None,
                        descir=str(value[7]).strip() if not pd.isna(value[7]) else None,
                        seghora=convertir_a_time(value[8]),
                        seglugar=str(value[9]).strip() if not pd.isna(value[9]) else None,
                        segcir=str(value[10]).strip() if not pd.isna(value[10]) else None,
                        finalhora=convertir_a_time(value[11]),
                        finallugar=str(value[12]).strip() if not pd.isna(value[12]) else None,
                        finalrelevo=str(value[13]).strip() if not pd.isna(value[13]) else None,
                        finbalcir=str(value[14]).strip() if not pd.isna(value[14]) else None,
                        duracion=str(value[15]).strip() if not pd.isna(value[15]) else None,
                        observaciones=str(value[16]).strip() if len(value) > 16 and not pd.isna(value[16]) else "",
                        usuario_carga=usuario,
                        fecha_carga=pd.Timestamp.now().date()
                    )
                    horario_obj.save()
                    #print(f"Guardado turno {value[0]}")
                    total_cargadas += 1

                except Exception as e:
                    print(f"Error procesando fila {i}: {e}")  
                    errores.append(f"Error procesando fila {i}: {e}")


    except Exception as e:
        errores.append(f"Error general en procesamiento: {e}")

    return total_cargadas, errores

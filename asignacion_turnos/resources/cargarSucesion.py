import re
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Q
import pandas as pd

from asignacion_turnos.models import Sucesion, Horario, Empleado_Oddo
# from asignacion_turnos.models import Estados_servicios  # si lo necesitas luego

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
}

SEMANA_RE = re.compile(
    r"Semana de\s+\w+\s+(\d{1,2}/\d{4})\s+a\s+\w+\s+(\d{1,2}/\d{4})",
    flags=re.IGNORECASE
)

def convertir_fecha(texto: str):
    """
    Acepta cadenas tipo:
    'Semana de Agosto 04/2025 a Agosto 10/2025'  (mes con palabras)
    o genéricas siempre que encajen al regex.
    """
    m = SEMANA_RE.search(texto)
    if not m:
        # fallback a tu parser original
        try:
            partes = texto.split()
            mes_ini = partes[2].lower()
            dia_y_anio_ini = partes[3]
            mes_fin = partes[5].lower()
            dia_y_anio_fin = partes[6]

            dia_ini, anio_ini = dia_y_anio_ini.split('/')
            dia_fin, anio_fin = dia_y_anio_fin.split('/')

            fecha_ini = datetime.strptime(f"{anio_ini}-{MESES[mes_ini]}-{int(dia_ini):02d}", "%Y-%m-%d")
            fecha_fin = datetime.strptime(f"{anio_fin}-{MESES[mes_fin]}-{int(dia_fin):02d}", "%Y-%m-%d")
            return fecha_ini, fecha_fin
        except Exception as e:
            raise ValueError(f"Formato de fecha no reconocido: '{texto}' ({e})")
    # Si matchea el regex, convierte DD/YYYY con el mes inferido del texto
    # Nota: el regex ya extrajo '04/2025' y '10/2025'; pero necesitamos el mes textual.
    # Para obtención robusta del mes textual, rebuscamos dentro del string original.
    partes = texto.split()
    mes_ini_txt = partes[2].lower()
    mes_fin_txt = partes[5].lower()
    dia_ini, anio_ini = m.group(1).split('/')
    dia_fin, anio_fin = m.group(2).split('/')

    fecha_ini = datetime.strptime(f"{anio_ini}-{MESES[mes_ini_txt]}-{int(dia_ini):02d}", "%Y-%m-%d")
    fecha_fin = datetime.strptime(f"{anio_fin}-{MESES[mes_fin_txt]}-{int(dia_fin):02d}", "%Y-%m-%d")
    return fecha_ini, fecha_fin


def _first_semana_row(df: pd.DataFrame):
    col0 = df.iloc[:, 0].astype(str)
    mask = col0.str.contains("Semana de", case=False, na=False)
    idx = mask.idxmax() if mask.any() else None
    return idx if (idx is not None and mask.loc[idx]) else None


def procesar_sucesion_multifila(file, usuario):
    # Lee sin adivinar tipos numéricos para evitar floats en códigos
    df = pd.read_excel(file, header=None, dtype=object)  # dtype=object evita sorpresas
    errores = []
    total_cargadas = 0

    fila_semana = _first_semana_row(df)
    if fila_semana is None:
        return 0, ["No se encontró fila con 'Semana de...'"]

    try:
        fecha_inicio, fecha_fin = convertir_fecha(str(df.iat[fila_semana, 0]))
    except Exception as e:
        return 0, [str(e)]

    # Precalcular rango de fechas de la semana
    fechas_semana = [(fecha_inicio + timedelta(days=d)).date() for d in range(7)]

    # 1) Prefetch de catálogos para eliminar consultas por iteración
    # Horarios por código de turno
    horarios_map = dict(Horario.objects.all().values_list('turno', 'id'))

    # Empleados activos por código
    empleados_qs = Empleado_Oddo.objects.filter(estado="Activo").values('codigo', 'id', 'cedula', 'cargo')
    empleados_map = {str(e['codigo']).strip().upper(): e for e in empleados_qs}

    # 2) Traer de una vez sucesiones ya existentes en la semana para saltarlas
    existentes = set(
        Sucesion.objects
        .filter(fecha__range=(fechas_semana[0], fechas_semana[-1]))
        .values_list('nombre', 'codigo', 'fecha')
    )

    # 3) Escanear filas de datos: empiezan 4 más abajo de "Semana de"
    inicio_datos = fila_semana + 4
    filas = df.shape[0]

    # Utilidad local para celda -> None/valor ya limpio
    def _val(x):
        return None if pd.isna(x) else x

    objetos_para_crear = []

    i = inicio_datos
    while i < filas:
        # Saltar encabezados y filas incompletas hasta encontrar una válida (POS, NOMBRE, COD)
        while i < filas:
            row = df.iloc[i]
            pos, nombre, codigo = row[0], row[1], row[2]

            # encabezado "POS"...
            if isinstance(pos, str) and 'pos' in pos.lower():
                i += 1
                continue

            if pd.isna(pos) or pd.isna(nombre) or pd.isna(codigo):
                i += 1
                continue
            break

        if i >= filas:
            break

        fila1 = df.iloc[i]
        fila2 = df.iloc[i + 1] if i + 1 < filas else pd.Series([None] * df.shape[1])
        fila3 = df.iloc[i + 2] if i + 2 < filas else pd.Series([None] * df.shape[1])

        try:
            # Normalizaciones que usaremos múltiples veces
            try:
                pos_int = int(str(fila1[0]).split('.')[0])  # por si viene como 12.0
            except Exception:
                pos_int = None

            nombre_fmt = str(fila1[1]).strip().upper()
            codigo_fmt = str(fila1[2]).strip().upper()

            empleado = empleados_map.get(codigo_fmt)
            # Si no está el empleado activo, crea igualmente la sucesión sin FK (evita reventar)
            empleado_id = empleado['id'] if empleado else None
            cedula_val = str(empleado['cedula']) if (empleado and empleado['cedula'] is not None) else None
            cargo_val = str(empleado['cargo']) if (empleado and empleado['cargo'] is not None) else None

            for dia in range(7):
                col_base = 3 + dia * 3
                estado_inicio = _val(fila1[col_base])
                codigo_horario = _val(fila2[col_base + 1])
                estado_fin = _val(fila1[col_base + 2])
                hora_inicio = _val(fila3[col_base])
                hora_fin = _val(fila3[col_base + 2])

                # Si no hay nada para ese día, continúa rápido
                if pd.isna(codigo_horario) and pd.isna(estado_inicio) and pd.isna(estado_fin) and pd.isna(hora_inicio) and pd.isna(hora_fin):
                    continue

                codigo_turno = str(codigo_horario).strip() if codigo_horario is not None else None
                fecha_dia = fechas_semana[dia]

                # Evitar re-consulta: checar en set existentes
                if (nombre_fmt, codigo_fmt, fecha_dia) in existentes:
                    continue

                horario_id = horarios_map.get(codigo_turno) if codigo_turno else None

                objetos_para_crear.append(
                    Sucesion(
                        pos=pos_int if pos_int is not None else 0,
                        nombre=nombre_fmt,        # ya en upper
                        codigo=codigo_fmt,        # ya en upper
                        cedula=cedula_val,
                        cargo=cargo_val,
                        fecha=fecha_dia,
                        estado_inicio=estado_inicio,
                        codigo_horario=(codigo_turno or ""),
                        estado_fin=estado_fin,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        usuario_carga=usuario,
                        estado_sucesion='revision',
                        # FKs por id para no cargar objetos
                        horario_id=horario_id,
                        empleado_id=empleado_id,
                    )
                )

            i += 3

        except Exception as e:
            errores.append(f"Error en filas {i}-{i + 2}: {e}")
            i += 3

    # 4) Inserción masiva
    if not objetos_para_crear:
        return 0, errores

    with transaction.atomic():
        # Si defines una restricción única (ver notas abajo), esto ignorará duplicados en carrera
        created = Sucesion.objects.bulk_create(
            objetos_para_crear,
            batch_size=1000,
            ignore_conflicts=True
        )
        total_cargadas = len(created)

    return total_cargadas, errores

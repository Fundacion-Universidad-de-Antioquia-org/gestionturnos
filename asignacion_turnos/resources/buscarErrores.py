import pandas as pd

def leer_y_filtrar_excel(file):
    # 1) Por si alguien ya leyó el archivo
    if hasattr(file, "seek"):
        try:
            file.seek(0)
        except Exception:
            pass

    # 2) Leer hoja 7 (índice 6)
    df = pd.read_excel(file, sheet_name=0)

    # 3) Normalizar cabeceras y helper case-insensitive
    df.columns = [str(c).strip() for c in df.columns]
    cols_map = {c.upper(): c for c in df.columns}

    def col(name, required=True):
        key = name.upper()
        if key in cols_map:
            return cols_map[key]
        if required:
            raise KeyError(f"Falta columna requerida: {name}. Presentes: {list(df.columns)}")
        return None

    FECHA    = col("FECHA")
    CUBIERTO = col("CUBIERTO")
    CODPER   = col("CODPER")
    NOMBRE   = col("NOMBRE", required=False)  # opcional

    # 4) Tipos y filtro
    df[FECHA] = pd.to_datetime(df[FECHA], errors="coerce")
    df = df.sort_values(by=FECHA, ascending=True)
    df = df[df[CUBIERTO].astype(str).str.contains("LIBRE|COMPE", case=False, na=False)]
    if df.empty:
        return []  # nada que mostrar

    # 5) Semanas (bloques de 7 días desde la mínima)
    fecha_inicial = df[FECHA].min().normalize()
    df["SEMANA"] = ((df[FECHA].dt.normalize() - fecha_inicial).dt.days // 7) + 1
    sem1 = df[df["SEMANA"] == 1]
    sem2 = df[df["SEMANA"] == 2]

    # 6) Empleados únicos
    empleados = df[CODPER].dropna().unique()

    resultados = []
    procesados = set()

    for empleado in empleados:
        if empleado in procesados:
            continue

        # Último descanso en semana 1 (max FECHA del empleado)
        f1 = sem1.loc[sem1[CODPER] == empleado, FECHA]
        # Primer descanso en semana 2 (min FECHA del empleado)
        f2 = sem2.loc[sem2[CODPER] == empleado, FECHA]

        if not f1.empty and not f2.empty:
            d1 = f1.max()
            d2 = f2.min()
            dias = (d2 - d1).days - 1
            if dias > 7:
                # Nombre tolerante
                nombre_val = ""
                if NOMBRE:
                    s = df.loc[df[CODPER] == empleado, NOMBRE]
                    if not s.empty:
                        nombre_val = str(s.iloc[0])

                # CEDULA como int/str JSON-safe
                try:
                    cedula_val = int(empleado)
                except Exception:
                    cedula_val = str(empleado)

                resultados.append({
                    "NOMBRE": nombre_val,
                    "CEDULA": cedula_val,
                    "DIAS_SIN_DESCANSO": int(dias),
                    "ESTADO": "Sobrepaso",
                    "DESCANSO_SEM1": str(d1.date()),
                    "DESCANSO_SEM2": str(d2.date()),
                })

        procesados.add(empleado)

    # 7) Devolver lista de dicts (JSON-ready)
    return resultados

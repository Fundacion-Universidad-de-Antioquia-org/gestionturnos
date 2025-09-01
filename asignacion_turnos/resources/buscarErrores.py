import pandas as pd
import unicodedata

def leer_y_filtrar_excel(file):
    # 1) Por si alguien ya leyó el archivo
    if hasattr(file, "seek"):
        try:
            file.seek(0)
        except Exception:
            pass

    
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
    NOMBRE   = col("NOMBRE", required=False)
    CODIGO = col("NMNIdentificadorDosNomina")


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

    print(empleados)

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
                codigo_val = ""

                if NOMBRE:
                    s = df.loc[df[CODPER] == empleado, NOMBRE]
                    if not s.empty:
                        nombre_val = str(s.iloc[0])
                
                if CODIGO:
                    c = df.loc[df[CODPER] == empleado, CODIGO]
                    if not c.empty:
                        codigo_val = str(c.iloc[0])
                # CEDULA como int/str JSON-safe
                try:
                    cedula_val = int(empleado)
                except Exception:
                    cedula_val = str(empleado)
                
                
                print(codigo_val)
                resultados.append({
                    "NOMBRE": nombre_val,
                    "CODIGO": codigo_val,
                    "CEDULA": cedula_val,
                    "DIAS_SIN_DESCANSO": int(dias),
                    "ESTADO": "Sobrepaso",
                    "DESCANSO_SEM1": str(d1.date()),
                    "DESCANSO_SEM2": str(d2.date()),

                })

        procesados.add(empleado)

    # 7) Devolver lista de dicts (JSON-ready)
    return resultados


def encontrarServiciosRepetidos(file):
    #dataset de los servicios de trenes y tranvia
    #df = pd.read_excel(file, sheet_name=2)

    df = pd.read_excel(file, sheet_name=1)
    dfServicios = pd.read_excel(file, sheet_name=2)

    #aca normalizamos las columnas
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
    NOMBRE   = col("NOMBRE", required=False)
    CODIGO = col("NMNIDENTIFICADORDOSNOMINA")
    RD_EQUIPO = col("RD_EQUIPO")

    #trenes
    dfServiciosSabado = dfServicios.iloc[:,"SABADO"]
    SERVICIOS_DOMINGO = dfServicios.iloc[:,"DOMINGO"]
    SERVICIOS_LUNES_VIERNES = dfServicios.iloc[:,"LUN-VIER"]

    
    df[FECHA] = pd.to_datetime(df[FECHA], errors="coerce")
    df = df.sort_values(by= FECHA , ascending=True)
    df = df[(df[RD_EQUIPO] >=1) & (df[RD_EQUIPO] <= 27)]

    turnosInvalidos = ["NOVED","COMPE","LIBRE","INDUC","CAFTA","DISPO","FUNDA","REIND"]

    df["DIA_NOMBRE"] = df[FECHA].dt.day_name(locale="es_ES").apply(quitar_tildes)
    df = df[~df[CUBIERTO].isin(turnosInvalidos)] # Excluir estos turnos


def diagnostico_servicios(
    file,
    hoja_asign: int = 1,
    hoja_catalogo: int = 2,
    cols_df: dict | None = None,
    cols_cat: dict | None = None,
    turnos_invalidos: list | None = None,
    equipo_rango: tuple | None = (1, 27),
    expand_lv: bool = True ) -> dict:
    """
    Diagnóstico de servicios: repetidos por día, faltantes, sobrantes y asignados no definidos.

    Parámetros:
    - file_path: ruta del Excel.
    - hoja_asign: índice de hoja con ASIGNACIONES (df) → p.ej. 1.
    - hoja_catalogo: índice de hoja con CATÁLOGO (dfServicios) → p.ej. 2.
    - cols_df: mapeo de columnas en df (asignaciones), p.ej.:
        {
          "fecha": "FECHA",
          "servicio": "CUBIERTO",        # clave del servicio a asignar
          "equipo": "RD_EQUIPO"          # (opcional) para filtrar rango
        }
      Si no se pasa, intenta resolver con esos nombres por defecto (case-insensitive).
    - cols_cat: mapeo de columnas del catálogo (dfServicios), p.ej.:
        {
          "sabado": "SERVICIOS_SABADO",
          "domingo": "SERVICIOS_DOMINGO",
          "lv": "SERVICIOS_LUN_VIE"
        }
      Si no se pasa, se usarán las 3 primeras columnas como sab/dom/lv en ese orden.
    - turnos_invalidos: lista de valores en df[servicio] a excluir (por defecto:
      ["NOVED","COMPE","LIBRE","INDUC","CAFTA","DISPO","FUNDA","REIND"])
    - equipo_rango: (min, max) para filtrar df[equipo]. Si None, no filtra.
    - expand_lv: si True, los servicios de Lunes-Viernes del catálogo se replican
      para cada día laboral (lu, ma, mi, ju, vi). Si False, se etiqueta como "lunes_viernes".

    Retorna:
    dict con:
      - df_asign: asignaciones normalizadas + DIA_NOMBRE
      - asig: conteo de asignadas por (DIA_NOMBRE, servicio)
      - esperados: esperados por (DIA_NOMBRE, servicio)
      - base: merge esperados vs asignadas con faltan/sobran
      - repetidos: (DIA_NOMBRE, servicio) con asignadas > 1
      - faltantes: faltan > 0
      - sobrantes: sobran > 0
      - asignados_no_definidos: asignaciones que no existen en catálogo del día
      - resumen_dia: totales por día
    """

    # -------- Helpers --------
    def quitar_tildes(s):
        if pd.isna(s): 
            return s
        s = str(s)
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    def normaliza_cols(df_):
        df_.columns = [str(c).strip() for c in df_.columns]
        return {c.upper(): c for c in df_.columns}

    def col(df_, cmap, name, required=True):
        key = name.upper()
        if key in cmap:
            return cmap[key]
        if required:
            raise KeyError(f"Falta columna requerida '{name}'. Presentes: {list(df_.columns)}")
        return None

    # -------- Lectura --------
    df = pd.read_excel(file, sheet_name=hoja_asign)
    dfServicios = pd.read_excel(file, sheet_name=hoja_catalogo)

    # -------- Normalización de columnas --------
    cmap_df = normaliza_cols(df)
    cmap_cat = normaliza_cols(dfServicios)

    # Columnas en df (asignaciones)
    cols_df = cols_df or {
        "fecha": "FECHA",
        "servicio": "CUBIERTO",
        "equipo": "RD_EQUIPO",   # opcional
    }
    FECHA = col(df, cmap_df, cols_df["fecha"], required=True)
    SERV  = col(df, cmap_df, cols_df["servicio"], required=True)
    EQUIPO = cols_df.get("equipo")
    EQUIPO = col(df, cmap_df, EQUIPO, required=False) if EQUIPO else None

    # Columnas en dfServicios (catálogo)
    if cols_cat:
        COL_SAB = col(dfServicios, cmap_cat, cols_cat["sabado"], required=True)
        COL_DOM = col(dfServicios, cmap_cat, cols_cat["domingo"], required=True)
        COL_LV  = col(dfServicios, cmap_cat, cols_cat["lv"], required=True)
    else:
        # Usa las 3 primeras columnas como sab/dom/lv
        if dfServicios.shape[1] < 3:
            raise ValueError("La hoja de catálogo debe tener al menos 3 columnas (sab, dom, lv) o pasar cols_cat.")
        COL_SAB, COL_DOM, COL_LV = dfServicios.columns[:3]

    # -------- Limpieza y features en df --------
    df[FECHA] = pd.to_datetime(df[FECHA], errors="coerce")
    # Orden por fecha
    df = df.sort_values(by=FECHA, ascending=True)

    # Filtro por equipo si procede
    if EQUIPO and equipo_rango:
        df[EQUIPO] = pd.to_numeric(df[EQUIPO], errors="coerce")
        lo, hi = equipo_rango
        df = df[(df[EQUIPO] >= lo) & (df[EQUIPO] <= hi)]

    # Excluir turnos inválidos
    if turnos_invalidos is None:
        turnos_invalidos = ["NOVED","COMPE","LIBRE","INDUC","CAFTA","DISPO","FUNDA","REIND"]

    # Normaliza servicio y día
    df[SERV] = df[SERV].astype(str).str.strip().str.upper()
    df["DIA_NOMBRE"] = df[FECHA].dt.strftime("%A").apply(quitar_tildes).str.lower()
    df = df[~df[SERV].isin(turnos_invalidos)]

    # -------- Normalización en catálogo --------
    for colname in [COL_SAB, COL_DOM, COL_LV]:
        dfServicios[colname] = dfServicios[colname].astype(str).str.strip().str.upper()

    # -------- 2) Asignaciones por (día, servicio) --------
    asig = (
        df.groupby(["DIA_NOMBRE", SERV], dropna=False)
          .size().rename("asignadas").reset_index()
    )
    repetidos = asig[asig["asignadas"] > 1].copy()

    # -------- 3) Esperados por (día, servicio) desde catálogo --------
    def vc(df_, col):
        # value_counts de una columna, ignorando vacíos
        return (df_[col]
                .replace("", pd.NA)
                .dropna()
                .value_counts()
                .rename_axis(SERV)
                .reset_index(name="esperados"))

    esp_sab = vc(dfServicios, COL_SAB)
    esp_sab["DIA_NOMBRE"] = "sabado"

    esp_dom = vc(dfServicios, COL_DOM)
    esp_dom["DIA_NOMBRE"] = "domingo"

    esp_lv_base = vc(dfServicios, COL_LV)

    if expand_lv:
        lv_days = ["lunes","martes","miercoles","jueves","viernes"]
        esp_lv = pd.concat(
            [esp_lv_base.assign(DIA_NOMBRE=d) for d in lv_days],
            ignore_index=True
        )
    else:
        esp_lv = esp_lv_base.assign(DIA_NOMBRE="lunes_viernes")

    esperados = pd.concat([esp_sab, esp_dom, esp_lv], ignore_index=True)

    # -------- 4) Comparar esperados vs asignadas --------
    base = esperados.merge(asig, how="left", on=["DIA_NOMBRE", SERV])
    base["asignadas"] = base["asignadas"].fillna(0).astype(int)

    base["faltan"] = (base["esperados"] - base["asignadas"]).clip(lower=0)
    base["sobran"] = (base["asignadas"] - base["esperados"]).clip(lower=0)

    faltantes = base[base["faltan"] > 0].sort_values(["DIA_NOMBRE", "faltan"], ascending=[True, False]).copy()
    sobrantes = base[base["sobran"] > 0].sort_values(["DIA_NOMBRE", "sobran"], ascending=[True, False]).copy()

    # -------- 5) Asignados que no existen en catálogo del día --------
    solo_asignados = asig.merge(
        esperados[["DIA_NOMBRE", SERV]],
        on=["DIA_NOMBRE", SERV],
        how="left", 
        indicator=True
    )
    asignados_no_definidos = solo_asignados[solo_asignados["_merge"] == "left_only"].copy()
    asignados_no_definidos = asignados_no_definidos.drop(columns=["_merge"])

    # -------- 6) Resumen por día --------
    resumen_dia = (
        base.groupby("DIA_NOMBRE", as_index=False)[["esperados","asignadas","faltan","sobran"]]
            .sum()
            .sort_values("DIA_NOMBRE")
    )

    # Resultado
    return {
        "df_asign": df.reset_index(drop=True),
        "asig": asig.sort_values(["DIA_NOMBRE", SERV]).reset_index(drop=True),
        "esperados": esperados.sort_values(["DIA_NOMBRE", SERV]).reset_index(drop=True),
        "base": base.sort_values(["DIA_NOMBRE", SERV]).reset_index(drop=True),
        "repetidos": repetidos.sort_values(["DIA_NOMBRE", "asignadas"], ascending=[True, False]).reset_index(drop=True),
        "faltantes": faltantes.reset_index(drop=True),
        "sobrantes": sobrantes.reset_index(drop=True),
        "asignados_no_definidos": asignados_no_definidos.sort_values(["DIA_NOMBRE", "asignadas"], ascending=[True, False]).reset_index(drop=True),
        "resumen_dia": resumen_dia.reset_index(drop=True),
        "columnas_usadas": {
            "df": {"FECHA": FECHA, "SERVICIO": SERV, "EQUIPO": EQUIPO},
            "catalogo": {"sabado": COL_SAB, "domingo": COL_DOM, "lv": COL_LV}
        }
    }


        
        



















def quitar_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )







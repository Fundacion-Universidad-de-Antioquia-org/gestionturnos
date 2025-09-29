import pandas as pd
import numpy as np
import unicodedata
from datetime import date, datetime


def sobreCargaLaboral(file):
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
    RD_EQUIPO = col("RD_EQUIPO")
    

    maskEquipoTrenes = df[RD_EQUIPO].between(1,29,inclusive="both")
    df["CARGO"] = np.where(maskEquipoTrenes, "CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO", "CARGO SIN ASIGNAR")

    
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
                cargo_val = ""

                if NOMBRE:
                    s = df.loc[df[CODPER] == empleado, NOMBRE]
                    cargo = df.loc[df[CODPER] == empleado, "CARGO"]
                    if not s.empty:
                        nombre_val = str(s.iloc[0])
                        cargo_val = str(cargo.iloc[0])
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
                    "CARGO":cargo_val,
                    "CODIGO": codigo_val,
                    "CEDULA": cedula_val,
                    "DIAS_SIN_DESCANSO": int(dias),
                    "ESTADO": "Sobrepaso",
                    "DESCANSO_SEM1": str(d1.date()),
                    "DESCANSO_SEM2": str(d2.date()),

                })

        procesados.add(empleado)

    return resultados


    df = pd.read_excel("REVISION 29-25.xlsx", sheet_name=1)
    dfServicios = pd.read_excel("REVISION 29-25.xlsx", sheet_name=2)

    # --- Normalización de encabezados y acceso seguro a nombres ---
    df.columns = [str(c).strip() for c in df.columns]
    cols_map = {c.upper(): c for c in df.columns}

    def col(name, required=True):
        key = name.upper()
        if key in cols_map:
            return cols_map[key]
        if required:
            raise KeyError(f"Falta columna requerida: {name}. Presentes: {list(df.columns)}")
        return None

    FECHA      = col("FECHA")
    CUBIERTO   = col("CUBIERTO")
    CODPER     = col("CODPER", required=False)
    RD_EQUIPO  = col("RD_EQUIPO")

    df["CARGO"] = "SIN CARGO"

    #Aca usamos los RD_EQUIPO para separar por cargos.
    mask_equipo = df[RD_EQUIPO].between(1,27, inclusive="both")
    df["CARGO"] = np.where(mask_equipo, "CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO",
                           "NO SE ENCONTRO CARGO CORRECTO")

    #Filtrar solo los de trenes
    df = df[(df[RD_EQUIPO] >= 1) & (df[RD_EQUIPO] <= 27)]
    # FECHA a datetime
    df[FECHA] = pd.to_datetime(df[FECHA], errors="coerce")

    # Excluir turnos no-asignables (ajusta si aplica)
    excluir = {"LIBRE","COMPE","NOVED","CAFTA","DISPO","INDUC","FUNDA","REIND"}
    df = df[~df[CUBIERTO].isin(excluir)].copy()

    # Día de la semana (sin depender de locales)
    dow = df[FECHA].dt.dayofweek  # 0=Lun ... 6=Dom
    df["DIA_SEMANA"] = dow.map({0:"LUNES",1:"MARTES",2:"MIERCOLES",3:"JUEVES",4:"VIERNES",5:"SABADO",6:"DOMINGO"})

    # --- Normalizaciones de texto ---
    def norm_ser(s):
        return (s.astype(str).str.strip().str.upper().str.replace(r"\s+", " ", regex=True))

    df[CUBIERTO] = norm_ser(df[CUBIERTO])

    # Conjuntos válidos por día-plantilla
    valid_lv  = set(norm_ser(dfServicios["LUNES-VIERNES"].dropna()))
    valid_sab = set(norm_ser(dfServicios["SABADO"].dropna()))
    valid_dom = set(norm_ser(dfServicios["DOMINGO"].dropna()))

    # --- Máscaras de día ---
    mask_lv  = dow.between(0,4)   
    mask_sab = dow.eq(5)
    mask_dom = dow.eq(6)

    # Estado asignación: 0=sin validar; 1=match plantilla; 2=duplicado en mismo día/servicio
    df["ESTADO_ASIGNACION"] = 0

    df.loc[mask_lv & df[CUBIERTO].isin(valid_lv), "ESTADO_ASIGNACION"] = 1
    df.loc[mask_sab & df[CUBIERTO].isin(valid_sab), "ESTADO_ASIGNACION"] = 1
    df.loc[mask_dom & df[CUBIERTO].isin(valid_dom), "ESTADO_ASIGNACION"] = 1
    #HASTA ACA ESTAMOS BIEN ---- 

    esperado_por_dia_lv = 0
    esperado_por_dia_s = 0
    esperado_por_dia_d = 0

    if df[mask_lv] is not None :
        esperado_por_dia_lv = dfServicios["LUNES-VIERNES"].count()
    elif df[mask_sab] is not None:
        esperado_por_dia_s = dfServicios["SABADO"]
    elif df[mask_dom] is not None:
        esperado_por_dia_d = dfServicios["DOMINGO"]
   
    asignado_por_dia = (
        df[(df["ESTADO_ASIGNACION"] == 1) & mask_lv]
          .groupby(df[FECHA]).size().rename("Servicios asignados")
    )

    print("INFORME DE ASIGNACION LUNES - VIERNES ")
    print(f"Servicios esperados: {esperado_por_dia_lv}")
    print(f"Servicios asignados:{df['ESTADO_ASIGNACION'].count()} ")
    print(asignado_por_dia)
   
    asignados_por_servicio = (
        df[(df["ESTADO_ASIGNACION"] == 1) & mask_lv]
          .drop_duplicates([FECHA, CUBIERTO])
          [CUBIERTO]
          .value_counts()  # número de días que se asignó ese servicio
    )

    mask_dup = df.duplicated(subset=[FECHA, CUBIERTO], keep=False)

    if mask_dup is not None:
        df_repetidos = df.loc[mask_dup].sort_values([FECHA, CUBIERTO])

        print("Servicios repetidos en la misma fecha \n", df_repetidos.head())

        df_subset = df_repetidos[[FECHA, NOMBRE, CODPER, ESTACION_ENT, ESTACION_SAL, RD_EQUIPO, CUBIERTO, "CARGO", "DIA_SEMANA"]]
        serviciosRepetidos = df_subset.to_json(orient="records", force_ascii=False)

        print(serviciosRepetidos)
 


    # SERVICIOS FALTANTES LUNES A VIERNES:
    dfServicios["TURNOS_ASIGNADOS_LUNES_VIERNES"] = 0
    
    servicios_en_sucesion = set(norm_ser(df[CUBIERTO].dropna()))
    dfServicios["TURNOS_ASIGNADOS_LUNES_VIERNES"] = norm_ser(dfServicios["LUNES-VIERNES"]).isin(servicios_en_sucesion).astype(int)

    print("\nTOTAL SERVICIOS L–V EN SUCESION (únicos):", len(servicios_en_sucesion))
    print("Asignados (únicos servicio-día, L–V):", asignado_por_dia.sum())

    canon_lv = set(dfServicios["LUNES-VIERNES"]
               .dropna()
               .astype(str).str.strip().str.upper())

    faltantes_por_dia = {}

    for fecha, sub in df[df["DIA_SEMANA"].isin(["LUNES","MARTES","MIERCOLES","JUEVES","VIERNES"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_lv - presentes)
        if faltan:
            faltantes_por_dia[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_por_dia.items():
        print(f, "faltan", len(lst), "-", lst[:10], "…")  # muestra los primeros 10

    #SERVICIOS FALTANTES SABADOS:
    print(f"Servicios esperados para el sabado: {dfServicios["SABADO"].count()}")
    dfServicios["TURNOS_ASIGNADOS_SABADO"] = 0

    canon_s = set(dfServicios["SABADO"]
               .dropna()
               .astype(str).str.strip().str.upper())

    faltantes_por_dia = {}

    for fecha, sub in df[df["DIA_SEMANA"].isin(["SABADO"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_s - presentes)
        if faltan:
            faltantes_por_dia[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_por_dia.items():
        print(f, "faltan", len(lst), "-", lst[:10], "…")  # muestra los primeros 10


    faltantes_por_dia = {}

    #SERVICIOS FALTANTES DOMINGOS & ASIGNADOS:
    print(f"Servicios esperados para el domingo {dfServicios["DOMINGO"].count()}")
    canon_d = set(dfServicios["DOMINGO"]
               .dropna()
               .astype(str).str.strip().str.upper())
    
    for fecha, sub in df[df["DIA_SEMANA"].isin(["DOMINGO"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_d - presentes)
        if faltan:
            faltantes_por_dia[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_por_dia.items():
        print(f, "faltan", len(lst), "-", lst[:100], "…")  # muestra los primeros 10

def sobreCargaLaboralTranvia(file):
    # 1) Por si alguien ya leyó el archivo
    if hasattr(file, "seek"):
        try:
            file.seek(0)
        except Exception:
            pass

    
    df = pd.read_excel(file, sheet_name=3)

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
    RD_EQUIPO = col("RD_EQUIPO")
    
    maskEquipoTranvia = df[RD_EQUIPO].between(30,36,inclusive="both")
    df["CARGO"] = np.where(maskEquipoTranvia, "CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO TRANVIA", "CARGO SIN ASIGNAR")

    
   #Aplicamos filtros
    df[FECHA] = pd.to_datetime(df[FECHA], errors="coerce")
    df = df.sort_values(by=FECHA, ascending=True)
    df = df[df[CUBIERTO].astype(str).str.contains("LIBRE|COMPE", case=False, na=False)]
    if df.empty:
        return []  

    #Semanas (bloques de 7 días desde la mínima)
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
                codigo_val = ""
                cargo_val = ""

                if NOMBRE:
                    s = df.loc[df[CODPER] == empleado, NOMBRE]
                    cargo = df.loc[df[CODPER] == empleado, "CARGO"]
                    if not s.empty:
                        nombre_val = str(s.iloc[0])
                        cargo_val = str(cargo.iloc[0])
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
                    "CARGO":cargo_val,
                    "CODIGO": codigo_val,
                    "CEDULA": cedula_val,
                    "DIAS_SIN_DESCANSO": int(dias),
                    "ESTADO": "Sobrepaso",
                    "DESCANSO_SEM1": str(d1.date()),
                    "DESCANSO_SEM2": str(d2.date()),

                })

        procesados.add(empleado)

    return resultados


def asignacionServicios(file):
    # 1) Por si alguien ya leyó el archivo / RESETEAR EL PUNTERO
    if hasattr(file, "seek"):
        try:
            file.seek(0)
        except Exception:
            pass
    
    df = pd.read_excel(file, sheet_name=1)
    dfServicios = pd.read_excel(file, sheet_name=2)

    # --- Normalización de encabezados y acceso seguro a nombres ---
    df.columns = [str(c).strip() for c in df.columns]
    cols_map = {c.upper(): c for c in df.columns}

    def col(name, required=True):
        key = name.upper()
        if key in cols_map:
            return cols_map[key]
        if required:
            raise KeyError(f"Falta columna requerida: {name}. Presentes: {list(df.columns)}")
        return None

    FECHA = col("FECHA")
    NOMBRE = col("NOMBRE")
    CUBIERTO  = col("CUBIERTO")
    CODPER = col("CODPER", required=False)
    CODIGO = col("NMNIdentificadorDosNomina")
    RD_EQUIPO  = col("RD_EQUIPO")
    ESTACION_ENT = col("ESTACION_ENT")
    ESTACION_SAL = col("ESTACION_SAL")

    df["CARGO"] = "SIN CARGO"

    #Aca usamos los RD_EQUIPO para separar por cargos.
    mask_equipoTrenes = df[RD_EQUIPO].between(1,29, inclusive="both")
    df["CARGO"] = np.where(mask_equipoTrenes, "CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO METRO",
                           "NO SE ENCONTRO CARGO")
    
    #mas_equipoTranvia = df[RD_EQUIPO].between(30,36, inclusive="both")
    #df["CARGO"] = np.where(mas_equipoTranvia,"CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO TRANVIA", "SIN CARGO ASIGNADO")

    #Filtrar solo los de trenes
    df = df[(df[RD_EQUIPO] >= 1) & (df[RD_EQUIPO] <= 27)]
    # FECHA a datetime
    df[FECHA] = pd.to_datetime(df[FECHA], errors="coerce")

    # Excluir turnos 
    excluir = {"LIBRE","COMPE","NOVED","CAFTA","DISPO","INDUC","FUNDA","REIND","ACTRAN","TPLC","PLCT"}
    df = df[~df[CUBIERTO].isin(excluir)].copy()

    # Día de la semana 
    dow = df[FECHA].dt.dayofweek  # 0=Lun ... 6=Dom
    df["DIA_SEMANA"] = dow.map({0:"LUNES",1:"MARTES",2:"MIERCOLES",3:"JUEVES",4:"VIERNES",5:"SABADO",6:"DOMINGO"})

    # --- Normalizaciones de texto ---
    def norm_ser(s):
        return (s.astype(str).str.strip().str.upper().str.replace(r"\s+", " ", regex=True))

    df[CUBIERTO] = norm_ser(df[CUBIERTO])

    # Conjuntos válidos por día-plantilla
    valid_lv  = set(norm_ser(dfServicios["LUNES-VIERNES"].dropna()))
    valid_sab = set(norm_ser(dfServicios["SABADO"].dropna()))
    valid_dom = set(norm_ser(dfServicios["DOMINGO"].dropna()))

    # --- Máscaras de día ---
    mask_lv  = dow.between(0,4)       # L–V
    mask_sab = dow.eq(5)
    mask_dom = dow.eq(6)

    # Estado asignación: 0=sin validar; 1=match plantilla; 2=duplicado en mismo día/servicio
    df["ESTADO_ASIGNACION"] = 0

    df.loc[mask_lv & df[CUBIERTO].isin(valid_lv), "ESTADO_ASIGNACION"] = 1
    df.loc[mask_sab & df[CUBIERTO].isin(valid_sab), "ESTADO_ASIGNACION"] = 1
    df.loc[mask_dom & df[CUBIERTO].isin(valid_dom), "ESTADO_ASIGNACION"] = 1
    #HASTA ACA ESTAMOS BIEN ---- 

    esperado_por_dia_lv = 0
    esperado_por_dia_s = 0
    esperado_por_dia_d = 0

    if df[mask_lv] is not None :
        esperado_por_dia_lv = dfServicios["LUNES-VIERNES"].count()
    elif df[mask_sab] is not None:
        esperado_por_dia_s = dfServicios["SABADO"]
    elif df[mask_dom] is not None:
        esperado_por_dia_d = dfServicios["DOMINGO"]
   
    asignado_por_dia = (
        df[(df["ESTADO_ASIGNACION"] == 1) & mask_lv]
          .groupby(df[FECHA]).size().rename("Servicios asignados")
    )

    print("INFORME DE ASIGNACION LUNES - VIERNES ")
    print(f"Servicios esperados: {esperado_por_dia_lv}")
    print(f"Servicios asignados:{df['ESTADO_ASIGNACION'].count()} ")
    print(asignado_por_dia)
   
    asignados_por_servicio = (
        df[(df["ESTADO_ASIGNACION"] == 1) & mask_lv]
          .drop_duplicates([FECHA, CUBIERTO])
          [CUBIERTO]
          .value_counts()  # número de días que se asignó ese servicio
    )

    mask_dup = df.duplicated(subset=[FECHA, CUBIERTO], keep=False)

    serviciosRepetidos = None

    if mask_dup is not None:
        df_repetidos = df.loc[mask_dup].sort_values([FECHA, CUBIERTO])
        print("Servicios repetidos en la misma fecha \n", df_repetidos.head())
        df_subset = df_repetidos[[FECHA, NOMBRE, CODPER, CODIGO, ESTACION_ENT, ESTACION_SAL, RD_EQUIPO, CUBIERTO, "CARGO", "DIA_SEMANA", "NMNIdentificadorDosNomina"]]

        serviciosRepetidos = df_subset.to_dict(orient="records")
        print(serviciosRepetidos)

    # SERVICIOS FALTANTES LUNES A VIERNES:
    dfServicios["TURNOS_ASIGNADOS_LUNES_VIERNES"] = 0
    
    servicios_en_sucesion = set(norm_ser(df[CUBIERTO].dropna()))
    dfServicios["TURNOS_ASIGNADOS_LUNES_VIERNES"] = norm_ser(dfServicios["LUNES-VIERNES"]).isin(servicios_en_sucesion).astype(int)

    print("\nTOTAL SERVICIOS L–V EN SUCESION (únicos):", len(servicios_en_sucesion))
    print("Asignados (únicos servicio-día, L–V):", asignado_por_dia.sum())

    canon_lv = set(dfServicios["LUNES-VIERNES"]
               .dropna()
               .astype(str).str.strip().str.upper())

    faltantes_por_dia_lunes_viernes = {}
    faltantes_lunes_viernes = []

    for fecha, sub in df[df["DIA_SEMANA"].isin(["LUNES","MARTES","MIERCOLES","JUEVES","VIERNES"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_lv - presentes)
        if faltan:
            faltantes_por_dia_lunes_viernes[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_por_dia_lunes_viernes.items():
        print(f, "faltan", len(lst), "-", lst[:10], "…")  
        faltantes_lunes_viernes.append({
            "fecha": to_iso_str(f),
            "rango":"LUNES-VIERNES",
            "cantidad":len(lst),
            "turnos":lst
        })
    
    print(f"SERVICIOS FALTANTES PARA LUNES A VIERNES: {len(faltantes_lunes_viernes)}")
    #SERVICIOS FALTANTES SABADOS:
    print(f"Servicios esperados para el sabado: {dfServicios["SABADO"].count()}")
    dfServicios["TURNOS_ASIGNADOS_SABADO"] = 0

    canon_s = set(dfServicios["SABADO"]
               .dropna()
               .astype(str).str.strip().str.upper())

    faltantes_sabado = {}
    faltantes_sabado_json = []

    for fecha, sub in df[df["DIA_SEMANA"].isin(["SABADO"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_s - presentes)
        if faltan:
            faltantes_sabado[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_sabado.items():
        #print(f, "faltan", len(lst), "-", lst[:10], "…") 
        faltantes_sabado_json.append({
            "fecha": to_iso_str(f),
            "rango": "SABADOS",
            "cantidad":len(lst),
            "turnos":lst
        })
#-----------------------------------------------------------------------------------------------------------------
    faltantes_domingo = {}
    faltantes_domingo_json = []

    #SERVICIOS FALTANTES DOMINGOS & ASIGNADOS:
    print(f"Servicios esperados para el domingo {dfServicios["DOMINGO"].count()}")
    canon_d = set(dfServicios["DOMINGO"]
               .dropna()
               .astype(str).str.strip().str.upper())
    
    for fecha, sub in df[df["DIA_SEMANA"].isin(["DOMINGO"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_d - presentes)
        if faltan:
            faltantes_domingo[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_domingo.items():
        #print(f, "faltan", len(lst), "-", lst[:100], "…")  # muestra los primeros 10
        faltantes_domingo_json.append({
            "fecha":to_iso_str(f),
            "rango":"DOMINGO",
            "cantidad":len(lst),
            "turnos": lst
        })
    
    return serviciosRepetidos,faltantes_lunes_viernes,faltantes_sabado_json,faltantes_domingo_json

def asignacionServiciosTranvia(file):
    # 1) Por si alguien ya leyó el archivo
    if hasattr(file, "seek"):
        try:
            file.seek(0)
        except Exception:
            pass
    
    df = pd.read_excel(file, sheet_name=1)
    dfServicios = pd.read_excel(file, sheet_name=2)
    dfServicios.columns = [str(c).strip() for c in dfServicios.columns]

    print(dfServicios)

    # --- Normalización de encabezados y acceso seguro a nombres ---
    df.columns = [str(c).strip() for c in df.columns]
    cols_map = {c.upper(): c for c in df.columns}

    def col(name, required=True):
        key = name.upper()
        if key in cols_map:
            return cols_map[key]
        if required:
            raise KeyError(f"Falta columna requerida: {name}. Presentes: {list(df.columns)}")
        return None

    FECHA = col("FECHA")
    NOMBRE = col("NOMBRE")
    CUBIERTO  = col("CUBIERTO")
    CODPER = col("CODPER", required=False)
    CODIGO = col("NMNIdentificadorDosNomina")
    RD_EQUIPO  = col("RD_EQUIPO")
    ESTACION_ENT = col("ESTACION_ENT")
    ESTACION_SAL = col("ESTACION_SAL")
   
    df["CARGO"] = "SIN CARGO"
    #Aca usamos los RD_EQUIPO para separar por cargos.
    mas_equipoTranvia = df[RD_EQUIPO].between(30,36, inclusive="both")
    df["CARGO"] = np.where(mas_equipoTranvia,"CONDUCTOR(A) DE VEHICULOS DE PASAJEROS TIPO TRANVIA", "SIN CARGO ASIGNADO")

    #Filtrar tranvia
    df = df[(df[RD_EQUIPO] >= 30) & (df[RD_EQUIPO] <= 36)]
    # FECHA a datetime
    df[FECHA] = pd.to_datetime(df[FECHA], errors="coerce")

    # Excluir turnos 
    excluir = {"LIBRE","COMPE","NOVED","CAFTA","DISPO","INDUC","FUNDA","REIND","CTRAM", "DISTR"}
    df = df[~df[CUBIERTO].isin(excluir)].copy()

    # Día de la semana 
    dow = df[FECHA].dt.dayofweek  # 0=Lun ... 6=Dom
    df["DIA_SEMANA"] = dow.map({0:"LUNES",1:"MARTES",2:"MIERCOLES",3:"JUEVES",4:"VIERNES",5:"SABADO",6:"DOMINGO"})

    # --- Normalizaciones de texto ---
    def norm_ser(s):
        return (s.astype(str).str.strip().str.upper().str.replace(r"\s+", " ", regex=True))

    df[CUBIERTO] = norm_ser(df[CUBIERTO])
    print(f"SERVICIOS TODOS::: {dfServicios["LUNES-VIERNES-TRANVIA"]}")

    # Conjuntos válidos por día-plantilla
    valid_lv  = set(norm_ser(dfServicios["LUNES-VIERNES-TRANVIA"].dropna()))
    valid_sab = set(norm_ser(dfServicios["SABADO-TRANVIA"].dropna()))
    valid_dom = set(norm_ser(dfServicios["DOMINGO-FESTIVO-TRANVIA"].dropna()))

    # --- Máscaras de día ---
    mask_lv  = dow.between(0,4)      
    mask_sab = dow.eq(5)
    mask_dom = dow.eq(6)

    # Estado asignación: 0=sin validar; 1=match plantilla; 2=duplicado en mismo día/servicio
    df["ESTADO_ASIGNACION"] = 0

    df.loc[mask_lv & df[CUBIERTO].isin(valid_lv), "ESTADO_ASIGNACION"] = 1
    df.loc[mask_sab & df[CUBIERTO].isin(valid_sab), "ESTADO_ASIGNACION"] = 1
    df.loc[mask_dom & df[CUBIERTO].isin(valid_dom), "ESTADO_ASIGNACION"] = 1
    #HASTA ACA ESTAMOS BIEN ---- 

    esperado_por_dia_lv = 0
    esperado_por_dia_s = 0
    esperado_por_dia_d = 0

    if df[mask_lv] is not None :
        esperado_por_dia_lv = dfServicios["LUNES-VIERNES-TRANVIA"].count()
    elif df[mask_sab] is not None:
        esperado_por_dia_s = dfServicios["SABADO-TRANVIA"]
    elif df[mask_dom] is not None:
        esperado_por_dia_d = dfServicios["DOMINGO-FESTIVO-TRANVIA"]
   
    asignado_por_dia = (
        df[(df["ESTADO_ASIGNACION"] == 1) & mask_lv]
          .groupby(df[FECHA]).size().rename("Servicios asignados")
    )

    print("INFORME DE ASIGNACION LUNES - VIERNES ")
    print(f"Servicios esperados: {esperado_por_dia_lv}")
    print(f"Servicios asignados:{df['ESTADO_ASIGNACION'].count()} ")
    print(asignado_por_dia)
   
    asignados_por_servicio = (
        df[(df["ESTADO_ASIGNACION"] == 1) & mask_lv]
          .drop_duplicates([FECHA, CUBIERTO])
          [CUBIERTO]
          .value_counts()  # número de días que se asignó ese servicio
    )

    mask_dup = df.duplicated(subset=[FECHA, CUBIERTO], keep=False)

    serviciosRepetidos = None

    if mask_dup is not None:
        df_repetidos = df.loc[mask_dup].sort_values([FECHA, CUBIERTO])
        print("Servicios repetidos en la misma fecha \n", df_repetidos.head())
        df_subset = df_repetidos[[FECHA, NOMBRE, CODPER, CODIGO, ESTACION_ENT, ESTACION_SAL, RD_EQUIPO, CUBIERTO, "CARGO", "DIA_SEMANA", "NMNIdentificadorDosNomina"]]

        serviciosRepetidosTranvia = df_subset.to_dict(orient="records")
        print(serviciosRepetidos)

    # SERVICIOS FALTANTES LUNES A VIERNES:
    dfServicios["TURNOS_ASIGNADOS_LUNES_VIERNES"] = 0
    
    servicios_en_sucesion = set(norm_ser(df[CUBIERTO].dropna()))
    dfServicios["TURNOS_ASIGNADOS_LUNES_VIERNES"] = norm_ser(dfServicios["LUNES-VIERNES-TRANVIA"]).isin(servicios_en_sucesion).astype(int)

    print("\nTOTAL SERVICIOS L–V EN SUCESION (únicos):", len(servicios_en_sucesion))
    print("Asignados (únicos servicio-día, L–V):", asignado_por_dia.sum())

    canon_lv = set(dfServicios["LUNES-VIERNES-TRANVIA"]
               .dropna()
               .astype(str).str.strip().str.upper())

    faltantes_por_dia = {}
    faltantes_lunes_viernesTranvia = []

    for fecha, sub in df[df["DIA_SEMANA"].isin(["LUNES","MARTES","MIERCOLES","JUEVES","VIERNES"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_lv - presentes)
        if faltan:
            faltantes_por_dia[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_por_dia.items():
        #print(f, "faltan", len(lst), "-", lst[:10], "…")  
        faltantes_lunes_viernesTranvia.append({
            "fecha": to_iso_str(f),
            "cantidad":len(lst),
            "rango":"LUNES - VIERNES",
            "turnos":lst
        })
      
          
    #SERVICIOS FALTANTES SABADOS:
    print(f"Servicios esperados para el sabado: {dfServicios["SABADO-TRANVIA"].count()}")
    dfServicios["TURNOS_ASIGNADOS_SABADO"] = 0

    canon_s = set(dfServicios["SABADO-TRANVIA"]
               .dropna()
               .astype(str).str.strip().str.upper())

    faltantes_sabado = {}
    faltantes_sabado_jsonTranvia = []

    for fecha, sub in df[df["DIA_SEMANA"].isin(["SABADO"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_s - presentes)
        if faltan:
            faltantes_sabado[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_sabado.items():
        #print(f, "faltan", len(lst), "-", lst[:10], "…") 
        faltantes_sabado_jsonTranvia.append({
            "fecha": to_iso_str(f),
            "cantidad":len(lst),
            "rango":"SABADOS",
            "turnos":lst
        })
#-----------------------------------------------------------------------------------------------------------------
    faltantes_domingo = {}
    faltantes_domingo_jsonTranvia = []

    #SERVICIOS FALTANTES DOMINGOS & ASIGNADOS:
    print(f"Servicios esperados para el domingo {dfServicios["DOMINGO-FESTIVO-TRANVIA"].count()}")
    canon_d = set(dfServicios["DOMINGO-FESTIVO-TRANVIA"]
               .dropna()
               .astype(str).str.strip().str.upper())
    
    for fecha, sub in df[df["DIA_SEMANA"].isin(["DOMINGO"])] \
                        .groupby("FECHA"):
        presentes = set(sub["CUBIERTO"].astype(str).str.strip().str.upper())
        faltan = sorted(canon_d - presentes)
        if faltan:
            faltantes_domingo[fecha.date()] = faltan

    print("Servicios pendientes por asignar / fecha:")
    for f, lst in faltantes_domingo.items():
        #print(f, "faltan", len(lst), "-", lst[:100], "…")  # muestra los primeros 10
        faltantes_domingo_jsonTranvia.append({
            "fecha":to_iso_str(f),
            "cantidad":len(lst),
            "rango":"DOMINGOS",
            "turnos": lst
        })
    
    return serviciosRepetidosTranvia,faltantes_lunes_viernesTranvia,faltantes_sabado_jsonTranvia,faltantes_domingo_jsonTranvia

def to_iso_str(f):
    if isinstance(f, datetime):
        return f.isoformat(sep=" ", timespec="seconds")   
    if isinstance(f, date):
        return f.isoformat()                               
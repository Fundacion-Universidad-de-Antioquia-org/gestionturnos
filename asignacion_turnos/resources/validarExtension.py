
def validarExcel(archivo):
    if archivo.name.lower().endswith('xlsx'):
        return True
    else: 
        return False

import os
import requests
import time
import json
# Función para enviar logs con reintentos en caso de fallo
def send_log(correo, fecha, tipo_evento, observacion, nombre_aplicacion, tipo, id_registro, retries=3, delay=2):

    log_url = os.getenv("URLLOG") # URL del endpoint para registrar backup
    headers = {'Content-Type': 'application/json'}
    data = {
        'correo': correo,
        'fecha': fecha.isoformat(),  # Usar .isoformat() para asegurar la representación correcta de la zona horaria
        'tipo_evento': tipo_evento,
        'observacion': observacion,
        'id_registro' : id_registro,
        'nombre_aplicacion': nombre_aplicacion,
        'tipo': tipo
    }
 

    for attempt in range(retries):
        try:
            response = requests.post(log_url, headers=headers, data=json.dumps(data), timeout=10)
            response.raise_for_status()
            break  # Salir del bucle si el log se envía exitosamente
        except requests.exceptions.RequestException as e:
            print(f"Failed to send log (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)  # Esperar antes de intentar nuevamente
            else:
                # Guardar log en archivo local si el envío falla
                save_log_locally(data, str(e))
 
def save_log_locally(data, error_message):
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_backups.txt')
    with open(log_file_path, 'a') as log_file:
        log_entry = f"{data['fecha']} - {data['tipo_evento']} - {data['observacion']} - {error_message}\n"
        log_file.write(log_entry)
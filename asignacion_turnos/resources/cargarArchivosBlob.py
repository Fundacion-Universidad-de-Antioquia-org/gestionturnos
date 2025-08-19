from azure.storage.blob import BlobServiceClient
from urllib.parse import unquote
import os
import traceback
from urllib.parse import urlparse
import re
import uuid
import unicodedata



def upload_to_azure_blob(file, filename,app):
    print('Intentando subir archivo a Azure Blob Storage...')
    container_name = None
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if app == "comunicaciones":
            print("Container comunicaciones")
            container_name = os.getenv("AZURE_CONTAINER_COMUNICADOS")
        elif app == "solicitud_gt":
            print("Container solicitudesGt")
            container_name = os.getenv("AZURE_CONTAINER_SOLICITUDESGT")
 
        if not connection_string or not container_name:
            print("Error: La cadena de conexión o el nombre del contenedor no están configurados.")
            return None
        

        print(filename)
    
        # Sanitizar el nombre del archivo para evitar problemas con caracteres especiales
        filename = ''.join(c for c in filename if c.isalnum() or c in '._-') 
        print(filename)


        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)
 
        # Subir el archivo
        content_settings = None
        if hasattr(file, 'content_type') and file.content_type:
            from azure.storage.blob import ContentSettings
            content_settings = ContentSettings(content_type=file.content_type)
           
        blob_client.upload_blob(file, overwrite=True, content_settings=content_settings)
        print(f"Archivo subido a: {blob_client.url}")
 
        return blob_client.url
    except Exception as e:
        print(f"Error subiendo el archivo a Azure Blob Storage: {e}")
        import traceback
        traceback.print_exc()
        return None
    

 
def delete_blob_from_azure(blob_url):
    try:
        # Obtener la cadena de conexión desde las variables de entorno
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            print("Error: No se encontró la cadena de conexión de Azure")
            return False
           
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
       
        # Extraer el nombre del contenedor y del blob desde la URL de manera más robusta
        parsed_url = urlparse(blob_url)
       
        # Manejar diferentes formatos de URL de Azure
        if 'blob.core.windows.net' in parsed_url.netloc:
            # Formato estándar: https://account.blob.core.windows.net/container/blob
            path_parts = parsed_url.path.lstrip('/').split('/', 1)
        else:
            # Podría ser una URL personalizada o CDN
            print(f"Formato de URL no reconocido: {blob_url}")
            return False
       
        if len(path_parts) < 2:
            print(f"Error: URL mal formateada: {blob_url}")
            return False
           
        container_name = path_parts[0]
        blob_name = unquote(path_parts[1])
 
 
       
        # Verificar si el contenedor existe
        try:
            container_client = blob_service_client.get_container_client(container_name)
            container_client.get_container_properties()
        except Exception as e:
            print(f"Error: El contenedor {container_name} no existe: {e}")
            return False
       
        # Obtener el cliente del blob
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
       
        # Verificar si el blob existe antes de intentar eliminarlo
        try:
            blob_client.get_blob_properties()
        except Exception as e:
            print(f"Error: El blob {blob_name} no existe: {e}")
            return False
       
        # Eliminar el blob
        blob_client.delete_blob()
       
        print("Blob eliminado exitosamente.")
        return True
    except Exception as e:
        print(f"Error eliminando el blob de Azure Blob Storage: {e}")
        traceback.print_exc()
        return False





def generar_nombre_blob_seguro(nombre_original: str) -> str:
    """
    Limpia un nombre de archivo para que sea válido en Azure Blob Storage.
    Conserva la extensión original.

    Args:
        nombre_original (str): El nombre original del archivo (ej: "✉️ Formato (Final).pdf")

    Returns:
        str: Un nombre seguro (ej: "formato_Final.pdf")
    """

    if not nombre_original:
        return f"{uuid.uuid4()}.bin"  # si llega vacío

    # Extraer nombre base y extensión
    nombre_base, ext = os.path.splitext(nombre_original)

    # Asegurar que tenga extensión
    ext = ext if ext else ".bin"

    # Normalizar tildes y eliminar caracteres Unicode especiales
    nombre_base = unicodedata.normalize('NFKD', nombre_base).encode('ascii', 'ignore').decode()

    # Reemplazar caracteres inválidos por "_"
    nombre_base = re.sub(r'[^a-zA-Z0-9_.-]', '_', nombre_base)

    # Eliminar puntos o guiones al principio/final y múltiples puntos seguidos
    nombre_base = nombre_base.strip("._-")
    nombre_base = re.sub(r'\.{2,}', '.', nombre_base)

    # Si el nombre quedó vacío, usar UUID
    if not nombre_base:
        nombre_base = str(uuid.uuid4())

    # Construir nombre final
    nombre_seguro = f"{nombre_base}{ext}"

    # Validación de seguridad
    if "/" in nombre_seguro or "\\" in nombre_seguro or ".." in nombre_seguro:
        raise ValueError(f"Nombre de archivo no permitido: '{nombre_seguro}'")

    return nombre_seguro

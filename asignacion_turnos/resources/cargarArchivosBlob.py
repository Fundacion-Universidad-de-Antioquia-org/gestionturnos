from azure.storage.blob import BlobServiceClient
from urllib.parse import unquote
import os
import traceback


def upload_to_azure_blob(file, filename):
    print('Intentando subir archivo a Azure Blob Storage...')
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_CONTAINER_NAME")
 
        if not connection_string or not container_name:
            print("Error: La cadena de conexión o el nombre del contenedor no están configurados.")
            return None
 
        # Sanitizar el nombre del archivo para evitar problemas con caracteres especiales
        filename = ''.join(c for c in filename if c.isalnum() or c in '._- ')
       
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
    
"""
Módulo mejorado para gestión de archivos en Google Cloud Storage
Nueva estructura: users/{email}/uploads|processed/{año}/{mes}/archivo
"""

from google.cloud import storage
from pathlib import Path
from typing import List, Optional, Dict
import os
import json
import tempfile
from datetime import datetime
import io


class GCSStorageManagerV2:
    """
    Manejador mejorado de almacenamiento en GCS con estructura por fechas
    """
    
    def __init__(self, bucket_name: str = "bucket-profe-go"):
        """
        Inicializa el manejador de GCS
        
        Args:
            bucket_name: Nombre del bucket en GCS
        """
        # Configurar credenciales
        credentials_json_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if credentials_json_str:
            try:
                credentials_dict = json.loads(credentials_json_str)
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                    json.dump(credentials_dict, f)
                    temp_creds_path = f.name
                
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_path
                print(f"✓ Credenciales GCS configuradas desde variable de entorno")
            except Exception as e:
                print(f"⚠️ Error configurando credenciales: {e}")
        
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name
        self.usuarios_inicializados = set()
    
    def _normalizar_email(self, email: str) -> str:
        """
        Normaliza el email para usarlo como nombre de carpeta
        """
        return email.replace("@", "_").replace(".", "_")
    
    def _obtener_fecha_path(self) -> str:
        """
        Obtiene la ruta de fecha actual (año/mes)
        """
        now = datetime.now()
        return f"{now.year}/{now.month:02d}"
    
    def _construir_ruta(self, email: str, es_procesado: bool, nombre_archivo: str, 
                       fecha_personalizada: Optional[str] = None) -> str:
        """
        Construye la ruta completa en el bucket con nueva estructura
        
        Args:
            email: Email del usuario
            es_procesado: Si es archivo procesado o original
            nombre_archivo: Nombre del archivo
            fecha_personalizada: Fecha en formato "YYYY/MM" (opcional)
        
        Returns:
            Ruta: users/{email}/uploads|processed/{año}/{mes}/archivo
        """
        usuario_normalizado = self._normalizar_email(email)
        tipo_carpeta = "processed" if es_procesado else "uploads"
        fecha_path = fecha_personalizada or self._obtener_fecha_path()
        
        return f"users/{usuario_normalizado}/{tipo_carpeta}/{fecha_path}/{nombre_archivo}"
    
    def inicializar_usuario(self, email: str) -> bool:
        """
        Crea la estructura de carpetas para un nuevo usuario
        """
        try:
            usuario_normalizado = self._normalizar_email(email)
            
            # Crear archivos .keep en las carpetas base
            for tipo in ["uploads", "processed"]:
                ruta_keep = f"users/{usuario_normalizado}/{tipo}/.keep"
                blob = self.bucket.blob(ruta_keep)
                
                if not blob.exists():
                    blob.upload_from_string("")
                    print(f"✓ Creada estructura: users/{usuario_normalizado}/{tipo}/")
            
            self.usuarios_inicializados.add(email)
            return True
            
        except Exception as e:
            print(f"✗ Error inicializando usuario {email}: {e}")
            return False
    
    def subir_archivo_desde_bytes(self, contenido: bytes, email: str, 
                                  nombre_archivo: str, es_procesado: bool = False) -> Dict:
        """
        Sube un archivo desde bytes directamente a GCS
        
        Args:
            contenido: Contenido del archivo en bytes
            email: Email del usuario
            nombre_archivo: Nombre del archivo
            es_procesado: Si es archivo procesado o original
        
        Returns:
            Dict con información del archivo subido
        """
        try:
            if email not in self.usuarios_inicializados:
                self.inicializar_usuario(email)
            
            # Construir ruta en GCS con fecha actual
            ruta_gcs = self._construir_ruta(email, es_procesado, nombre_archivo)
            
            # Subir archivo
            blob = self.bucket.blob(ruta_gcs)
            blob.upload_from_string(contenido)
            
            # Obtener información
            blob.reload()
            
            return {
                'success': True,
                'filename': nombre_archivo,
                'path': ruta_gcs,
                'size': blob.size,
                'url': f"gs://{self.bucket_name}/{ruta_gcs}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': nombre_archivo
            }
    
    def obtener_archivo_bytes(self, email: str, nombre_archivo: str, 
                              es_procesado: bool = False) -> Optional[bytes]:
        """
        Obtiene el contenido de un archivo como bytes
        
        Args:
            email: Email del usuario
            nombre_archivo: Nombre del archivo
            es_procesado: Si es archivo procesado o original
        
        Returns:
            Contenido del archivo en bytes o None si no existe
        """
        try:
            # Buscar el archivo en cualquier fecha
            usuario_normalizado = self._normalizar_email(email)
            tipo_carpeta = "processed" if es_procesado else "uploads"
            prefijo = f"users/{usuario_normalizado}/{tipo_carpeta}/"
            
            # Buscar el archivo
            blobs = list(self.bucket.list_blobs(prefix=prefijo))
            for blob in blobs:
                if blob.name.endswith(nombre_archivo):
                    return blob.download_as_bytes()
            
            return None
            
        except Exception as e:
            print(f"Error obteniendo archivo: {e}")
            return None
    
    def descargar_archivo(self, email: str, nombre_archivo: str, 
                         destino_local: str, es_procesado: bool = False) -> Dict:
        """
        Descarga un archivo del bucket a un archivo local
        """
        try:
            contenido = self.obtener_archivo_bytes(email, nombre_archivo, es_procesado)
            
            if contenido is None:
                return {
                    'success': False,
                    'error': f'Archivo no encontrado: {nombre_archivo}'
                }
            
            # Guardar en archivo local
            with open(destino_local, 'wb') as f:
                f.write(contenido)
            
            return {
                'success': True,
                'filename': nombre_archivo,
                'local_path': destino_local,
                'size': len(contenido)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def listar_archivos(self, email: str, tipo: str = "uploads") -> List[Dict]:
        """
        Lista todos los archivos de un usuario
        
        Args:
            email: Email del usuario
            tipo: "uploads" o "processed"
        
        Returns:
            Lista de diccionarios con información de archivos
        """
        try:
            usuario_normalizado = self._normalizar_email(email)
            prefijo = f"users/{usuario_normalizado}/{tipo}/"
            blobs = self.bucket.list_blobs(prefix=prefijo)
            
            archivos = []
            for blob in blobs:
                # Ignorar archivos .keep
                if blob.name.endswith('.keep'):
                    continue
                
                # Extraer información
                partes = blob.name.split('/')
                if len(partes) >= 5:  # users/email/tipo/año/mes/archivo
                    nombre_archivo = partes[-1]
                    fecha = f"{partes[-3]}/{partes[-2]}"
                    
                    archivos.append({
                        'name': nombre_archivo,
                        'size': blob.size,
                        'size_mb': f"{blob.size / (1024*1024):.2f}",
                        'date': fecha,
                        'created': blob.time_created.isoformat() if blob.time_created else "",
                        'path': blob.name,
                        'content_type': blob.content_type
                    })
            
            # Ordenar por fecha de creación (más reciente primero)
            archivos.sort(key=lambda x: x['created'], reverse=True)
            
            return archivos
            
        except Exception as e:
            print(f"Error listando archivos: {e}")
            return []
    
    def eliminar_archivo(self, email: str, nombre_archivo: str, 
                        es_procesado: bool = False) -> Dict:
        """
        Elimina un archivo del bucket
        """
        try:
            # Buscar el archivo en cualquier fecha
            usuario_normalizado = self._normalizar_email(email)
            tipo_carpeta = "processed" if es_procesado else "uploads"
            prefijo = f"users/{usuario_normalizado}/{tipo_carpeta}/"
            
            # Buscar y eliminar el archivo
            blobs = list(self.bucket.list_blobs(prefix=prefijo))
            archivo_encontrado = False
            
            for blob in blobs:
                if blob.name.endswith(nombre_archivo):
                    blob.delete()
                    archivo_encontrado = True
                    break
            
            if not archivo_encontrado:
                return {
                    'success': False,
                    'error': f'Archivo no encontrado: {nombre_archivo}'
                }
            
            return {
                'success': True,
                'filename': nombre_archivo,
                'message': f'Archivo {nombre_archivo} eliminado correctamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def obtener_info_almacenamiento(self, email: str) -> Dict:
        """
        Obtiene información detallada del almacenamiento del usuario
        """
        try:
            archivos_subidos = self.listar_archivos(email, "uploads")
            archivos_procesados = self.listar_archivos(email, "processed")
            
            total_size_subidos = sum(archivo['size'] for archivo in archivos_subidos)
            total_size_procesados = sum(archivo['size'] for archivo in archivos_procesados)
            total_size = total_size_subidos + total_size_procesados
            
            return {
                "email": email,
                "total_files": len(archivos_subidos) + len(archivos_procesados),
                "uploaded_files": len(archivos_subidos),
                "processed_files": len(archivos_procesados),
                "total_size_bytes": total_size,
                "total_size_mb": f"{total_size / (1024*1024):.2f}",
                "uploaded_size_mb": f"{total_size_subidos / (1024*1024):.2f}",
                "processed_size_mb": f"{total_size_procesados / (1024*1024):.2f}",
                "storage_structure": {
                    "uploads_by_month": self._agrupar_por_fecha(archivos_subidos),
                    "processed_by_month": self._agrupar_por_fecha(archivos_procesados)
                }
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "email": email,
                "total_files": 0
            }
    
    def _agrupar_por_fecha(self, archivos: List[Dict]) -> Dict:
        """
        Agrupa archivos por año/mes
        """
        agrupados = {}
        for archivo in archivos:
            fecha = archivo.get('date', 'sin_fecha')
            if fecha not in agrupados:
                agrupados[fecha] = []
            agrupados[fecha].append(archivo['name'])
        return agrupados
    
    def obtener_url_descarga_temporal(self, email: str, nombre_archivo: str,
                                     es_procesado: bool = False, 
                                     expiracion_minutos: int = 60) -> Optional[str]:
        """
        Genera una URL firmada temporal para descargar un archivo
        """
        try:
            from datetime import timedelta
            
            # Buscar el archivo
            usuario_normalizado = self._normalizar_email(email)
            tipo_carpeta = "processed" if es_procesado else "uploads"
            prefijo = f"users/{usuario_normalizado}/{tipo_carpeta}/"
            
            blobs = list(self.bucket.list_blobs(prefix=prefijo))
            for blob in blobs:
                if blob.name.endswith(nombre_archivo):
                    url = blob.generate_signed_url(
                        version="v4",
                        expiration=timedelta(minutes=expiracion_minutos),
                        method="GET"
                    )
                    return url
            
            return None
            
        except Exception as e:
            print(f"Error generando URL: {e}")
            return None
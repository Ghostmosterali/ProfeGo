"""
Script de pruebas mejorado para Google Cloud Storage con descarga de archivos
"""

from google.cloud import storage
from gcs_storage import GCSStorageManagerV2
import os
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
BUCKET_NAME = "bucket-profe-go"

# ============================================================================
# PRUEBA 1: Verificar conexión y listar buckets
# ============================================================================
def test_conexion():
    """Prueba la conexión con Google Cloud Storage"""
    print("\n" + "="*60)
    print("PRUEBA 1: Verificación de Conexión")
    print("="*60)
    
    try:
        client = storage.Client()
        
        print("\n✅ Conexión exitosa con Google Cloud Storage")
        print("\n📦 Buckets disponibles en tu proyecto:")
        
        buckets = client.list_buckets()
        bucket_list = list(buckets)
        
        if not bucket_list:
            print("   ⚠️  No hay buckets en este proyecto")
        else:
            for bucket in bucket_list:
                print(f"   - {bucket.name}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")
        print("\n💡 Verifica que:")
        print("   1. GOOGLE_APPLICATION_CREDENTIALS esté configurado")
        print("   2. El archivo de credenciales sea válido")
        print("   3. Tengas permisos en el proyecto")
        return False

# ============================================================================
# PRUEBA 2: Verificar bucket específico
# ============================================================================
def test_bucket_existe():
    """Verifica que el bucket de ProfeGo exista"""
    print("\n" + "="*60)
    print(f"PRUEBA 2: Verificar Bucket '{BUCKET_NAME}'")
    print("="*60)
    
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        if bucket.exists():
            print(f"\n✅ El bucket '{BUCKET_NAME}' existe")
            print(f"   Ubicación: {bucket.location}")
            print(f"   Clase de almacenamiento: {bucket.storage_class}")
            return True
        else:
            print(f"\n⚠️  El bucket '{BUCKET_NAME}' NO existe")
            print(f"\n💡 Crear el bucket con:")
            print(f"   gsutil mb gs://{BUCKET_NAME}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error verificando bucket: {e}")
        return False

# ============================================================================
# NUEVA FUNCIÓN: Descargar archivos del bucket
# ============================================================================
def descargar_archivo_bucket():
    """Descarga archivos desde el bucket de GCS"""
    print("\n" + "="*60)
    print("DESCARGAR ARCHIVO DEL BUCKET")
    print("="*60)
    
    try:
        manager = GCSStorageManagerV2(BUCKET_NAME)
        
        # Solicitar email del usuario
        email_usuario = input("\n📧 Email del usuario: ").strip()
        if not email_usuario:
            print("❌ Email requerido")
            return False
        
        # Listar archivos disponibles
        print("\n📂 Buscando archivos...")
        
        archivos_originales = manager.listar_archivos(email_usuario, "uploads")
        archivos_procesados = manager.listar_archivos(email_usuario, "processed")
        
        todos_archivos = []
        
        print("\n--- ARCHIVOS ORIGINALES ---")
        if archivos_originales:
            for idx, archivo in enumerate(archivos_originales, 1):
                todos_archivos.append(('uploads', archivo))
                print(f"{len(todos_archivos)}. {archivo['name']} ({archivo['size_mb']} MB) - {archivo['date']}")
        else:
            print("   No hay archivos originales")
        
        print("\n--- ARCHIVOS PROCESADOS ---")
        if archivos_procesados:
            for idx, archivo in enumerate(archivos_procesados, 1):
                todos_archivos.append(('processed', archivo))
                print(f"{len(todos_archivos)}. {archivo['name']} ({archivo['size_mb']} MB) - {archivo['date']}")
        else:
            print("   No hay archivos procesados")
        
        if not todos_archivos:
            print("\n⚠️  No se encontraron archivos para este usuario")
            return False
        
        # Seleccionar archivo
        print("\n" + "-"*40)
        seleccion = input("Selecciona el número del archivo a descargar (0 para cancelar): ")
        
        if seleccion == "0":
            print("❌ Descarga cancelada")
            return False
        
        try:
            idx = int(seleccion) - 1
            if 0 <= idx < len(todos_archivos):
                tipo, archivo_info = todos_archivos[idx]
                es_procesado = (tipo == "processed")
                nombre_archivo = archivo_info['name']
                
                # Crear carpeta de descargas si no existe
                carpeta_descargas = Path("descargas_bucket") / email_usuario.replace("@", "_").replace(".", "_")
                carpeta_descargas.mkdir(parents=True, exist_ok=True)
                
                # Destino local
                destino_local = carpeta_descargas / nombre_archivo
                
                print(f"\n⬇️  Descargando: {nombre_archivo}")
                print(f"📁 Destino: {destino_local}")
                
                # Descargar archivo
                resultado = manager.descargar_archivo(
                    email=email_usuario,
                    nombre_archivo=nombre_archivo,
                    destino_local=str(destino_local),
                    es_procesado=es_procesado
                )
                
                if resultado['success']:
                    print(f"✅ Archivo descargado exitosamente")
                    print(f"   Tamaño: {resultado['size'] / 1024:.2f} KB")
                    print(f"   Ubicación: {resultado['local_path']}")
                else:
                    print(f"❌ Error: {resultado['error']}")
                
                return resultado['success']
            else:
                print("❌ Selección inválida")
                return False
                
        except ValueError:
            print("❌ Por favor ingresa un número válido")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# ============================================================================
# NUEVA FUNCIÓN: Descarga masiva
# ============================================================================
def descargar_todos_archivos():
    """Descarga todos los archivos de un usuario"""
    print("\n" + "="*60)
    print("DESCARGA MASIVA DE ARCHIVOS")
    print("="*60)
    
    try:
        manager = GCSStorageManagerV2(BUCKET_NAME)
        
        email_usuario = input("\n📧 Email del usuario: ").strip()
        if not email_usuario:
            print("❌ Email requerido")
            return False
        
        print("\nOpciones de descarga:")
        print("1. Solo archivos originales")
        print("2. Solo archivos procesados")
        print("3. Todos los archivos")
        
        opcion = input("\nSelecciona opción (1-3): ")
        
        archivos_a_descargar = []
        
        if opcion in ["1", "3"]:
            archivos_originales = manager.listar_archivos(email_usuario, "uploads")
            for archivo in archivos_originales:
                archivos_a_descargar.append(("uploads", archivo, False))
        
        if opcion in ["2", "3"]:
            archivos_procesados = manager.listar_archivos(email_usuario, "processed")
            for archivo in archivos_procesados:
                archivos_a_descargar.append(("processed", archivo, True))
        
        if not archivos_a_descargar:
            print("\n⚠️  No se encontraron archivos")
            return False
        
        print(f"\n📥 Se descargarán {len(archivos_a_descargar)} archivos")
        confirmar = input("¿Continuar? (s/n): ")
        
        if confirmar.lower() != 's':
            print("❌ Descarga cancelada")
            return False
        
        # Crear carpeta de descargas
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        carpeta_descargas = Path("descargas_bucket") / f"{email_usuario.replace('@', '_').replace('.', '_')}_{timestamp}"
        carpeta_descargas.mkdir(parents=True, exist_ok=True)
        
        exitosos = 0
        fallidos = 0
        
        for tipo, archivo_info, es_procesado in archivos_a_descargar:
            nombre_archivo = archivo_info['name']
            print(f"\n⬇️  Descargando {nombre_archivo}...")
            
            # Crear subcarpeta según tipo
            subcarpeta = carpeta_descargas / tipo
            subcarpeta.mkdir(exist_ok=True)
            
            destino_local = subcarpeta / nombre_archivo
            
            resultado = manager.descargar_archivo(
                email=email_usuario,
                nombre_archivo=nombre_archivo,
                destino_local=str(destino_local),
                es_procesado=es_procesado
            )
            
            if resultado['success']:
                print(f"   ✅ Descargado")
                exitosos += 1
            else:
                print(f"   ❌ Error: {resultado['error']}")
                fallidos += 1
        
        print("\n" + "="*60)
        print(f"📊 RESUMEN DE DESCARGA")
        print(f"   ✅ Exitosos: {exitosos}")
        print(f"   ❌ Fallidos: {fallidos}")
        print(f"   📁 Carpeta: {carpeta_descargas}")
        print("="*60)
        
        return exitosos > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# ============================================================================
# PRUEBA MEJORADA: Listar archivos con nueva estructura
# ============================================================================
def test_listar_archivos_v2():
    """Lista archivos con la nueva estructura de carpetas por fecha"""
    print("\n" + "="*60)
    print("LISTAR ARCHIVOS (Nueva Estructura)")
    print("="*60)
    
    try:
        manager = GCSStorageManagerV2(BUCKET_NAME)
        
        # Solicitar email o listar todos
        print("\nOpciones:")
        print("1. Listar archivos de un usuario específico")
        print("2. Listar estructura completa del bucket")
        
        opcion = input("\nSelecciona opción (1-2): ")
        
        if opcion == "1":
            email = input("Email del usuario: ")
            
            print(f"\n📁 Archivos de {email}:")
            
            # Listar uploads
            archivos_uploads = manager.listar_archivos(email, "uploads")
            if archivos_uploads:
                print("\n--- UPLOADS ---")
                for archivo in archivos_uploads:
                    print(f"   {archivo['date']}/{archivo['name']} ({archivo['size_mb']} MB)")
            
            # Listar processed
            archivos_processed = manager.listar_archivos(email, "processed")
            if archivos_processed:
                print("\n--- PROCESSED ---")
                for archivo in archivos_processed:
                    print(f"   {archivo['date']}/{archivo['name']} ({archivo['size_mb']} MB)")
            
            if not archivos_uploads and not archivos_processed:
                print("   No hay archivos")
                
        else:
            # Listar toda la estructura
            client = storage.Client()
            bucket = client.bucket(BUCKET_NAME)
            
            print("\n📂 Estructura del bucket:")
            
            estructura = {}
            for blob in bucket.list_blobs(prefix="users/"):
                partes = blob.name.split('/')
                if len(partes) >= 2:
                    usuario = partes[1]
                    if usuario not in estructura:
                        estructura[usuario] = {'uploads': 0, 'processed': 0}
                    
                    if 'uploads' in blob.name:
                        estructura[usuario]['uploads'] += 1
                    elif 'processed' in blob.name:
                        estructura[usuario]['processed'] += 1
            
            for usuario, conteos in estructura.items():
                print(f"\n👤 {usuario}")
                print(f"   📤 Uploads: {conteos['uploads']} archivos")
                print(f"   ✅ Processed: {conteos['processed']} archivos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# ============================================================================
# PRUEBA 6: Operaciones CRUD mejoradas
# ============================================================================
def test_operaciones_crud():
    """Prueba todas las operaciones CRUD con nueva estructura"""
    print("\n" + "="*60)
    print("PRUEBA: Operaciones CRUD")
    print("="*60)
    
    try:
        manager = GCSStorageManagerV2(BUCKET_NAME)
        test_email = "crud_test@ejemplo.com"
        archivo_test = "crud_test.txt"
        
        # CREATE
        print("\n1️⃣  CREATE - Subir archivo")
        with open(archivo_test, "w") as f:
            f.write("Archivo de prueba CRUD - " + datetime.now().isoformat())
        
        with open(archivo_test, "rb") as f:
            contenido = f.read()
        
        resultado_subida = manager.subir_archivo_desde_bytes(
            contenido=contenido,
            email=test_email,
            nombre_archivo=archivo_test,
            es_procesado=False
        )
        print(f"   {'✅' if resultado_subida['success'] else '❌'} Subida: {resultado_subida['success']}")
        
        # READ
        print("\n2️⃣  READ - Listar archivos")
        archivos = manager.listar_archivos(test_email, "uploads")
        print(f"   ✅ Archivos encontrados: {len(archivos)}")
        for archivo in archivos:
            print(f"      - {archivo['date']}/{archivo['name']} ({archivo['size_mb']} MB)")
        
        # DOWNLOAD
        print("\n3️⃣  DOWNLOAD - Descargar archivo")
        destino_descarga = f"descargado_{archivo_test}"
        resultado_descarga = manager.descargar_archivo(
            email=test_email,
            nombre_archivo=archivo_test,
            destino_local=destino_descarga,
            es_procesado=False
        )
        print(f"   {'✅' if resultado_descarga['success'] else '❌'} Descarga: {resultado_descarga['success']}")
        if resultado_descarga['success']:
            print(f"      Archivo guardado en: {destino_descarga}")
            # Limpiar archivo descargado
            if os.path.exists(destino_descarga):
                os.remove(destino_descarga)
        
        # DELETE
        print("\n4️⃣  DELETE - Eliminar archivo")
        resultado_eliminacion = manager.eliminar_archivo(
            email=test_email,
            nombre_archivo=archivo_test,
            es_procesado=False
        )
        print(f"   {'✅' if resultado_eliminacion['success'] else '❌'} Eliminación: {resultado_eliminacion['success']}")
        
        # Verificar eliminación
        archivos_despues = manager.listar_archivos(test_email, "uploads")
        archivo_existe = any(a['name'] == archivo_test for a in archivos_despues)
        print(f"   ✅ Verificación post-eliminación: archivo {'existe' if archivo_existe else 'no existe'}")
        
        # Limpiar archivo local
        if os.path.exists(archivo_test):
            os.remove(archivo_test)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error en pruebas CRUD: {e}")
        return False

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================
def ejecutar_todas_las_pruebas():
    """Ejecuta todas las pruebas en secuencia"""
    print("\n" + "🚀"*30)
    print("INICIANDO PRUEBAS DE GOOGLE CLOUD STORAGE v2")
    print("🚀"*30)
    
    resultados = {
        "Conexión": test_conexion(),
        "Bucket Existe": test_bucket_existe(),
        "Listar Archivos v2": test_listar_archivos_v2(),
        "Operaciones CRUD": test_operaciones_crud()
    }
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*60)
    
    for nombre, resultado in resultados.items():
        icono = "✅" if resultado else "❌"
        print(f"{icono} {nombre}: {'PASÓ' if resultado else 'FALLÓ'}")
    
    total = len(resultados)
    exitosas = sum(resultados.values())
    
    print("\n" + "="*60)
    print(f"🎯 Resultado Final: {exitosas}/{total} pruebas exitosas")
    print("="*60)
    
    if exitosas == total:
        print("\n🎉 ¡Todas las pruebas pasaron! El sistema está listo.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa la configuración.")

# ============================================================================
# UTILIDADES ADICIONALES
# ============================================================================
def limpiar_archivos_prueba():
    """Limpia archivos de prueba del bucket"""
    print("\n" + "="*60)
    print("LIMPIAR ARCHIVOS DE PRUEBA")
    print("="*60)
    
    respuesta = input("\n⚠️  ¿Eliminar archivos de usuarios de prueba? (si/no): ")
    
    if respuesta.lower() not in ['si', 's', 'yes', 'y']:
        print("❌ Operación cancelada")
        return
    
    try:
        manager = GCSStorageManagerV2(BUCKET_NAME)
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        # Usuarios de prueba a limpiar
        usuarios_prueba = [
            "test_usuario@ejemplo.com",
            "crud_test@ejemplo.com",
            "test@ejemplo.com"
        ]
        
        total_eliminados = 0
        
        for usuario in usuarios_prueba:
            print(f"\n🧹 Limpiando archivos de: {usuario}")
            usuario_normalizado = usuario.replace("@", "_").replace(".", "_")
            prefijo = f"users/{usuario_normalizado}/"
            
            blobs = list(bucket.list_blobs(prefix=prefijo))
            contador = 0
            
            for blob in blobs:
                if not blob.name.endswith('.keep'):
                    blob.delete()
                    contador += 1
            
            print(f"   ✅ {contador} archivos eliminados")
            total_eliminados += contador
        
        print(f"\n✅ Limpieza completada: {total_eliminados} archivos eliminados en total")
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")

def obtener_estadisticas_bucket():
    """Obtiene estadísticas del bucket"""
    print("\n" + "="*60)
    print("ESTADÍSTICAS DEL BUCKET")
    print("="*60)
    
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        # Recopilar estadísticas
        total_archivos = 0
        total_size = 0
        usuarios = set()
        archivos_por_tipo = {'uploads': 0, 'processed': 0}
        archivos_por_extension = {}
        
        for blob in bucket.list_blobs(prefix="users/"):
            if not blob.name.endswith('.keep'):
                total_archivos += 1
                total_size += blob.size
                
                # Extraer usuario
                partes = blob.name.split('/')
                if len(partes) >= 2:
                    usuarios.add(partes[1])
                
                # Tipo de archivo
                if 'uploads' in blob.name:
                    archivos_por_tipo['uploads'] += 1
                elif 'processed' in blob.name:
                    archivos_por_tipo['processed'] += 1
                
                # Extension
                extension = Path(blob.name).suffix.lower()
                if extension:
                    archivos_por_extension[extension] = archivos_por_extension.get(extension, 0) + 1
        
        # Mostrar estadísticas
        print(f"\n📊 RESUMEN GENERAL:")
        print(f"   📦 Bucket: {BUCKET_NAME}")
        print(f"   👥 Usuarios totales: {len(usuarios)}")
        print(f"   📄 Archivos totales: {total_archivos}")
        print(f"   💾 Tamaño total: {total_size / (1024*1024):.2f} MB")
        
        print(f"\n📈 POR TIPO:")
        print(f"   📤 Uploads: {archivos_por_tipo['uploads']} archivos")
        print(f"   ✅ Procesados: {archivos_por_tipo['processed']} archivos")
        
        if archivos_por_extension:
            print(f"\n📁 POR EXTENSIÓN:")
            for ext, count in sorted(archivos_por_extension.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   {ext}: {count} archivos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return False

# ============================================================================
# MENÚ INTERACTIVO MEJORADO
# ============================================================================
def menu_interactivo():
    """Menú interactivo mejorado con nuevas funciones"""
    while True:
        print("\n" + "="*60)
        print("🔧 MENÚ DE PRUEBAS - Google Cloud Storage v2")
        print("="*60)
        print("\n--- PRUEBAS BÁSICAS ---")
        print("1. ✅ Verificar conexión")
        print("2. 📦 Verificar bucket existe")
        print("3. 📁 Listar archivos (nueva estructura)")
        print("4. 🔄 Operaciones CRUD")
        print("5. 🚀 Ejecutar TODAS las pruebas")
        
        print("\n--- GESTIÓN DE ARCHIVOS ---")
        print("6. ⬇️  Descargar archivo específico")
        print("7. 📥 Descarga masiva de archivos")
        print("8. 📊 Ver estadísticas del bucket")
        print("9. 🧹 Limpiar archivos de prueba")
        
        print("\n0. ❌ Salir")
        print("="*60)
        
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == "1":
            test_conexion()
        elif opcion == "2":
            test_bucket_existe()
        elif opcion == "3":
            test_listar_archivos_v2()
        elif opcion == "4":
            test_operaciones_crud()
        elif opcion == "5":
            ejecutar_todas_las_pruebas()
        elif opcion == "6":
            descargar_archivo_bucket()
        elif opcion == "7":
            descargar_todos_archivos()
        elif opcion == "8":
            obtener_estadisticas_bucket()
        elif opcion == "9":
            limpiar_archivos_prueba()
        elif opcion == "0":
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("\n❌ Opción inválida. Intenta de nuevo.")
        
        input("\n⏸️  Presiona Enter para continuar...")

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    import sys
    
    print("\n" + "🔵"*30)
    print("ProfeGo - Script de Pruebas GCS v2")
    print("Nueva estructura con carpetas por fecha")
    print("🔵"*30)
    
    # Verificar credenciales
    credenciales = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not credenciales:
        print("\n⚠️  ADVERTENCIA: Variable GOOGLE_APPLICATION_CREDENTIALS no configurada")
        print("\n💡 Configúrala con:")
        print("   Windows: $env:GOOGLE_APPLICATION_CREDENTIALS='ruta\\al\\archivo.json'")
        print("   Linux/Mac: export GOOGLE_APPLICATION_CREDENTIALS='ruta/al/archivo.json'")
        print("\n")
    else:
        print(f"\n✅ Credenciales configuradas: {credenciales}")
        
        if not os.path.exists(credenciales):
            print(f"⚠️  ADVERTENCIA: El archivo de credenciales no existe en esa ruta")
    
    # Si se pasa un argumento, ejecutar función específica
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        comandos = {
            "test": ejecutar_todas_las_pruebas,
            "conexion": test_conexion,
            "bucket": test_bucket_existe,
            "listar": test_listar_archivos_v2,
            "crud": test_operaciones_crud,
            "descargar": descargar_archivo_bucket,
            "masiva": descargar_todos_archivos,
            "stats": obtener_estadisticas_bucket,
            "limpiar": limpiar_archivos_prueba
        }
        
        if comando in comandos:
            comandos[comando]()
        else:
            print(f"\n❌ Comando desconocido: {comando}")
            print("\nComandos disponibles:")
            for cmd in comandos.keys():
                print(f"   - python bucket.py {cmd}")
    else:
        # Sin argumentos, mostrar menú interactivo
        menu_interactivo()
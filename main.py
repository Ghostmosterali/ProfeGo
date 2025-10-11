from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import pyrebase
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Optional
import json
from datetime import datetime
import tempfile
import io

# Importar el módulo OCR
from PruebaOcr import process_file_to_txt, check_supported_file

# Importar el módulo de Google Cloud Storage mejorado
from gcs_storage import GCSStorageManagerV2

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="ProfeGo API", version="2.0.0")

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configurar CORS para desarrollo y producción
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
allowed_origins = []

if RENDER_EXTERNAL_URL:
    # En producción (Render)
    allowed_origins = [
        RENDER_EXTERNAL_URL,
        f"https://{RENDER_EXTERNAL_URL.replace('https://', '')}",
    ]
else:
    # En desarrollo local - CORS PERMISIVO
    allowed_origins = ["*"]  # Permitir todos los orígenes en desarrollo

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de archivos
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', 
    '.png', '.xlsx', '.xls', '.csv', '.json', '.xml'
}

# Obtener directorio base del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# ========== IMPORTANTE: SERVIR ARCHIVOS ESTÁTICOS CORRECTAMENTE ==========
# Verificar que el directorio frontend existe
if not os.path.exists(FRONTEND_DIR):
    print(f"⚠️  ADVERTENCIA: No se encontró el directorio frontend en {FRONTEND_DIR}")
else:
    print(f"✅ Frontend encontrado en: {FRONTEND_DIR}")
    
    # Montar archivos estáticos ANTES de definir las rutas
    # Esto permite que FastAPI sirva CSS, JS, y otros archivos
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")
    print(f"✅ Archivos estáticos montados en /frontend")

# Firebase Config (Solo Auth)
firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL", "")
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

# Google Cloud Storage Manager V2 con nueva estructura
gcs_storage = GCSStorageManagerV2(
    bucket_name=os.getenv("GCS_BUCKET_NAME", "bucket-profe-go")
)

# ---------------- Modelos Pydantic ----------------
class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    email: str
    token: str
    message: str

class FileInfo(BaseModel):
    name: str
    type: str
    size: str
    category: str
    date: str
    download_url: Optional[str] = None

class ProcessingResult(BaseModel):
    success: bool
    files_uploaded: int
    files_processed: int
    message: str
    errors: List[str] = []

class PaginatedFiles(BaseModel):
    files: List[FileInfo]
    total: int
    page: int
    pages: int
    per_page: int

# ---------------- Utilidades ----------------
class ProfeGoUtils:
    @staticmethod
    def validar_email(email: str) -> bool:
        """Validar formato de email"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validar_password(password: str) -> bool:
        """Validar que la contraseña tenga al menos 6 caracteres"""
        return len(password) >= 6
    
    @staticmethod
    def obtener_tipo_archivo(filename: str) -> str:
        """Determinar el tipo de archivo basado en su extensión"""
        ext = os.path.splitext(filename)[1].lower()
        
        tipos = {
            '.pdf': "PDF",
            '.jpg': "Imagen", '.jpeg': "Imagen", '.png': "Imagen",
            '.doc': "Word", '.docx': "Word",
            '.xls': "Excel", '.xlsx': "Excel",
            '.txt': "Texto",
            '.csv': "CSV",
            '.json': "JSON",
            '.xml': "XML"
        }
        
        return tipos.get(ext, "Archivo")
    
    @staticmethod
    def validar_extension(filename: str) -> bool:
        """Validar si la extensión del archivo está permitida"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in ALLOWED_EXTENSIONS

# ---------------- Dependency para autenticación ----------------
async def get_current_user(authorization: str = Header(None)):
    """Verificar token de Firebase y extraer usuario"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        user_info = auth.get_account_info(token)
        email = user_info['users'][0]['email']
        return {"email": email, "token": token}
    except Exception as e:
        print(f"Error verificando token: {e}")
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

# ---------------- Rutas de Autenticación ----------------
@app.post("/api/auth/login", response_model=UserResponse)
@limiter.limit("10/minute")  # Aumentado de 5 a 10 para desarrollo
async def login(request: Request, user_data: UserLogin):
    """Iniciar sesión con rate limiting"""
    print(f"📧 Intento de login: {user_data.email}")
    
    if not ProfeGoUtils.validar_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email inválido")
    
    if not ProfeGoUtils.validar_password(user_data.password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    try:
        user = auth.sign_in_with_email_and_password(user_data.email, user_data.password)
        
        # Inicializar estructura en GCS
        gcs_storage.inicializar_usuario(user_data.email)
        
        print(f"✅ Login exitoso: {user_data.email}")
        
        return UserResponse(
            email=user_data.email,
            token=user.get("idToken"),
            message=f"Bienvenido/a {user_data.email}"
        )
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error en login: {error_msg}")
        
        if "EMAIL_NOT_FOUND" in error_msg:
            raise HTTPException(status_code=400, detail="Usuario no encontrado")
        elif "INVALID_PASSWORD" in error_msg or "INVALID_LOGIN_CREDENTIALS" in error_msg:
            raise HTTPException(status_code=400, detail="Credenciales incorrectas")
        elif "TOO_MANY_ATTEMPTS" in error_msg:
            raise HTTPException(status_code=429, detail="Demasiados intentos. Intenta más tarde")
        else:
            raise HTTPException(status_code=400, detail="Error de autenticación")

@app.post("/api/auth/register")
@limiter.limit("3/minute")
async def register(request: Request, user_data: UserLogin):
    """Registrar nuevo usuario con rate limiting"""
    print(f"📝 Intento de registro: {user_data.email}")
    
    if not ProfeGoUtils.validar_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email inválido")
    
    if not ProfeGoUtils.validar_password(user_data.password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    try:
        auth.create_user_with_email_and_password(user_data.email, user_data.password)
        gcs_storage.inicializar_usuario(user_data.email)
        
        print(f"✅ Registro exitoso: {user_data.email}")
        
        return {"message": "Usuario registrado correctamente. Ya puedes iniciar sesión."}
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error en registro: {error_msg}")
        
        if "EMAIL_EXISTS" in error_msg:
            raise HTTPException(status_code=400, detail="Este email ya está registrado")
        else:
            raise HTTPException(status_code=400, detail="Error en el registro")

# ---------------- Rutas de Archivos ----------------
@app.post("/api/files/upload", response_model=ProcessingResult)
@limiter.limit("10/minute")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Subir y procesar archivos con validaciones"""
    user_email = current_user["email"]
    
    archivos_subidos = []
    archivos_procesados = []
    errores_procesamiento = []
    
    for file in files:
        try:
            # Validar extensión
            if not ProfeGoUtils.validar_extension(file.filename):
                errores_procesamiento.append(
                    f"{file.filename}: Tipo de archivo no permitido"
                )
                continue
            
            # Leer contenido del archivo
            content = await file.read()
            
            # Validar tamaño
            if len(content) > MAX_FILE_SIZE:
                errores_procesamiento.append(
                    f"{file.filename}: Archivo muy grande (máx: 20MB)"
                )
                continue
            
            # Crear archivo temporal para procesamiento
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                # Subir archivo original a GCS
                resultado_subida = gcs_storage.subir_archivo_desde_bytes(
                    contenido=content,
                    email=user_email,
                    nombre_archivo=file.filename,
                    es_procesado=False
                )
                
                if resultado_subida['success']:
                    archivos_subidos.append(file.filename)
                    
                    # Verificar si es procesable
                    verificacion = check_supported_file(tmp_file_path)
                    
                    if verificacion['supported']:
                        # Procesar archivo
                        nombre_base = Path(file.filename).stem
                        resultado_conversion = process_file_to_txt(tmp_file_path)
                        
                        if resultado_conversion['success']:
                            # Leer el archivo procesado
                            with open(resultado_conversion['output_file'], 'rb') as f:
                                contenido_procesado = f.read()
                            
                            # Subir archivo procesado a GCS
                            resultado_txt = gcs_storage.subir_archivo_desde_bytes(
                                contenido=contenido_procesado,
                                email=user_email,
                                nombre_archivo=f"{nombre_base}_procesado.txt",
                                es_procesado=True
                            )
                            
                            if resultado_txt['success']:
                                archivos_procesados.append({
                                    'original': file.filename,
                                    'txt': f"{nombre_base}_procesado.txt"
                                })
                            
                            # Limpiar archivo procesado temporal
                            if os.path.exists(resultado_conversion['output_file']):
                                os.remove(resultado_conversion['output_file'])
                else:
                    errores_procesamiento.append(
                        f"{file.filename}: Error subiendo a GCS"
                    )
                    
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
                    
        except Exception as ex:
            errores_procesamiento.append(f"{file.filename}: {str(ex)}")
    
    message = f"Archivos subidos: {len(archivos_subidos)}"
    if archivos_procesados:
        message += f", Procesados: {len(archivos_procesados)}"
    
    return ProcessingResult(
        success=len(archivos_subidos) > 0,
        files_uploaded=len(archivos_subidos),
        files_processed=len(archivos_procesados),
        message=message,
        errors=errores_procesamiento
    )

@app.get("/api/files/list")
async def list_files(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=100),  # Aumentado para desarrollo
    current_user: dict = Depends(get_current_user)
):
    """Listar archivos sin paginación estricta para desarrollo"""
    user_email = current_user["email"]
    files_info = []
    
    try:
        # Obtener todos los archivos
        archivos_originales = gcs_storage.listar_archivos(user_email, "uploads")
        archivos_procesados = gcs_storage.listar_archivos(user_email, "processed")
        
        # Combinar y formatear
        for archivo in archivos_originales:
            files_info.append({
                "name": archivo['name'],
                "type": ProfeGoUtils.obtener_tipo_archivo(archivo['name']),
                "size": f"{archivo['size_mb']} MB",
                "category": "original",
                "date": archivo['date']
            })
        
        for archivo in archivos_procesados:
            files_info.append({
                "name": archivo['name'],
                "type": "TXT Procesado",
                "size": f"{archivo['size_mb']} MB",
                "category": "procesado",
                "date": archivo['date']
            })
        
        # Retornar lista simple (sin paginación para simplificar)
        return files_info
        
    except Exception as e:
        print(f"❌ Error listando archivos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listando archivos: {str(e)}")

@app.get("/api/files/download/{category}/{filename}")
async def download_file(
    category: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Descargar archivo directamente desde GCS"""
    user_email = current_user["email"]
    
    try:
        es_procesado = category == "procesado"
        
        # Obtener el archivo desde GCS
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=es_procesado
        )
        
        if contenido is None:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Determinar el tipo MIME
        content_type = "application/octet-stream"
        ext = Path(filename).suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        content_type = mime_types.get(ext, content_type)
        
        # Retornar el archivo como stream
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error descargando archivo: {str(ex)}")

@app.get("/api/files/preview/{category}/{filename}")
async def preview_file(
    category: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Vista previa de archivo - devuelve contenido según tipo"""
    user_email = current_user["email"]
    
    try:
        es_procesado = category == "procesado"
        
        # Obtener el archivo desde GCS
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=es_procesado
        )
        
        if contenido is None:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Detectar tipo de archivo
        ext = Path(filename).suffix.lower()
        
        # Para PDFs e imágenes, devolver el archivo directamente
        if ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            mime_types = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp'
            }
            
            return StreamingResponse(
                io.BytesIO(contenido),
                media_type=mime_types.get(ext, 'application/octet-stream'),
                headers={"Content-Disposition": f"inline; filename={filename}"}
            )
        
        # Para archivos TXT, devolver el contenido como JSON
        elif ext == '.txt':
            try:
                texto = contenido.decode('utf-8')
            except UnicodeDecodeError:
                texto = contenido.decode('latin-1', errors='ignore')
            
            return JSONResponse(content={
                "type": "text",
                "content": texto,
                "filename": filename
            })
        
        else:
            raise HTTPException(
                status_code=400, 
                detail="Tipo de archivo no soportado para vista previa"
            )
            
    except HTTPException:
        raise
    except Exception as ex:
        print(f"Error en preview: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(ex)}")

@app.delete("/api/files/delete/{category}/{filename}")
@limiter.limit("20/minute")
async def delete_file(
    request: Request,
    category: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar archivo de GCS"""
    user_email = current_user["email"]
    
    try:
        es_procesado = category == "procesado"
        
        resultado = gcs_storage.eliminar_archivo(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=es_procesado
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=404, detail=resultado.get('error', 'Archivo no encontrado'))
        
        return {"message": f"Archivo '{filename}' eliminado correctamente"}
        
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error eliminando archivo: {str(ex)}")

@app.get("/api/user/storage-info")
async def get_storage_info(current_user: dict = Depends(get_current_user)):
    """Obtener información de almacenamiento del usuario"""
    user_email = current_user["email"]
    
    try:
        info = gcs_storage.obtener_info_almacenamiento(user_email)
        return info
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error obteniendo información: {str(ex)}")

# ========== RUTAS PARA SERVIR EL FRONTEND ==========

@app.get("/")
async def serve_index():
    """Servir index.html (redirección a login)"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(
            content={
                "message": "ProfeGo API v2.0",
                "status": "running",
                "docs": "/docs",
                "error": "Frontend no encontrado"
            },
            status_code=404
        )

@app.get("/login.html")
async def serve_login():
    """Servir login.html"""
    login_path = os.path.join(FRONTEND_DIR, "login.html")
    
    if os.path.exists(login_path):
        return FileResponse(login_path)
    else:
        raise HTTPException(status_code=404, detail="login.html no encontrado")

@app.get("/menu.html")
async def serve_menu():
    """Servir menu.html"""
    menu_path = os.path.join(FRONTEND_DIR, "menu.html")
    
    if os.path.exists(menu_path):
        return FileResponse(menu_path)
    else:
        raise HTTPException(status_code=404, detail="menu.html no encontrado")

# ========== RUTAS PARA ARCHIVOS ESTÁTICOS ==========

@app.get("/styles.css")
async def serve_styles():
    """Servir styles.css"""
    styles_path = os.path.join(FRONTEND_DIR, "styles.css")
    
    if os.path.exists(styles_path):
        return FileResponse(styles_path, media_type="text/css")
    else:
        raise HTTPException(status_code=404, detail="styles.css no encontrado")

@app.get("/shared.js")
async def serve_shared_js():
    """Servir shared.js"""
    shared_path = os.path.join(FRONTEND_DIR, "shared.js")
    
    if os.path.exists(shared_path):
        return FileResponse(shared_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="shared.js no encontrado")

@app.get("/login-script.js")
async def serve_login_script():
    """Servir login-script.js"""
    script_path = os.path.join(FRONTEND_DIR, "login-script.js")
    
    if os.path.exists(script_path):
        return FileResponse(script_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="login-script.js no encontrado")

@app.get("/menu-script.js")
async def serve_menu_script():
    """Servir menu-script.js"""
    script_path = os.path.join(FRONTEND_DIR, "menu-script.js")
    
    if os.path.exists(script_path):
        return FileResponse(script_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="menu-script.js no encontrado")

@app.get("/health")
async def health_check():
    """Verificar estado del servicio"""
    try:
        gcs_status = "connected" if gcs_storage.bucket.exists() else "disconnected"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "gcs_status": gcs_status,
            "bucket_name": gcs_storage.bucket_name,
            "frontend_dir": FRONTEND_DIR,
            "frontend_exists": os.path.exists(FRONTEND_DIR)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 ProfeGo API v2.0 - Servidor Iniciando")
    print("=" * 60)
    print(f"📁 Frontend: {FRONTEND_DIR}")
    print(f"☁️  GCS Bucket: {gcs_storage.bucket_name}")
    print(f"📦 Límite de archivo: {MAX_FILE_SIZE / (1024*1024)}MB")
    print(f"🔐 CORS Origins: {allowed_origins}")
    print(f"🌐 Servidor: http://127.0.0.1:8000")
    print(f"📖 Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
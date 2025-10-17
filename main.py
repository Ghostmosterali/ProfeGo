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
from typing import List, Optional, Dict
import json
from datetime import datetime
import tempfile
import io
import time
import uuid
import logging
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Importar el módulo OCR
from PruebaOcr import process_file_to_txt, check_supported_file, get_text_only

# Importar el módulo de Google Cloud Storage mejorado
from gcs_storage import GCSStorageManagerV2

# Importar el servicio de Gemini AI
from gemini_service import generar_plan_estudio

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
MAX_FILE_SIZE = 80 * 1024 * 1024  # 80MB
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
    print(f"⚠️ ADVERTENCIA: No se encontró el directorio frontend en {FRONTEND_DIR}")
else:
    print(f"✅ Frontend encontrado en: {FRONTEND_DIR}")
    
    # Montar archivos estáticos ANTES de definir las rutas
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

class PlanGenerationRequest(BaseModel):
    plan_filename: str
    diagnostico_filename: Optional[str] = None

class PlanResponse(BaseModel):
    success: bool
    plan_id: Optional[str] = None
    plan_data: Optional[Dict] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

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
        logger.error(f"Error verificando token: {e}")
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================

@app.post("/api/auth/login", response_model=UserResponse)
@limiter.limit("10/minute")
async def login(request: Request, user_data: UserLogin):
    """Iniciar sesión con rate limiting"""
    logger.info(f"📧 Intento de login: {user_data.email}")
    
    if not ProfeGoUtils.validar_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email inválido")
    
    if not ProfeGoUtils.validar_password(user_data.password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    try:
        user = auth.sign_in_with_email_and_password(user_data.email, user_data.password)
        
        # Inicializar estructura en GCS
        gcs_storage.inicializar_usuario(user_data.email)
        
        logger.info(f"✅ Login exitoso: {user_data.email}")
        
        return UserResponse(
            email=user_data.email,
            token=user.get("idToken"),
            message=f"Bienvenido/a {user_data.email}"
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error en login: {error_msg}")
        
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
    logger.info(f"📝 Intento de registro: {user_data.email}")
    
    if not ProfeGoUtils.validar_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email inválido")
    
    if not ProfeGoUtils.validar_password(user_data.password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    try:
        auth.create_user_with_email_and_password(user_data.email, user_data.password)
        gcs_storage.inicializar_usuario(user_data.email)
        
        logger.info(f"✅ Registro exitoso: {user_data.email}")
        
        return {"message": "Usuario registrado correctamente. Ya puedes iniciar sesión."}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error en registro: {error_msg}")
        
        if "EMAIL_EXISTS" in error_msg:
            raise HTTPException(status_code=400, detail="Este email ya está registrado")
        else:
            raise HTTPException(status_code=400, detail="Error en el registro")

# ============================================================================
# RUTAS DE ARCHIVOS
# ============================================================================

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
                    f"{file.filename}: Archivo muy grande (máx: 80MB)"
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
    per_page: int = Query(100, ge=1, le=100),
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
        
        # Filtrar archivos procesados (excluir planes JSON)
        for archivo in archivos_procesados:
            # Excluir archivos que son planes generados
            if not archivo['name'].startswith('plan_') or not archivo['name'].endswith('.json'):
                files_info.append({
                    "name": archivo['name'],
                    "type": "TXT Procesado",
                    "size": f"{archivo['size_mb']} MB",
                    "category": "procesado",
                    "date": archivo['date']
                })
        
        return files_info
        
    except Exception as e:
        logger.error(f"❌ Error listando archivos: {str(e)}")
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
        logger.error(f"Error en preview: {str(ex)}")
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

def generar_documento_word(plan_data: Dict) -> io.BytesIO:
    """
    Genera un documento Word profesional a partir de los datos del plan
    """
    doc = Document()
    
    # Configurar estilos del documento
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(12)
    p_format = style.paragraph_format
    p_format.line_spacing = 1.5
    # ========== PORTADA ==========
    portada = doc.add_heading(plan_data.get('nombre_plan', 'Plan Educativo'), 0)
    portada.alignment = WD_ALIGN_PARAGRAPH.CENTER
    portada.runs[0].font.color.rgb = RGBColor(0, 102, 204)
    
    # Información general
    info_general = doc.add_paragraph()
    info_general.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if plan_data.get('grado'):
        run = info_general.add_run(f"Grado: {plan_data['grado']}\n")
        run.bold = True
        run.font.size = Pt(12)
    
    if plan_data.get('edad_aprox'):
        run = info_general.add_run(f"Edad aproximada: {plan_data['edad_aprox']}\n")
        run.font.size = Pt(12)
    
    if plan_data.get('duracion_total'):
        run = info_general.add_run(f"Duración total: {plan_data['duracion_total']}\n")
        run.font.size = Pt(12)

    if plan_data.get('fecha_generacion'):
        fecha = datetime.fromisoformat(plan_data['fecha_generacion']).strftime('%d/%m/%Y %H:%M')
        run = info_general.add_run(f"Generado: {fecha}\n")
        run.font.size = Pt(12)
        run.italic = True
    
    doc.add_paragraph()  # Espacio
    
    # Campo formativo y ejes
    if plan_data.get('campo_formativo_principal'):
        p = doc.add_paragraph()
        p.add_run('Campo Formativo Principal: ').bold = True
        p.add_run(plan_data['campo_formativo_principal'])
    
    if plan_data.get('ejes_articuladores_generales'):
        p = doc.add_paragraph()
        p.add_run('Ejes Articuladores: ').bold = True
        p.add_run(', '.join(plan_data['ejes_articuladores_generales']))
    
    doc.add_page_break()
    
    # ========== MÓDULOS ==========
    doc.add_heading('📚 Módulos del Plan', 1)
    
    modulos = plan_data.get('modulos', [])
    
    for idx, modulo in enumerate(modulos, 1):
        # Encabezado del módulo
        modulo_heading = doc.add_heading(f"Módulo {modulo.get('numero', idx)}: {modulo.get('nombre', '')}", 2)
        modulo_heading.runs[0].font.color.rgb = RGBColor(0, 102, 204)
        
        # Información del módulo
        if modulo.get('campo_formativo'):
            p = doc.add_paragraph()
            p.add_run('📘 Campo Formativo: ').bold = True
            p.add_run(modulo['campo_formativo'])
        
        if modulo.get('ejes_articuladores'):
            p = doc.add_paragraph()
            p.add_run('🔗 Ejes Articuladores: ').bold = True
            p.add_run(', '.join(modulo['ejes_articuladores']))
        
        if modulo.get('aprendizaje_esperado'):
            p = doc.add_paragraph()
            p.add_run('🎯 Aprendizaje Esperado: ').bold = True
            p.add_run(modulo['aprendizaje_esperado'])
        
        if modulo.get('tiempo_estimado'):
            p = doc.add_paragraph()
            p.add_run('⏱️ Tiempo Estimado: ').bold = True
            p.add_run(modulo['tiempo_estimado'])
        
        doc.add_paragraph()  # Espacio
        
        # Actividad de inicio
        if modulo.get('actividad_inicio'):
            doc.add_heading('🎬 Actividad de Inicio', 3)
            inicio = modulo['actividad_inicio']
            
            p = doc.add_paragraph()
            p.add_run('Nombre: ').bold = True
            p.add_run(inicio.get('nombre', ''))
            
            p = doc.add_paragraph()
            p.add_run('Descripción: ').bold = True
            p.add_run(inicio.get('descripcion', ''))
            
            if inicio.get('duracion'):
                p = doc.add_paragraph()
                p.add_run('Duración: ').bold = True
                p.add_run(inicio['duracion'])
            
            if inicio.get('materiales'):
                p = doc.add_paragraph()
                p.add_run('Materiales: ').bold = True
                materiales = inicio['materiales'] if isinstance(inicio['materiales'], list) else [inicio['materiales']]
                p.add_run(', '.join(materiales))
            
            if inicio.get('organizacion'):
                p = doc.add_paragraph()
                p.add_run('Organización: ').bold = True
                p.add_run(inicio['organizacion'])
        
        # Actividades de desarrollo
        if modulo.get('actividades_desarrollo'):
            doc.add_heading('🚀 Actividades de Desarrollo', 3)
            
            for act_idx, actividad in enumerate(modulo['actividades_desarrollo'], 1):
                doc.add_heading(f"Actividad {act_idx}: {actividad.get('nombre', '')}", 4)
                
                if actividad.get('tipo'):
                    p = doc.add_paragraph()
                    p.add_run('Tipo: ').bold = True
                    p.add_run(actividad['tipo'])
                
                if actividad.get('descripcion'):
                    p = doc.add_paragraph()
                    p.add_run('Descripción: ').bold = True
                    p.add_run(actividad['descripcion'])
                
                if actividad.get('duracion'):
                    p = doc.add_paragraph()
                    p.add_run('Duración: ').bold = True
                    p.add_run(actividad['duracion'])
                
                if actividad.get('organizacion'):
                    p = doc.add_paragraph()
                    p.add_run('Organización: ').bold = True
                    p.add_run(actividad['organizacion'])
                
                if actividad.get('materiales'):
                    p = doc.add_paragraph()
                    p.add_run('Materiales: ').bold = True
                    materiales = actividad['materiales'] if isinstance(actividad['materiales'], list) else [actividad['materiales']]
                    p.add_run(', '.join(materiales))
                
                if actividad.get('aspectos_a_observar'):
                    p = doc.add_paragraph()
                    p.add_run('Aspectos a observar: ').bold = True
                    p.add_run(actividad['aspectos_a_observar'])
                
                doc.add_paragraph()  # Espacio entre actividades
        
        # Actividad de cierre
        if modulo.get('actividad_cierre'):
            doc.add_heading('🎬 Actividad de Cierre', 3)
            cierre = modulo['actividad_cierre']
            
            p = doc.add_paragraph()
            p.add_run('Nombre: ').bold = True
            p.add_run(cierre.get('nombre', ''))
            
            p = doc.add_paragraph()
            p.add_run('Descripción: ').bold = True
            p.add_run(cierre.get('descripcion', ''))
            
            if cierre.get('duracion'):
                p = doc.add_paragraph()
                p.add_run('Duración: ').bold = True
                p.add_run(cierre['duracion'])
            
            if cierre.get('preguntas_guia'):
                p = doc.add_paragraph()
                p.add_run('Preguntas guía:').bold = True
                for pregunta in cierre['preguntas_guia']:
                    doc.add_paragraph(f"• {pregunta}", style='List Bullet')
        
        # Información adicional del módulo
        if modulo.get('consejos_maestra'):
            doc.add_heading('💡 Consejos para la Maestra', 3)
            doc.add_paragraph(modulo['consejos_maestra'])
        
        if modulo.get('variaciones'):
            doc.add_heading('🔄 Variaciones', 3)
            doc.add_paragraph(modulo['variaciones'])
        
        if modulo.get('vinculo_familia'):
            doc.add_heading('🏠 Vínculo con la Familia', 3)
            doc.add_paragraph(modulo['vinculo_familia'])
        
        if modulo.get('evaluacion'):
            doc.add_heading('📋 Evaluación', 3)
            doc.add_paragraph(modulo['evaluacion'])
        
        # Separador entre módulos
        if idx < len(modulos):
            doc.add_page_break()
    
    # ========== RECURSOS EDUCATIVOS ==========
    if plan_data.get('recursos_educativos'):
        doc.add_page_break()
        doc.add_heading('📚 Recursos Educativos', 1)
        recursos = plan_data['recursos_educativos']
        
        if recursos.get('materiales_generales'):
            doc.add_heading('🛠️ Materiales Generales', 2)
            for material in recursos['materiales_generales']:
                doc.add_paragraph(f"• {material}", style='List Bullet')
        
        if recursos.get('cuentos_recomendados'):
            doc.add_heading('📖 Cuentos Recomendados', 2)
            for cuento in recursos['cuentos_recomendados']:
                p = doc.add_paragraph()
                p.add_run(f"• {cuento.get('titulo', '')}: ").bold = True
                
                detalles = []
                if cuento.get('autor'):
                    detalles.append(f"Autor: {cuento['autor']}")
                if cuento.get('tipo'):
                    detalles.append(f"Tipo: {cuento['tipo']}")
                if cuento.get('acceso'):
                    detalles.append(f"Acceso: {cuento['acceso']}")
                if cuento.get('disponibilidad'):
                    detalles.append(f"Disponibilidad: {cuento['disponibilidad']}")
                
                p.add_run(' | '.join(detalles))
                
                if cuento.get('descripcion_breve'):
                    doc.add_paragraph(f"  {cuento['descripcion_breve']}", style='List Bullet 2')
        
        if recursos.get('canciones_recomendadas'):
            doc.add_heading('🎵 Canciones Recomendadas', 2)
            for cancion in recursos['canciones_recomendadas']:
                p = doc.add_paragraph()
                p.add_run(f"• {cancion.get('titulo', '')}: ").bold = True
                
                detalles = []
                if cancion.get('tipo'):
                    detalles.append(f"Tipo: {cancion['tipo']}")
                if cancion.get('acceso'):
                    detalles.append(f"Acceso: {cancion['acceso']}")
                if cancion.get('disponibilidad'):
                    detalles.append(f"Disponibilidad: {cancion['disponibilidad']}")
                
                p.add_run(' | '.join(detalles))
                
                if cancion.get('uso_sugerido'):
                    doc.add_paragraph(f"  Uso sugerido: {cancion['uso_sugerido']}", style='List Bullet 2')
    
    # ========== RECOMENDACIONES DE AMBIENTE ==========
    if plan_data.get('recomendaciones_ambiente'):
        doc.add_heading('🏫 Recomendaciones para el Ambiente', 2)
        doc.add_paragraph(plan_data['recomendaciones_ambiente'])
    
    # ========== VINCULACIÓN CURRICULAR ==========
    if plan_data.get('vinculacion_curricular'):
        doc.add_heading('🔗 Vinculación Curricular', 2)
        vinculacion = plan_data['vinculacion_curricular']
        
        if vinculacion.get('campo_formativo_principal'):
            p = doc.add_paragraph()
            p.add_run('Campo Formativo Principal: ').bold = True
            p.add_run(vinculacion['campo_formativo_principal'])
        
        if vinculacion.get('campos_secundarios'):
            p = doc.add_paragraph()
            p.add_run('Campos Secundarios: ').bold = True
            p.add_run(', '.join(vinculacion['campos_secundarios']))
        
        if vinculacion.get('ejes_transversales'):
            p = doc.add_paragraph()
            p.add_run('Ejes Transversales: ').bold = True
            p.add_run(', '.join(vinculacion['ejes_transversales']))
        
        if vinculacion.get('aprendizajes_clave'):
            doc.add_heading('Aprendizajes Clave:', 3)
            for aprendizaje in vinculacion['aprendizajes_clave']:
                doc.add_paragraph(f"• {aprendizaje}", style='List Bullet')
    
    # Guardar en memoria
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    
    return docx_bytes

# ============================================================================
# RUTAS PARA GENERACIÓN DE PLANES CON IA
# ============================================================================

@app.post("/api/plans/generate", response_model=PlanResponse)
@limiter.limit("5/hour")  # Límite: 5 planes por hora
async def generate_plan(
    request: Request,
    plan_file: UploadFile = File(..., description="Archivo del plan de estudios"),
    diagnostico_file: Optional[UploadFile] = File(None, description="Archivo de diagnóstico (opcional)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Genera un plan de estudio personalizado usando Gemini AI
    
    - **plan_file**: Archivo obligatorio con el plan de estudios oficial
    - **diagnostico_file**: Archivo opcional con diagnóstico del grupo
    
    Proceso:
    1. Extrae texto de los archivos con OCR
    2. Envía a Gemini AI para análisis y estructuración
    3. Guarda el plan generado en GCS
    4. Retorna la estructura completa del plan
    """
    user_email = current_user["email"]
    start_time = time.time()
    
    logger.info(f"🎓 Generando plan para usuario: {user_email}")
    
    try:
        # ========== VALIDACIÓN DE ARCHIVOS ==========
        
        # Validar archivo del plan
        if not ProfeGoUtils.validar_extension(plan_file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido para plan: {plan_file.filename}"
            )
        
        plan_content = await plan_file.read()
        if len(plan_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="El archivo del plan excede el límite de 80MB"
            )
        
        # Validar archivo de diagnóstico (si existe)
        diagnostico_content = None
        diagnostico_filename = None
        
        if diagnostico_file and diagnostico_file.filename:
            if not ProfeGoUtils.validar_extension(diagnostico_file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de archivo no permitido para diagnóstico: {diagnostico_file.filename}"
                )
            
            diagnostico_content = await diagnostico_file.read()
            if len(diagnostico_content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail="El archivo de diagnóstico excede el límite de 80MB"
                )
            diagnostico_filename = diagnostico_file.filename
        
        logger.info(f"✅ Archivos validados - Plan: {plan_file.filename}, Diagnóstico: {diagnostico_filename or 'No proporcionado'}")
        
        # ========== PROCESAMIENTO OCR ==========
        
        logger.info("📄 Extrayendo texto del plan de estudios...")
        
        # Guardar plan temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(plan_file.filename).suffix) as tmp_plan:
            tmp_plan.write(plan_content)
            tmp_plan_path = tmp_plan.name
        
        try:
            # Extraer texto del plan
            plan_result = get_text_only(tmp_plan_path)
            
            if not plan_result['success'] or not plan_result['text']:
                raise HTTPException(
                    status_code=400,
                    detail=f"No se pudo extraer texto del plan: {plan_result.get('error', 'Error desconocido')}"
                )
            
            plan_text = plan_result['text']
            logger.info(f"✅ Texto extraído del plan: {len(plan_text)} caracteres")
            
            # Extraer texto del diagnóstico si existe
            diagnostico_text = None
            
            if diagnostico_content:
                logger.info("📄 Extrayendo texto del diagnóstico...")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(diagnostico_filename).suffix) as tmp_diag:
                    tmp_diag.write(diagnostico_content)
                    tmp_diag_path = tmp_diag.name
                
                try:
                    diagnostico_result = get_text_only(tmp_diag_path)
                    
                    if diagnostico_result['success'] and diagnostico_result['text']:
                        diagnostico_text = diagnostico_result['text']
                        logger.info(f"✅ Texto extraído del diagnóstico: {len(diagnostico_text)} caracteres")
                    else:
                        logger.warning(f"⚠️ No se pudo extraer texto del diagnóstico, continuando sin él")
                        diagnostico_text = None
                
                finally:
                    if os.path.exists(tmp_diag_path):
                        os.remove(tmp_diag_path)
            
        finally:
            # Limpiar archivo temporal del plan
            if os.path.exists(tmp_plan_path):
                os.remove(tmp_plan_path)
        
        # ========== GENERACIÓN CON GEMINI ==========
        
        logger.info("🤖 Generando plan con Gemini AI...")
        
        resultado_gemini = await generar_plan_estudio(
            plan_text=plan_text,
            diagnostico_text=diagnostico_text
        )
        
        if not resultado_gemini['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Error generando plan con IA: {resultado_gemini.get('error', 'Error desconocido')}"
            )
        
        plan_data = resultado_gemini['plan']
        
        logger.info(f"✅ Plan generado: {plan_data['nombre_plan']}")
        logger.info(f"📊 Módulos: {plan_data.get('num_modulos', len(plan_data['modulos']))}")
        
        # ========== GUARDAR EN GCS ==========
        
        # Generar ID único para el plan
        plan_id = f"plan_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        
        # Agregar metadata al plan
        plan_data['plan_id'] = plan_id
        plan_data['usuario'] = user_email
        plan_data['fecha_generacion'] = datetime.now().isoformat()
        plan_data['archivos_originales'] = {
            'plan': plan_file.filename,
            'diagnostico': diagnostico_filename
        }
        
        # Guardar plan como JSON en GCS
        plan_json = json.dumps(plan_data, indent=2, ensure_ascii=False)
        plan_json_bytes = plan_json.encode('utf-8')
        
        resultado_guardado = gcs_storage.subir_archivo_desde_bytes(
            contenido=plan_json_bytes,
            email=user_email,
            nombre_archivo=f"{plan_id}.json",
            es_procesado=True  # Guardar en carpeta "processed"
        )
        
        if not resultado_guardado['success']:
            logger.warning(f"⚠️ No se pudo guardar el plan en GCS: {resultado_guardado.get('error')}")
        else:
            logger.info(f"✅ Plan guardado en GCS: {resultado_guardado['path']}")
        
        # ========== GUARDAR ARCHIVOS ORIGINALES ==========
        
        # Subir plan original
        gcs_storage.subir_archivo_desde_bytes(
            contenido=plan_content,
            email=user_email,
            nombre_archivo=plan_file.filename,
            es_procesado=False
        )
        
        # Subir diagnóstico si existe
        if diagnostico_content:
            gcs_storage.subir_archivo_desde_bytes(
                contenido=diagnostico_content,
                email=user_email,
                nombre_archivo=diagnostico_filename,
                es_procesado=False
            )
        
        # ========== RETORNAR RESULTADO ==========
        
        processing_time = time.time() - start_time
        logger.info(f"⏱️ Tiempo total de procesamiento: {processing_time:.2f} segundos")
        
        return PlanResponse(
            success=True,
            plan_id=plan_id,
            plan_data=plan_data,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generando plan: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado generando plan: {str(e)}"
        )


@app.get("/api/plans/list")
async def list_plans(
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todos los planes generados del usuario
    """
    user_email = current_user["email"]
    
    try:
        # Obtener archivos JSON de la carpeta processed
        archivos_procesados = gcs_storage.listar_archivos(user_email, "processed")
        
        planes = []
        
        for archivo in archivos_procesados:
            # Solo archivos JSON que empiezan con "plan_"
            if archivo['name'].startswith('plan_') and archivo['name'].endswith('.json'):
                # Obtener el contenido del plan
                contenido = gcs_storage.obtener_archivo_bytes(
                    email=user_email,
                    nombre_archivo=archivo['name'],
                    es_procesado=True
                )
                
                if contenido:
                    try:
                        plan_data = json.loads(contenido.decode('utf-8'))
                        
                        # IMPORTANTE: Incluir TODOS los campos necesarios
                        planes.append({
                            'plan_id': plan_data.get('plan_id'),
                            'nombre_plan': plan_data.get('nombre_plan'),
                            'grado': plan_data.get('grado'),
                            
                            # ✅ NUEVA ESTRUCTURA (Preescolar mejorado)
                            'campo_formativo_principal': plan_data.get('campo_formativo_principal'),
                            'ejes_articuladores_generales': plan_data.get('ejes_articuladores_generales', []),
                            'edad_aprox': plan_data.get('edad_aprox'),
                            'duracion_total': plan_data.get('duracion_total'),
                            
                            # ❌ ESTRUCTURA ANTIGUA (para retrocompatibilidad)
                            'materia': plan_data.get('materia'),
                            
                            # Campos comunes
                            'num_modulos': plan_data.get('num_modulos', len(plan_data.get('modulos', []))),
                            'fecha_generacion': plan_data.get('fecha_generacion'),
                            'tiene_diagnostico': plan_data.get('tiene_diagnostico', False),
                            'archivos_originales': plan_data.get('archivos_originales', {}),
                            'generado_con': plan_data.get('generado_con'),
                            'modelo': plan_data.get('modelo')
                        })
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ No se pudo parsear el plan: {archivo['name']}")
        
        # Ordenar por fecha (más recientes primero)
        planes.sort(key=lambda x: x.get('fecha_generacion', ''), reverse=True)
        
        return {
            'success': True,
            'planes': planes,
            'total': len(planes)
        }
        
    except Exception as e:
        logger.error(f"❌ Error listando planes: {e}")
        raise HTTPException(status_code=500, detail=f"Error listando planes: {str(e)}")

@app.get("/api/plans/{plan_id}/download")
async def download_plan_word(
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Descarga el plan como documento Word (.docx) profesional
    """
    user_email = current_user["email"]
    
    try:
        # Obtener el plan desde GCS
        filename = f"{plan_id}.json"
        
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=True
        )
        
        if not contenido:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        plan_data = json.loads(contenido.decode('utf-8'))
        
        # Generar documento Word
        docx_bytes = generar_documento_word(plan_data)
        
        # Crear nombre de archivo seguro
        nombre_plan = plan_data.get('nombre_plan', 'Plan_Educativo')
        nombre_archivo = f"{nombre_plan.replace(' ', '_').replace('/', '_')}.docx"
        
        # Retornar archivo Word
        return StreamingResponse(
            docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_archivo}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generando documento Word: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando documento: {str(e)}")


@app.get("/api/plans/{plan_id}")
async def get_plan_detail(
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el detalle completo de un plan específico
    """
    user_email = current_user["email"]
    
    try:
        # Obtener el archivo JSON del plan
        filename = f"{plan_id}.json"
        
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=True
        )
        
        if not contenido:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        plan_data = json.loads(contenido.decode('utf-8'))
        
        return {
            'success': True,
            'plan': plan_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo plan: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo plan: {str(e)}")


@app.delete("/api/plans/{plan_id}")
@limiter.limit("10/minute")
async def delete_plan(
    request: Request,
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Elimina un plan generado
    """
    user_email = current_user["email"]
    
    try:
        filename = f"{plan_id}.json"
        
        resultado = gcs_storage.eliminar_archivo(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=True
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        return {
            'success': True,
            'message': 'Plan eliminado correctamente'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error eliminando plan: {e}")
        raise HTTPException(status_code=500, detail=f"Error eliminando plan: {str(e)}")

# ============================================================================
# RUTAS PARA SERVIR EL FRONTEND
# ============================================================================

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
        
        # Verificar si Gemini está configurado
        gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "gcs_status": gcs_status,
            "bucket_name": gcs_storage.bucket_name,
            "frontend_dir": FRONTEND_DIR,
            "frontend_exists": os.path.exists(FRONTEND_DIR),
            "gemini_configured": gemini_configured,
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 ProfeGo API v2.0 - Servidor Iniciando")
    print("=" * 60)
    print(f"📁 Frontend: {FRONTEND_DIR}")
    print(f"☁️ GCS Bucket: {gcs_storage.bucket_name}")
    print(f"📦 Límite de archivo: {MAX_FILE_SIZE / (1024*1024)}MB")
    print(f"🔐 CORS Origins: {allowed_origins}")
    print(f"🤖 Gemini AI: {'✅ Configurado' if os.getenv('GEMINI_API_KEY') else '❌ No configurado'}")
    print(f"🌐 Servidor: http://127.0.0.1:8000")
    print(f"📖 Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
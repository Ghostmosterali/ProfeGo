# ProfeGo - Sistema de Gestión de Archivos con OCR

Sistema completo de gestión de archivos con procesamiento OCR, almacenamiento en Google Cloud Storage y autenticación con Firebase.

## 🚀 Características

- ✅ Autenticación de usuarios con Firebase Auth
- ☁️ Almacenamiento en Google Cloud Storage
- 📄 Procesamiento OCR de múltiples formatos (PDF, imágenes, Word, Excel, etc.)
- 📁 Estructura de carpetas por usuario
- 🔒 Gestión segura de archivos

## 📋 Requisitos Previos

- Python 3.12.8
- Cuenta de Google Cloud Platform
- Proyecto de Firebase
- Tesseract OCR instalado

## 🛠️ Instalación

### 1. Clonar el repositorio e instalar dependencias

```bash
# Instalar las dependencias de Python
pip install fastapi uvicorn python-dotenv
pip install pyrebase4 google-cloud-storage
pip install opencv-python pytesseract
pip install python-docx PyPDF2 pandas openpyxl
```

### 2. Instalar Tesseract OCR

**Windows:**
```bash
# Descargar desde: https://github.com/UB-Mannheim/tesseract/wiki
# Agregar al PATH o configurar en PruebaOcr.py:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-spa  # Para español
```

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # Para idiomas adicionales
```

### 3. Configurar Google Cloud Storage

#### a) Crear Service Account

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Selecciona tu proyecto o crea uno nuevo
3. Navega a **IAM & Admin** > **Service Accounts**
4. Clic en **Create Service Account**
5. Asigna los siguientes roles:
   - `Storage Object Admin`
   - `Storage Object Creator`
   - `Storage Object Viewer`
6. Crea una clave JSON y descárgala

#### b) Crear el Bucket

```bash
# Opción 1: Desde la consola web
# Ve a Cloud Storage > Buckets > Create Bucket

# Opción 2: Desde la línea de comandos
gsutil mb -p TU_PROJECT_ID -c STANDARD -l us-central1 gs://bucket-profe-go
```

#### c) Configurar credenciales

**Windows (PowerShell):**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\ruta\a\tu-service-account-key.json"

# Para hacerlo permanente:
[System.Environment]::SetEnvironmentVariable('GOOGLE_APPLICATION_CREDENTIALS', 'C:\ruta\a\tu-service-account-key.json', 'User')
```

**Linux/macOS:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/ruta/a/tu-service-account-key.json"

# Para hacerlo permanente, agregar a ~/.bashrc o ~/.zshrc:
echo 'export GOOGLE_APPLICATION_CREDENTIALS="/ruta/a/tu-service-account-key.json"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Configurar Firebase (Solo para Auth)

1. Ve a [Firebase Console](https://console.firebase.google.com)
2. Crea un proyecto o selecciona uno existente
3. Ve a **Project Settings** > **General**
4. Copia la configuración de tu web app
5. Habilita **Authentication** > **Email/Password**

### 5. Crear archivo .env

Crea un archivo `.env` en la raíz del proyecto:

```env
# Firebase (Auth)
FIREBASE_API_KEY=tu_api_key
FIREBASE_AUTH_DOMAIN=tu_proyecto.firebaseapp.com
FIREBASE_PROJECT_ID=tu_proyecto_id
FIREBASE_STORAGE_BUCKET=tu_proyecto.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abc123
FIREBASE_DATABASE_URL=https://tu_proyecto.firebaseio.com

# Google Cloud Storage
GCS_BUCKET_NAME=bucket-profe-go
GOOGLE_APPLICATION_CREDENTIALS=ruta/a/tu-service-account-key.json
```

## 📂 Estructura del Proyecto

```
ProfeGo/
├── main.py                          # API principal con FastAPI
├── gcs_storage.py                   # Módulo de Google Cloud Storage
├── PruebaOcr.py                     # Módulo de procesamiento OCR
├── bucket.py                        # Ejemplos de uso de GCS
├── .env                             # Variables de entorno (NO SUBIR A GIT)
├── .env.example                     # Ejemplo de variables
├── frontend/                        # Archivos del frontend
│   └── index.html
└── tu-service-account-key.json      # Credenciales GCS (NO SUBIR A GIT)
```

## 🚀 Ejecutar el Proyecto

```bash
# Ejecutar el servidor
python main.py

# O con uvicorn directamente
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

El servidor estará disponible en:
- **Frontend:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs
- **Health Check:** http://127.0.0.1:8000/health

## 📚 Uso de la API

### Autenticación

**Registrar usuario:**
```bash
curl -X POST "http://127.0.0.1:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@ejemplo.com", "password": "password123"}'
```

**Iniciar sesión:**
```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@ejemplo.com", "password": "password123"}'
```

### Gestión de Archivos

**Subir archivo:**
```bash
curl -X POST "http://127.0.0.1:8000/api/files/upload?user_email=usuario@ejemplo.com" \
  -F "files=@documento.pdf"
```

**Listar archivos:**
```bash
curl "http://127.0.0.1:8000/api/files/list?user_email=usuario@ejemplo.com"
```

**Eliminar archivo:**
```bash
curl -X DELETE "http://127.0.0.1:8000/api/files/delete/original/documento.pdf?user_email=usuario@ejemplo.com"
```

## 🗂️ Estructura en GCS

Los archivos se organizan así en el bucket:

```
bucket-profe-go/
└── Carpeta_Archivos/
    ├── usuario_ejemplo_com/
    │   ├── ARCHIVOS_SUBIDOS/
    │   │   ├── documento1.pdf
    │   │   └── imagen1.jpg
    │   └── ARCHIVOS_DESCARGA/
    │       ├── documento1_procesado.txt
    │       └── imagen1_procesado.txt
    └── otro_usuario_com/
        ├── ARCHIVOS_SUBIDOS/
        └── ARCHIVOS_DESCARGA/
```

## 🔧 Verificar Configuración

### Probar conexión con GCS

```python
# Ejecutar bucket.py para probar la conexión
python bucket.py
```

### Probar el módulo de storage

```python
# Ejecutar gcs_storage.py
python gcs_storage.py
```

## ⚠️ Notas Importantes

1. **Nunca subas a Git:**
   - Archivo `.env`
   - Archivo `*-service-account-key.json`
   - Carpeta `Documents/ProfeGo_Biblioteca/`

2. **Agregar al .gitignore:**
```gitignore
.env
*-service-account-key.json
*.json
Documents/
__pycache__/
*.pyc
```

3. **Seguridad:**
   - En producción, implementa autenticación real con tokens
   - Valida permisos de usuarios
   - Usa HTTPS
   - Configura CORS correctamente

4. **Costos:**
   - GCS tiene costos por almacenamiento y transferencia
   - Monitorea el uso desde [GCP Console](https://console.cloud.google.com)

## 🐛 Solución de Problemas

### Error: "Could not automatically determine credentials"

```bash
# Verificar que la variable esté configurada
echo $GOOGLE_APPLICATION_CREDENTIALS  # Linux/macOS
echo %GOOGLE_APPLICATION_CREDENTIALS%  # Windows CMD
$env:GOOGLE_APPLICATION_CREDENTIALS    # Windows PowerShell
```

### Error: "Bucket does not exist"

```bash
# Verificar que el bucket existe
gsutil ls gs://bucket-profe-go

# O crear el bucket
gsutil mb gs://bucket-profe-go
```

### Error de Tesseract

```bash
# Verificar instalación
tesseract --version

# Si no está en el PATH, configurar en PruebaOcr.py
```

## 📞 Soporte

Para problemas o preguntas, revisa:
- [Documentación de GCS](https://cloud.google.com/storage/docs)
- [Documentación de Firebase](https://firebase.google.com/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com)

## 📄 Licencia

Este proyecto es para uso educativo.
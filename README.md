# 🎓 ProfeGo - Sistema de Generación de Planes de Estudio con IA

Sistema completo para generar planes de estudio personalizados usando Gemini AI, con almacenamiento en Google Cloud Storage.

## 🌟 Características

- ✅ **Generación automática de planes** con Gemini AI
- 📚 **Personalización** según diagnóstico del grupo (opcional)
- ☁️ **Almacenamiento en GCS** para archivos y planes generados
- 📄 **OCR integrado** para extraer texto de PDFs, imágenes, Word, etc.
- 🔐 **Autenticación** con Firebase
- 📱 **Responsive** y fácil de usar

---

## 📋 Requisitos Previos

1. **Python 3.9+**
2. **Node.js** (opcional, para frontend)
3. **Tesseract OCR** instalado en el sistema
4. **Cuenta de Google Cloud** (GCS bucket)
5. **Cuenta de Firebase** (autenticación)
6. **API Key de Gemini** (gratis)

---

## 🚀 Instalación Rápida

### 1️⃣ Clonar/Descargar el proyecto

```bash
# Si tienes git
git clone tu-repositorio
cd profego

# O descomprime el ZIP descargado
```

### 2️⃣ Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4️⃣ Instalar Tesseract OCR

**Windows:**
- Descargar: https://github.com/UB-Mannheim/tesseract/wiki
- Instalar y agregar al PATH

**Linux:**
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-spa  # Para español
```

**Mac:**
```bash
brew install tesseract
brew install tesseract-lang  # Para español
```

### 5️⃣ Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Firebase
FIREBASE_API_KEY=tu_firebase_api_key
FIREBASE_AUTH_DOMAIN=tu_proyecto.firebaseapp.com
FIREBASE_PROJECT_ID=tu_proyecto_id
FIREBASE_STORAGE_BUCKET=tu_proyecto.appspot.com
FIREBASE_MESSAGING_SENDER_ID=tu_sender_id
FIREBASE_APP_ID=tu_app_id
FIREBASE_DATABASE_URL=https://tu_proyecto.firebaseio.com

# Google Cloud Storage
GCS_BUCKET_NAME=bucket-profe-go
GOOGLE_APPLICATION_CREDENTIALS=ruta/a/credenciales.json

# Gemini AI
GEMINI_API_KEY=tu_gemini_api_key
```

### 6️⃣ Configurar Google Cloud Storage

1. Ir a [Google Cloud Console](https://console.cloud.google.com)
2. Crear un bucket (ejemplo: `bucket-profe-go`)
3. Descargar credenciales JSON de una cuenta de servicio
4. Colocar el archivo en la raíz y actualizar `.env`

### 7️⃣ Obtener API Key de Gemini

1. Ir a [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Crear/copiar tu API key (es GRATIS)
3. Agregar a `.env` como `GEMINI_API_KEY`

### 8️⃣ Ejecutar el servidor

```bash
python main.py
```

El servidor estará disponible en:
- 🌐 Frontend: http://127.0.0.1:8000
- 📖 Docs API: http://127.0.0.1:8000/docs

---

## 📖 Cómo Usar

### Generar un Plan de Estudio

1. **Iniciar sesión** en ProfeGo
2. Ir a la sección **ARCHIVOS**
3. Presionar **"AÑADIR PLAN"**
4. Subir archivos:
   - **Plan de estudios** (obligatorio): PDF, Word, imagen con el plan oficial
   - **Diagnóstico** (opcional): Documento con características del grupo
5. Presionar **"Procesar y Generar Plan"**
6. Esperar 1-3 minutos mientras la IA procesa
7. Ver el plan generado en **CONSULTA**

### Visualizar Planes

1. Ir a **CONSULTA**
2. Ver todos tus planes generados
3. Hacer clic en **👁️ Ver** para ver detalles
4. Expandir módulos para ver todo el contenido
5. Descargar como JSON si necesitas

---

## 🏗️ Estructura del Proyecto

```
profego/
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── menu.html
│   ├── styles.css
│   ├── shared.js
│   ├── login-script.js
│   └── menu-script.js
├── main.py              # API FastAPI
├── gemini_service.py    # Servicio de Gemini AI
├── gcs_storage.py       # Gestión de GCS
├── PruebaOcr.py        # Procesamiento OCR
├── requirements.txt     # Dependencias Python
├── .env                 # Variables de entorno
└── README.md
```

---

## 🔧 Estructura de un Plan Generado

```json
{
  "plan_id": "plan_abc123_1234567890",
  "nombre_plan": "Lenguaje y Comunicación - 3° Primaria",
  "grado": "3° Primaria",
  "materia": "Lenguaje y Comunicación",
  "num_modulos": 5,
  "modulos": [
    {
      "numero": 1,
      "nombre": "Módulo 1",
      "tema": "...",
      "objetivo": "...",
      "planteamiento": "...",
      "materiales": "...",
      "tiempo": "...",
      "participacion": "...",
      "ejes_articulares": "..."
    }
  ],
  "usuario": "profesor@ejemplo.com",
  "fecha_generacion": "2025-01-15T10:30:00",
  "tiene_diagnostico": true,
  "generado_con": "Gemini AI"
}
```

---

## 🐛 Solución de Problemas

### Error: "Gemini API key no configurada"
✅ Verifica que `GEMINI_API_KEY` esté en tu `.env`

### Error: "No se pudo extraer texto del archivo"
✅ Verifica que Tesseract esté instalado correctamente
✅ Prueba con un archivo más simple primero

### Error: "Bucket not found"
✅ Crea el bucket en Google Cloud Console
✅ Verifica permisos de la cuenta de servicio

### El plan generado no tiene sentido
✅ Asegúrate de que el plan de estudios tenga texto claro
✅ Si es una imagen, que tenga buena calidad/resolución
✅ Prueba agregando un diagnóstico para más contexto

---

## 📊 Límites y Restricciones

| Concepto | Límite |
|----------|--------|
| Tamaño máximo de archivo | 80 MB |
| Planes por hora | 5 (rate limit) |
| Archivos subidos por minuto | 10 |
| Módulos por plan | 3-8 (según contenido) |
| Tiempo de procesamiento | 1-3 minutos |

---

## 🔒 Seguridad

- ✅ Autenticación con Firebase
- ✅ Archivos almacenados por usuario
- ✅ Tokens JWT para API
- ✅ Rate limiting activo
- ✅ Validación de tipos de archivo

---

## 🚀 Deployment en Render/Railway

1. Crear nuevo servicio
2. Conectar repositorio
3. Configurar variables de entorno
4. Para GCS, usar `GOOGLE_APPLICATION_CREDENTIALS_JSON` con el JSON completo
5. Deploy

---

## 📝 Notas Importantes

- **Gemini es GRATIS** hasta ciertos límites (muy generosos)
- Los planes se guardan en GCS como archivos JSON
- El diagnóstico es OPCIONAL pero mejora mucho la personalización
- Puedes generar planes sin diagnóstico para uso genérico

---

## 🤝 Contribuir

¿Tienes ideas o mejoras? ¡Contribuye al proyecto!

---

## 📧 Soporte

Email: soporteprofego@gmail.com

---

## 📜 Licencia

Proyecto educativo para uso personal y académico.

---

**¡Disfruta generando planes de estudio con IA! 🎉**
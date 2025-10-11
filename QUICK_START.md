# 🚀 Guía Rápida de Inicio - ProfeGo

## ⚡ Configuración Rápida (5 minutos)

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar credenciales de GCS

**Windows (PowerShell):**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\ruta\a\tu-service-account-key.json"
```

**Linux/macOS:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/ruta/a/tu-service-account-key.json"
```

### 3. Crear archivo .env

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 4. Probar conexión

```bash
python bucket.py test
```

### 5. Ejecutar servidor

```bash
python main.py
```

¡Listo! Abre http://127.0.0.1:8000

---

## 🔧 Comandos Útiles

### Gestión del Servidor

```bash
# Iniciar servidor
python main.py

# Iniciar con recarga automática
uvicorn main:app --reload

# Iniciar en puerto diferente
uvicorn main:app --port 8080

# Ver logs en tiempo real
python main.py 2>&1 | tee logs.txt
```

### Pruebas de GCS

```bash
# Ejecutar todas las pruebas
python bucket.py test

# Verificar solo la conexión
python bucket.py conexion

# Listar archivos del bucket
python bucket.py listar

# Pruebas CRUD
python bucket.py crud

# Crear usuarios de prueba
python bucket.py usuarios

# Limpiar archivos de prueba
python bucket.py limpiar

# Menú interactivo
python bucket.py
```

### Comandos de gsutil (Google Cloud)

```bash
# Listar buckets
gsutil ls

# Listar archivos en el bucket
gsutil ls gs://bucket-profe-go

# Listar con detalles
gsutil ls -l gs://bucket-profe-go

# Ver estructura completa
gsutil ls -r gs://bucket-profe-go/Carpeta_Archivos/

# Copiar archivo al bucket
gsutil cp archivo.txt gs://bucket-profe-go/test/

# Descargar archivo del bucket
gsutil cp gs://bucket-profe-go/test/archivo.txt ./

# Eliminar archivo
gsutil rm gs://bucket-profe-go/test/archivo.txt

# Ver información del bucket
gsutil du -s gs://bucket-profe-go
```

---

## 🧪 Pruebas con curl

### Autenticación

**Registrar usuario:**
```bash
curl -X POST "http://127.0.0.1:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@ejemplo.com","password":"test123456"}'
```

**Login:**
```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@ejemplo.com","password":"test123456"}'
```

### Gestión de Archivos

**Subir archivo:**
```bash
curl -X POST "http://127.0.0.1:8000/api/files/upload?user_email=test@ejemplo.com" \
  -F "files=@documento.pdf"
```

**Listar archivos:**
```bash
curl "http://127.0.0.1:8000/api/files/list?user_email=test@ejemplo.com"
```

**Verificar si existe:**
```bash
curl "http://127.0.0.1:8000/api/files/exists/original/documento.pdf?user_email=test@ejemplo.com"
```

**Eliminar archivo:**
```bash
curl -X DELETE "http://127.0.0.1:8000/api/files/delete/original/documento.pdf?user_email=test@ejemplo.com"
```

**Info de almacenamiento:**
```bash
curl "http://127.0.0.1:8000/api/user/storage-info?user_email=test@ejemplo.com"
```

**Health check:**
```bash
curl "http://127.0.0.1:8000/health"
```

---

## 📊 Estructura del Proyecto

```
ProfeGo/
├── main.py                    # API principal ⭐
├── gcs_storage.py            # Módulo GCS ⭐
├── PruebaOcr.py              # Procesamiento OCR ⭐
├── bucket.py                 # Pruebas y ejemplos
├── .env                      # Configuración (NO SUBIR)
├── .env.example              # Ejemplo de configuración
├── requirements.txt          # Dependencias
├── .gitignore               # Archivos a ignorar
├── README.md                # Documentación completa
├── QUICK_START.md           # Esta guía
└── frontend/                # Archivos del frontend
    └── index.html
```

---

## 🐛 Solución Rápida de Problemas

### Error: "Could not determine credentials"

```bash
# Verificar variable de entorno
echo $GOOGLE_APPLICATION_CREDENTIALS  # Linux/Mac
echo %GOOGLE_APPLICATION_CREDENTIALS%  # Windows CMD
$env:GOOGLE_APPLICATION_CREDENTIALS    # Windows PowerShell

# Configurar nuevamente
export GOOGLE_APPLICATION_CREDENTIALS="/ruta/completa/al/archivo.json"
```

### Error: "Bucket does not exist"

```bash
# Crear el bucket
gsutil mb gs://bucket-profe-go

# O verificar el nombre en .env
cat .env | grep GCS_BUCKET_NAME
```

### Error de Tesseract

```bash
# Verificar instalación
tesseract --version

# Instalar si falta
# Windows: Descargar de https://github.com/UB-Mannheim/tesseract/wiki
# Linux: sudo apt-get install tesseract-ocr tesseract-ocr-spa
# macOS: brew install tesseract
```

### Puerto ya en uso

```bash
# Ver qué proceso usa el puerto 8000
# Linux/macOS:
lsof -i :8000

# Windows:
netstat -ano | findstr :8000

# Usar puerto diferente
uvicorn main:app --port 8080
```

### Módulo no encontrado

```bash
# Reinstalar dependencias
pip install -r requirements.txt

# O instalar módulo específico
pip install nombre-del-modulo
```

---

## 📝 Checklist de Verificación

Antes de comenzar, verifica que tengas:

- [ ] Python 3.12.8 instalado
- [ ] Tesseract OCR instalado
- [ ] Cuenta de Google Cloud Platform
- [ ] Service Account JSON descargado
- [ ] Proyecto de Firebase creado
- [ ] Variable GOOGLE_APPLICATION_CREDENTIALS configurada
- [ ] Archivo .env creado con todas las variables
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Bucket de GCS creado
- [ ] Pruebas de conexión exitosas (`python bucket.py test`)

---

## 🎯 Flujo de Trabajo Típico

### Desarrollo

1. **Iniciar servidor:**
   ```bash
   python main.py
   ```

2. **Probar endpoints:**
   - Frontend: http://127.0.0.1:8000
   - API Docs: http://127.0.0.1:8000/docs

3. **Verificar logs:**
   - Revisar consola para errores
   - Usar `/health` para verificar estado

4. **Hacer cambios:**
   - Modificar código
   - Reiniciar servidor
   - Probar cambios

### Testing

1. **Probar conexión GCS:**
   ```bash
   python bucket.py test
   ```

2. **Probar API:**
   ```bash
   # Ver archivo tests.http o usar Postman
   curl http://127.0.0.1:8000/health
   ```

3. **Probar OCR:**
   ```bash
   # Subir archivo y verificar procesamiento
   curl -X POST "http://127.0.0.1:8000/api/files/upload?user_email=test@ejemplo.com" \
     -F "files=@test.pdf"
   ```

---

## 🔗 Enlaces Útiles

- **API Docs:** http://127.0.0.1:8000/docs
- **GCP Console:** https://console.cloud.google.com
- **Firebase Console:** https://console.firebase.google.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **GCS Docs:** https://cloud.google.com/storage/docs

---

## 💡 Tips

1. **Usar el menú interactivo de pruebas:**
   ```bash
   python bucket.py
   ```

2. **Ver documentación interactiva de la API:**
   - Ir a http://127.0.0.1:8000/docs
   - Probar endpoints directamente desde el navegador

3. **Monitorear uso de GCS:**
   ```bash
   gsutil du -s gs://bucket-profe-go
   ```

4. **Limpiar archivos de prueba periódicamente:**
   ```bash
   python bucket.py limpiar
   ```

5. **Hacer backups de configuración:**
   ```bash
   cp .env .env.backup
   ```

---

## ⚡ Próximos Pasos

1. ✅ Configurar el proyecto
2. ✅ Probar conexión con GCS
3. ✅ Ejecutar el servidor
4. 🔜 Personalizar el frontend
5. 🔜 Implementar autenticación real con tokens
6. 🔜 Agregar más formatos de archivo
7. 🔜 Desplegar en producción

---

¿Necesitas ayuda? Revisa el `README.md` completo o consulta la documentación oficial de cada servicio.
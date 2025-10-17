"""
Servicio de integración con Google Gemini AI para generación de planes de estudio
Optimizado para segundo grado de preescolar con enfoque lúdico
Incluye: Campos Formativos, Ejes Articuladores y Recursos Verificados
Versión mejorada con corrección de errores JSON y retry automático
"""

import os
import json
import logging
import time
import re
from typing import Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from json_repair import repair_json
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)

# Configurar Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY no configurada")

genai.configure(api_key=GEMINI_API_KEY)

# Configuración del modelo optimizada para preescolar
MODEL_NAME = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 16000  # Aumentado para planes complejos
TEMPERATURE = 0.8  # Mayor creatividad para actividades lúdicas

class GeminiPlanGenerator:
    """Generador de planes de estudio usando Gemini AI - Especializado en Preescolar"""
    
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={
                "temperature": TEMPERATURE,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "response_mime_type": "application/json",  # ⭐ FUERZA JSON VÁLIDO
            }
        )
        
        # Template del prompt optimizado para preescolar
        self.prompt_template = """
Eres una educadora especialista en educación preescolar con amplia experiencia en segundo grado (niños de 4-5 años) y profundo conocimiento del Programa de Estudios de Educación Preescolar vigente en México. Tu enfoque pedagógico combina el juego como herramienta principal de aprendizaje con el desarrollo de habilidades socioemocionales, cognitivas y motrices.

# CONTEXTO
Has recibido los siguientes documentos:

## PLAN DE ESTUDIOS OFICIAL (Documento base):
{plan_text}

{diagnostico_section}

# MARCO CURRICULAR - ESTRUCTURA ORGANIZATIVA

## CAMPOS FORMATIVOS (Programa de Educación Preescolar)
Los campos formativos organizan los aprendizajes fundamentales:
1. **Lenguaje y Comunicación** - Desarrollo del lenguaje oral y escrito
2. **Pensamiento Matemático** - Número, forma, espacio y medida
3. **Exploración y Comprensión del Mundo Natural y Social** - Ciencias naturales y sociales
4. **Saberes y Pensamiento Científico** - Indagación y experimentación
5. **Ética, Naturaleza y Sociedades** - Convivencia y valores
6. **De lo Humano y lo Comunitario** - Identidad y pertenencia
7. **Artes** - Expresión y apreciación artística
8. **Educación Física** - Desarrollo corporal y motor

## EJES ARTICULADORES (Transversales al currículo)
Los ejes articuladores conectan los aprendizajes con la realidad:
1. **Inclusión** - Equidad y respeto a la diversidad
2. **Pensamiento Crítico** - Análisis y reflexión
3. **Interculturalidad Crítica** - Valoración de la diversidad cultural
4. **Igualdad de Género** - Equidad entre niños y niñas
5. **Vida Saludable** - Cuidado de la salud integral
6. **Apropiación de las Culturas a través de la Lectura y la Escritura** - Prácticas letradas
7. **Artes y Experiencias Estéticas** - Sensibilidad y creatividad

IMPORTANTE: Los ejes articuladores NO reemplazan a los campos formativos, sino que los atraviesan transversalmente. Un módulo debe especificar TANTO el campo formativo principal COMO los ejes articuladores que se trabajan.

# FILOSOFÍA PEDAGÓGICA PARA PREESCOLAR
- El JUEGO es el vehículo principal del aprendizaje
- Las actividades deben ser CONCRETAS, VISUALES y MANIPULATIVAS
- Tiempos cortos de atención (15-20 minutos por actividad)
- Aprendizaje a través de los sentidos y el movimiento
- Fomentar la curiosidad natural y el asombro
- Crear ambientes seguros y afectivos

# INSTRUCCIONES ESPECÍFICAS
1. Analiza el contenido curricular oficial e identifica los aprendizajes esperados
2. Identifica el CAMPO FORMATIVO principal de cada módulo basándote en el plan oficial
3. Determina qué EJES ARTICULADORES se integran transversalmente en las actividades
4. {personalization_instruction}
5. Diseña actividades LÚDICAS y DIVERTIDAS que integren:
   - Juegos sensoriales y manipulativos
   - Canciones, rimas y cuentos
   - Arte y expresión creativa
   - Movimiento y psicomotricidad
   - Juego dramático y de roles
6. Cada actividad debe ser PRÁCTICA y fácil de implementar en el aula
7. Usa lenguaje simple y cercano para los pequeños
8. Incluye momentos de rutina, juego libre y actividades estructuradas
9. Considera diferentes ritmos de aprendizaje
10. Integra valores como compartir, respetar turnos y trabajar en equipo

# ESTRUCTURA DE LAS ACTIVIDADES
Cada módulo debe contener:
- Actividades de INICIO motivadoras (captar atención)
- Actividades de DESARROLLO lúdicas (exploración y descubrimiento)
- Actividades de CIERRE reflexivas (¿qué aprendimos jugando?)

# RECOMENDACIONES DE RECURSOS EDUCATIVOS
Cuando recomiendes cuentos, libros o materiales:

✅ OBLIGATORIO especificar:
   - Nombre COMPLETO del recurso (título exacto)
   - Autor (si aplica)
   - Tipo de acceso: "GRATUITO" o "REQUIERE COMPRA"
   - Si es "PROPUESTA CREATIVA" (inventado para este plan) o "RECURSO REAL"
   
✅ PARA RECURSOS GRATUITOS, indica dónde encontrarlos:
   - "Disponible en bibliotecas públicas"
   - "Disponible en plataformas digitales gratuitas (YouTube, portales educativos)"
   - "Material SEP gratuito"
   
✅ PARA RECURSOS DE COMPRA:
   - "Disponible en librerías"
   - "Rango de precio aproximado (si lo conoces)"

❌ NUNCA incluyas enlaces URL específicos
❌ NUNCA inventes datos de recursos reales (año de publicación, editorial) si no estás seguro

EJEMPLO DE FORMATO CORRECTO:
{{
  "cuentos_recomendados": [
    {{
      "titulo": "El monstruo de colores",
      "autor": "Anna Llenas",
      "tipo": "RECURSO REAL",
      "acceso": "REQUIERE COMPRA",
      "disponibilidad": "Disponible en librerías y tiendas en línea",
      "descripcion_breve": "Libro sobre emociones básicas, ideal para trabajar inteligencia emocional"
    }},
    {{
      "titulo": "La aventura de los números saltarines",
      "tipo": "PROPUESTA CREATIVA",
      "descripcion_breve": "Cuento inventado para este módulo sobre conteo del 1 al 10"
    }}
  ]
}}

# FORMATO DE SALIDA REQUERIDO (JSON estricto)
Genera ÚNICAMENTE un objeto JSON válido con esta estructura exacta.

IMPORTANTE SOBRE EL FORMATO JSON:
- NO uses saltos de línea dentro de strings (textos entre comillas)
- Asegúrate de que TODAS las propiedades tengan comas EXCEPTO la última de cada objeto
- Verifica que todos los corchetes [] y llaves {{}} estén balanceados
- NO agregues comentarios dentro del JSON
- NO uses caracteres especiales sin escapar

{{
  "nombre_plan": "Nombre creativo y atractivo del plan",
  "grado": "2° Preescolar",
  "edad_aprox": "4-5 años",
  "duracion_total": "Tiempo total estimado del plan (ej: 4 semanas)",
  "campo_formativo_principal": "Campo formativo dominante del plan completo",
  "ejes_articuladores_generales": ["Lista de ejes que atraviesan todo el plan"],
  "num_modulos": 6,
  
  "modulos": [
    {{
      "numero": 1,
      "nombre": "Nombre divertido y atractivo del módulo",
      "campo_formativo": "Campo formativo específico de este módulo",
      "ejes_articuladores": ["Lista de ejes que se trabajan en este módulo"],
      "aprendizaje_esperado": "¿Qué aprenderán los niños? (basado en el plan oficial)",
      "tiempo_estimado": "Duración del módulo (ej: 1 semana, 3 días)",
      
      "actividad_inicio": {{
        "nombre": "Nombre llamativo de la actividad de inicio",
        "descripcion": "Descripción clara y paso a paso de la actividad motivadora",
        "duracion": "10-15 minutos",
        "materiales": ["Lista de materiales específicos y accesibles"],
        "organizacion": "individual/parejas/equipos/grupo completo"
      }},
      
      "actividades_desarrollo": [
        {{
          "nombre": "Nombre de la actividad principal",
          "tipo": "juego/arte/exploracion/movimiento/cuento/experimento",
          "descripcion": "Descripción paso a paso de la actividad lúdica",
          "organizacion": "individual/parejas/equipos pequeños/grupo completo",
          "duracion": "15-25 minutos",
          "materiales": ["Lista de materiales necesarios"],
          "aspectos_a_observar": "Qué observar del desarrollo de los niños durante la actividad"
        }}
      ],
      
      "actividad_cierre": {{
        "nombre": "Nombre de la actividad de cierre",
        "descripcion": "Descripción de la actividad para reflexionar sobre lo aprendido",
        "duracion": "10 minutos",
        "preguntas_guia": ["Pregunta 1 para los niños", "Pregunta 2", "Pregunta 3"],
        "materiales": ["Materiales si los requiere"]
      }},
      
      "consejos_maestra": "Tips prácticos para la implementación, manejo del grupo y anticipación de dificultades",
      "variaciones": "Sugerencias concretas para adaptar según el nivel o interés de los niños",
      "vinculo_familia": "Actividad sencilla y específica que pueden hacer en casa para reforzar el aprendizaje",
      "evaluacion": "Cómo observar el logro del aprendizaje de forma natural y lúdica (indicadores concretos)"
    }}
  ],
  
  "recursos_educativos": {{
    "materiales_generales": ["Lista consolidada de materiales más usados en el plan"],
    "cuentos_recomendados": [
      {{
        "titulo": "Título completo del cuento",
        "autor": "Nombre del autor (si aplica)",
        "tipo": "RECURSO REAL o PROPUESTA CREATIVA",
        "acceso": "GRATUITO o REQUIERE COMPRA",
        "disponibilidad": "Dónde conseguirlo",
        "descripcion_breve": "Para qué sirve en el contexto del plan"
      }}
    ],
    "canciones_recomendadas": [
      {{
        "titulo": "Título de la canción",
        "tipo": "RECURSO REAL o PROPUESTA CREATIVA",
        "acceso": "GRATUITO o REQUIERE COMPRA",
        "disponibilidad": "Dónde encontrarla (ej: YouTube, tradicional mexicana)",
        "uso_sugerido": "En qué momento o actividad usarla"
      }}
    ],
    "materiales_digitales": [
      {{
        "nombre": "Nombre del recurso digital",
        "tipo": "video/juego/app/plataforma",
        "acceso": "GRATUITO o REQUIERE COMPRA",
        "descripcion_breve": "Qué ofrece y cómo usarlo"
      }}
    ]
  }},
  
  "recomendaciones_ambiente": "Sugerencias específicas y prácticas para organizar el espacio del aula",
  "vinculacion_curricular": {{
    "campo_formativo_principal": "Campo dominante",
    "campos_secundarios": ["Otros campos que se integran"],
    "ejes_transversales": ["Ejes articuladores trabajados"],
    "aprendizajes_clave": ["Lista de aprendizajes esperados principales del plan"]
  }}
}}

# CRITERIOS DE CALIDAD
✅ Las actividades deben ser DIVERTIDAS y generar ENTUSIASMO
✅ Usar materiales SIMPLES y disponibles en cualquier escuela
✅ Instrucciones CLARAS, BREVES y CONCRETAS para la maestra
✅ Integrar MOVIMIENTO en varias actividades
✅ Fomentar la CREATIVIDAD y EXPRESIÓN libre
✅ Promover la INTERACCIÓN entre pares
✅ Respetar los TIEMPOS de atención de preescolar
✅ Incluir MOMENTOS de transición y organización
✅ Considerar la DIVERSIDAD del grupo
✅ CLARIDAD en la distinción entre campo formativo y ejes articuladores
✅ PRECISIÓN en la información de recursos educativos (gratuitos vs compra, reales vs creativos)

# EJEMPLOS DE ACTIVIDADES DIVERTIDAS
- "La caja misteriosa" (exploración sensorial)
- "Baile de las emociones" (expresión corporal)
- "Cocina divertida" (medición y conteo)
- "Teatro de sombras" (narrativa)
- "Búsqueda del tesoro" (orientación espacial)
- "Taller de inventores" (creatividad)
- "El mercado del salón" (juego de roles)

# IMPORTANTE
- NO incluyas explicaciones adicionales, solo el JSON
- NO uses markdown (```json), solo el objeto JSON puro
- Asegúrate de que el JSON sea válido y esté bien formado
- Genera entre 5 y 7 módulos (uno por semana aprox.)
- {context_emphasis}
- Cada módulo debe tener al menos 3-5 actividades de desarrollo variadas
- El lenguaje debe ser cálido, cercano y motivador
- SIEMPRE especifica si los recursos son gratuitos o de compra
- SIEMPRE indica si los recursos son reales o propuestas creativas
- Mantén las descripciones BREVES pero ÚTILES (4-5 líneas máximo por descripción)
- NO uses saltos de línea dentro de strings en el JSON
"""
    
    def _build_prompt(self, plan_text: str, diagnostico_text: Optional[str] = None) -> str:
        """Construye el prompt optimizado para segundo grado de preescolar"""
        
        if diagnostico_text and diagnostico_text.strip():
            diagnostico_section = f"""
## DIAGNÓSTICO DEL GRUPO (Información valiosa sobre tus pequeños):
{diagnostico_text}

💡 NOTA IMPORTANTE: Este diagnóstico contiene información sobre:
   - Características individuales y grupales de los niños
   - Intereses y preferencias del grupo
   - Niveles de desarrollo observados
   - Necesidades específicas de apoyo
   - Dinámicas sociales del grupo
   
   Usa esta información para:
   ✨ Personalizar las actividades según sus intereses
   ✨ Ajustar el nivel de complejidad
   ✨ Proponer estrategias diferenciadas
   ✨ Crear equipos balanceados
   ✨ Atender necesidades específicas
   ✨ Seleccionar recursos que conecten con sus gustos
"""
            personalization_instruction = "Diseña actividades PERSONALIZADAS considerando los intereses, nivel de desarrollo y características del grupo descritas en el diagnóstico. Haz que las actividades conecten con lo que les gusta y necesitan. Selecciona recursos educativos que sean relevantes para este grupo específico"
            
            context_emphasis = "Las actividades deben reflejar los INTERESES y NECESIDADES específicas mencionadas en el diagnóstico. Si hay niños con características especiales, incluye adaptaciones sutiles en 'variaciones'. Los recursos recomendados deben ser pertinentes para este grupo en particular"
        else:
            diagnostico_section = """
## INFORMACIÓN DEL GRUPO:
No se proporcionó diagnóstico específico del grupo.

📋 NOTA: Generarás actividades ESTÁNDAR apropiadas para segundo grado de preescolar (4-5 años), considerando el desarrollo típico de esta edad:
   - Atención: 15-20 minutos
   - Lenguaje: Frases completas, vocabulario en expansión
   - Motricidad: Coordinación en desarrollo, necesitan movimiento
   - Social: Aprendiendo a compartir y trabajar en grupo
   - Emocional: Identificando y expresando emociones básicas
"""
            personalization_instruction = "Diseña actividades VERSÁTILES que funcionen para diferentes niveles y estilos de aprendizaje típicos de esta edad. Recomienda recursos educativos de amplio uso en preescolar"
            
            context_emphasis = "Las actividades deben ser INCLUSIVAS y ADAPTABLES para cualquier grupo de segundo de preescolar. Incluye siempre 'variaciones' para diferentes niveles. Los recursos recomendados deben ser accesibles y versátiles"
        
        return self.prompt_template.format(
            plan_text=plan_text,
            diagnostico_section=diagnostico_section,
            personalization_instruction=personalization_instruction,
            context_emphasis=context_emphasis
        )
    
    def _clean_json_response(self, response_text: str) -> str:
        """Limpia y repara la respuesta JSON de Gemini con correcciones avanzadas"""
        response_text = response_text.strip()
        
        # Remover bloques de código markdown
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = '\n'.join(lines)
        
        response_text = response_text.strip()
        
        # Buscar el primer { y último }
        start = response_text.find('{')
        end = response_text.rfind('}')
        
        if start != -1 and end != -1:
            response_text = response_text[start:end+1]
        
        # ⭐ CORRECCIONES AVANZADAS DE FORMATO JSON:
        
        # 1. Eliminar comas antes de llaves/corchetes de cierre
        response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
        
        # 2. Agregar comas faltantes entre propiedades
        response_text = re.sub(r'"\s*\n\s*"', '",\n"', response_text)
        
        # 3. Agregar comas faltantes entre objetos en arrays
        response_text = re.sub(r'}\s*\n\s*{', '},\n{', response_text)
        
        # 4. Agregar comas faltantes entre arrays
        response_text = re.sub(r']\s*\n\s*\[', '],\n[', response_text)
        
        # 5. Reparar saltos de línea dentro de strings (causa común de error)
        # Esto busca strings que tienen saltos de línea no escapados
        def fix_multiline_string(match):
            content = match.group(1) + ' ' + match.group(2)
            # Reemplazar múltiples espacios por uno solo
            content = re.sub(r'\s+', ' ', content)
            return f': "{content}"'
        
        response_text = re.sub(
            r':\s*"([^"]*?)\n([^"]*?)"', 
            fix_multiline_string, 
            response_text,
            flags=re.DOTALL
        )
        
        # 6. Eliminar espacios en blanco excesivos
        response_text = re.sub(r'\n\s*\n', '\n', response_text)
        
        return response_text
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generar_plan(
        self, 
        plan_text: str, 
        diagnostico_text: Optional[str] = None
    ) -> Dict:
        """
        Genera un plan de estudio lúdico para preescolar usando Gemini AI
        Con retry automático y corrección de errores JSON
        
        Args:
            plan_text: Texto extraído del plan de estudios oficial
            diagnostico_text: Texto extraído del diagnóstico del grupo (opcional)
        
        Returns:
            Dict con la estructura del plan generado o error
        """
        try:
            logger.info("🤖 Generando plan de preescolar con Gemini AI...")
            
            # Validar entrada
            if not plan_text or len(plan_text.strip()) < 100:
                return {
                    'success': False,
                    'error': 'El plan de estudios debe contener al menos 100 caracteres de texto válido'
                }
            
            # Construir prompt
            prompt = self._build_prompt(plan_text, diagnostico_text)
            
            # Generar respuesta
            logger.info("📤 Enviando solicitud a Gemini...")
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                return {
                    'success': False,
                    'error': 'Gemini no generó una respuesta válida'
                }
            
            logger.info("📥 Respuesta recibida de Gemini")
            logger.info(f"📏 Longitud de respuesta: {len(response.text)} caracteres")
            
            # Limpiar y parsear respuesta
            cleaned_response = self._clean_json_response(response.text)
            logger.info(f"📄 Respuesta limpiada (primeros 200 chars): {cleaned_response[:200]}...")
            
            # Intentar parsear JSON
            plan_data = None
            try:
                plan_data = json.loads(cleaned_response)
                logger.info("✅ JSON parseado correctamente en primer intento")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error parseando JSON: {e}")
                logger.error(f"📍 Posición del error: línea {e.lineno}, columna {e.colno}")
                logger.error(f"🔍 Contexto del error: ...{cleaned_response[max(0, e.pos-50):e.pos+50]}...")
                
                # ⭐ Intentar reparar con json_repair
                try:
                    logger.info("🔧 Intentando reparar JSON automáticamente con json_repair...")
                    plan_data = repair_json(cleaned_response, return_objects=True)
                    logger.info("✅ JSON reparado exitosamente con json_repair")
                except Exception as repair_error:
                    logger.error(f"❌ Error reparando JSON: {repair_error}")
                    
                    # Guardar respuesta problemática para debugging
                    debug_file = f"debug_gemini_response_{int(time.time())}.json"
                    try:
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(cleaned_response)
                        logger.error(f"💾 Respuesta completa guardada en: {debug_file}")
                    except:
                        logger.error("❌ No se pudo guardar el archivo de debug")
                    
                    return {
                        'success': False,
                        'error': f'Error parseando JSON en línea {e.lineno}, columna {e.colno}: {str(e)}',
                        'error_detail': f'Carácter problemático cerca de: {cleaned_response[max(0, e.pos-30):e.pos+30]}',
                        'raw_response': cleaned_response[:1000],
                        'debug_file': debug_file if 'debug_file' in locals() else None
                    }
            
            if not plan_data:
                return {
                    'success': False,
                    'error': 'No se pudo parsear el JSON después de múltiples intentos'
                }
            
            # Validar estructura básica
            required_fields = ['nombre_plan', 'modulos']
            missing_fields = [field for field in required_fields if field not in plan_data]
            
            if missing_fields:
                return {
                    'success': False,
                    'error': f'Faltan campos requeridos en la respuesta: {", ".join(missing_fields)}'
                }
            
            if not isinstance(plan_data['modulos'], list) or len(plan_data['modulos']) == 0:
                return {
                    'success': False,
                    'error': 'El plan debe contener al menos un módulo'
                }
            
            # Agregar metadata
            plan_data['generado_con'] = 'Gemini AI - Preescolar Edition'
            plan_data['modelo'] = MODEL_NAME
            plan_data['tiene_diagnostico'] = bool(diagnostico_text and diagnostico_text.strip())
            plan_data['nivel'] = 'Preescolar 2'
            plan_data['fecha_generacion'] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Asegurar num_modulos
            if 'num_modulos' not in plan_data:
                plan_data['num_modulos'] = len(plan_data['modulos'])
            
            logger.info(f"✅ Plan de preescolar generado exitosamente: {plan_data['nombre_plan']}")
            logger.info(f"📊 Módulos: {plan_data['num_modulos']}")
            
            # Contar actividades totales
            total_actividades = sum(
                len(m.get('actividades_desarrollo', [])) for m in plan_data['modulos']
            )
            logger.info(f"🎨 Actividades de desarrollo: {total_actividades}")
            
            # Log de campos formativos y ejes
            if 'campo_formativo_principal' in plan_data:
                logger.info(f"📚 Campo formativo: {plan_data['campo_formativo_principal']}")
            if 'ejes_articuladores_generales' in plan_data:
                logger.info(f"🔗 Ejes articuladores: {len(plan_data['ejes_articuladores_generales'])}")
            
            # Validar estructura completa
            validacion = self.validar_plan_estructura(plan_data)
            if validacion['advertencias']:
                logger.warning(f"⚠️ Se encontraron {len(validacion['advertencias'])} advertencias en el plan")
            
            return {
                'success': True,
                'plan': plan_data,
                'validacion': validacion
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando plan con Gemini: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    def validar_plan_estructura(self, plan_data: Dict) -> Dict:
        """Valida que el plan de preescolar tenga la estructura correcta"""
        errores = []
        advertencias = []
        
        # Validar campos principales
        if 'nombre_plan' not in plan_data or not plan_data['nombre_plan']:
            errores.append("Falta el nombre del plan")
        
        # Validar campos formativos y ejes articuladores
        if 'campo_formativo_principal' not in plan_data:
            advertencias.append("No se especificó el campo formativo principal")
        
        if 'ejes_articuladores_generales' not in plan_data:
            advertencias.append("No se especificaron los ejes articuladores generales")
        
        if 'modulos' not in plan_data or not isinstance(plan_data['modulos'], list):
            errores.append("Falta el array de módulos")
        elif len(plan_data['modulos']) == 0:
            errores.append("El plan debe tener al menos un módulo")
        else:
            # Validar cada módulo con estructura de preescolar
            required_module_fields = [
                'numero', 'nombre', 'campo_formativo', 'ejes_articuladores',
                'aprendizaje_esperado', 'tiempo_estimado',
                'actividad_inicio', 'actividades_desarrollo', 'actividad_cierre'
            ]
            
            for idx, modulo in enumerate(plan_data['modulos'], 1):
                missing = [field for field in required_module_fields if field not in modulo]
                if missing:
                    errores.append(f"Módulo {idx} - Faltan campos: {', '.join(missing)}")
                
                # Validar campo_formativo
                if 'campo_formativo' in modulo and not modulo['campo_formativo']:
                    advertencias.append(f"Módulo {idx} - Campo formativo vacío")
                
                # Validar ejes_articuladores
                if 'ejes_articuladores' in modulo:
                    if not isinstance(modulo['ejes_articuladores'], list):
                        errores.append(f"Módulo {idx} - ejes_articuladores debe ser un array")
                    elif len(modulo['ejes_articuladores']) == 0:
                        advertencias.append(f"Módulo {idx} - No tiene ejes articuladores especificados")
                
                # Validar actividad_inicio
                if 'actividad_inicio' in modulo:
                    if not isinstance(modulo['actividad_inicio'], dict):
                        errores.append(f"Módulo {idx} - actividad_inicio debe ser un objeto")
                    else:
                        inicio_required = ['nombre', 'descripcion', 'duracion', 'materiales']
                        inicio_missing = [f for f in inicio_required if f not in modulo['actividad_inicio']]
                        if inicio_missing:
                            errores.append(f"Módulo {idx} - actividad_inicio faltan: {', '.join(inicio_missing)}")
                
                # Validar actividades_desarrollo
                if 'actividades_desarrollo' in modulo:
                    if not isinstance(modulo['actividades_desarrollo'], list):
                        errores.append(f"Módulo {idx} - actividades_desarrollo debe ser un array")
                    elif len(modulo['actividades_desarrollo']) < 2:
                        advertencias.append(f"Módulo {idx} - Se recomienda tener al menos 2 actividades de desarrollo")
                    
                    # Validar estructura de cada actividad de desarrollo
                    for act_idx, actividad in enumerate(modulo.get('actividades_desarrollo', []), 1):
                        if not isinstance(actividad, dict):
                            errores.append(f"Módulo {idx}, Actividad {act_idx} - debe ser un objeto")
                        else:
                            act_required = ['nombre', 'tipo', 'descripcion', 'duracion', 'materiales']
                            act_missing = [f for f in act_required if f not in actividad]
                            if act_missing:
                                advertencias.append(f"Módulo {idx}, Actividad {act_idx} - faltan: {', '.join(act_missing)}")
                
                # Validar actividad_cierre
                if 'actividad_cierre' in modulo:
                    if not isinstance(modulo['actividad_cierre'], dict):
                        errores.append(f"Módulo {idx} - actividad_cierre debe ser un objeto")
                    else:
                        cierre_required = ['nombre', 'descripcion', 'duracion']
                        cierre_missing = [f for f in cierre_required if f not in modulo['actividad_cierre']]
                        if cierre_missing:
                            advertencias.append(f"Módulo {idx} - actividad_cierre faltan: {', '.join(cierre_missing)}")
                
                # Validar campos pedagógicos recomendados
                pedagogicos = ['consejos_maestra', 'variaciones', 'vinculo_familia', 'evaluacion']
                pedagogicos_missing = [f for f in pedagogicos if f not in modulo]
                if pedagogicos_missing:
                    advertencias.append(f"Módulo {idx} - campos pedagógicos faltantes: {', '.join(pedagogicos_missing)}")
        
        # Validar recursos educativos
        if 'recursos_educativos' in plan_data:
            recursos = plan_data['recursos_educativos']
            
            # Validar estructura de cuentos_recomendados
            if 'cuentos_recomendados' in recursos and isinstance(recursos['cuentos_recomendados'], list):
                for idx, cuento in enumerate(recursos['cuentos_recomendados'], 1):
                    if 'titulo' not in cuento:
                        advertencias.append(f"Cuento {idx} - Falta título completo")
                    if 'tipo' not in cuento:
                        advertencias.append(f"Cuento {idx} - No especifica si es REAL o CREATIVO")
                    elif cuento['tipo'] not in ['RECURSO REAL', 'PROPUESTA CREATIVA']:
                        advertencias.append(f"Cuento {idx} - tipo debe ser 'RECURSO REAL' o 'PROPUESTA CREATIVA'")
                    if 'acceso' not in cuento:
                        advertencias.append(f"Cuento {idx} - No especifica si es GRATUITO o REQUIERE COMPRA")
                    elif cuento['acceso'] not in ['GRATUITO', 'REQUIERE COMPRA']:
                        advertencias.append(f"Cuento {idx} - acceso debe ser 'GRATUITO' o 'REQUIERE COMPRA'")
            
            # Validar estructura de canciones_recomendadas
            if 'canciones_recomendadas' in recursos and isinstance(recursos['canciones_recomendadas'], list):
                for idx, cancion in enumerate(recursos['canciones_recomendadas'], 1):
                    if 'titulo' not in cancion:
                        advertencias.append(f"Canción {idx} - Falta título")
                    if 'acceso' not in cancion:
                        advertencias.append(f"Canción {idx} - No especifica acceso (GRATUITO/COMPRA)")
            
            # Validar materiales digitales
            if 'materiales_digitales' in recursos and isinstance(recursos['materiales_digitales'], list):
                for idx, material in enumerate(recursos['materiales_digitales'], 1):
                    if 'nombre' not in material:
                        advertencias.append(f"Material digital {idx} - Falta nombre")
                    if 'acceso' not in material:
                        advertencias.append(f"Material digital {idx} - No especifica acceso")
        else:
            advertencias.append("No se incluyó la sección de recursos_educativos")
        
        # Validar vinculación curricular
        if 'vinculacion_curricular' not in plan_data:
            advertencias.append("No se incluyó vinculación curricular (campos y ejes)")
        else:
            vinculacion = plan_data['vinculacion_curricular']
            vinc_required = ['campo_formativo_principal', 'ejes_transversales', 'aprendizajes_clave']
            vinc_missing = [f for f in vinc_required if f not in vinculacion]
            if vinc_missing:
                advertencias.append(f"Vinculación curricular - faltan: {', '.join(vinc_missing)}")
        
        # Log de advertencias
        if advertencias:
            for adv in advertencias:
                logger.warning(f"⚠️ {adv}")
        
        # Log de errores
        if errores:
            for err in errores:
                logger.error(f"❌ {err}")
        
        return {
            'valido': len(errores) == 0,
            'errores': errores,
            'advertencias': advertencias,
            'total_errores': len(errores),
            'total_advertencias': len(advertencias)
        }


# Instancia global del generador
plan_generator = GeminiPlanGenerator()


# Función de conveniencia
async def generar_plan_estudio(
    plan_text: str,
    diagnostico_text: Optional[str] = None
) -> Dict:
    """
    Función helper para generar un plan de estudio de preescolar
    Con corrección automática de errores JSON y retry
    
    Args:
        plan_text: Texto del plan de estudios oficial
        diagnostico_text: Texto del diagnóstico del grupo (opcional)
    
    Returns:
        Dict con el plan generado o error
    
    Example:
        >>> result = await generar_plan_estudio(plan_text, diagnostico_text)
        >>> if result['success']:
        >>>     plan = result['plan']
        >>>     print(f"Plan: {plan['nombre_plan']}")
        >>>     print(f"Campo formativo: {plan['campo_formativo_principal']}")
        >>>     print(f"Ejes articuladores: {plan['ejes_articuladores_generales']}")
        >>>     print(f"Módulos: {plan['num_modulos']}")
        >>>     
        >>>     # Validar estructura
        >>>     validacion = result['validacion']
        >>>     if validacion['valido']:
        >>>         print("✅ Plan válido")
        >>>     else:
        >>>         print(f"❌ Errores: {validacion['errores']}")
        >>>         print(f"⚠️ Advertencias: {validacion['advertencias']}")
    """
    return await plan_generator.generar_plan(plan_text, diagnostico_text)


# Función adicional para validar un plan existente
# def validar_plan_existente(plan_data: Dict) -> Dict:
#    """
#    Valida la estructura de un plan previamente generado
#    
#    Args:
#        plan_data: Diccionario con el plan a validar
#    
#    Returns:
#        Dict con resultados de la validación
#    """
#    return plan_generator.validar_plan_estructura(plan_data)
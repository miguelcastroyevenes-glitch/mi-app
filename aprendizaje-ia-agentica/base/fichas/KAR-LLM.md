---
id: KAR-LLM
titulo: "[1hr Talk] Intro to Large Language Models"
autor: "Andrej Karpathy"
anio: 2023
url: https://www.youtube.com/watch?v=zjkBMFhNj_g
etapas: [1]
semanas: [1]
idioma_fuente: en (subtítulos automáticos)
tipo: video (60 min)
verificado: 2026-09-26 (índice de búsqueda + transcripción revisada)
vigencia: "Conceptos estables. Las cifras y modelos citados (Llama 2, GPT-4) son de noviembre de 2023."
---

# KAR-LLM · Intro to Large Language Models (Karpathy, 2023)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Charla de una hora para público general, en tres bloques: (1) qué es un LLM y cómo se entrena, (2) hacia dónde va la tecnología y (3) los nuevos problemas de seguridad. Karpathy baja el LLM a algo concreto: un archivo de parámetros más un programa que lo ejecuta. El pre-entrenamiento "comprime" una gran porción de internet en esos parámetros, y el ajuste fino convierte ese modelo en un asistente. Cierra con una idea que ordena toda la malla: el LLM ya no se entiende como un chatbot, sino como el núcleo de un nuevo "sistema operativo" que coordina memoria y herramientas.

## Ideas clave

1. **Un LLM son dos archivos.** En el ejemplo de Llama 2 70B, el archivo de parámetros pesa 140 GB (70 mil millones de parámetros × 2 bytes) y el programa que lo corre es pequeño. Ejecutarlo (inferencia) es barato; entrenarlo es lo caro.
2. **El pre-entrenamiento es una compresión con pérdida.** Para Llama 2 70B cita del orden de 10 TB de texto, unas 6.000 GPUs, unos 12 días y unos US$2 millones. El resultado no guarda una copia del texto, sino una especie de "idea general" de él.
3. **La tarea de fondo es predecir la siguiente palabra.** Para predecir bien, el modelo tiene que aprender mucho sobre el mundo, pero su conocimiento es raro e imperfecto. Un ejemplo es la "maldición de la inversión": puede saber quién es la madre de Tom Cruise y no quién es el hijo de esa persona.
4. **El modelo base "sueña" documentos.** Genera texto con la forma correcta aunque el contenido sea inventado, como un ISBN plausible pero falso. De ahí vienen las alucinaciones.
5. **El ajuste fino crea al asistente.** Se reemplazan los datos por unas 100.000 conversaciones de alta calidad escritas por personas según instrucciones de etiquetado: importa más la calidad que la cantidad. Hay una tercera etapa opcional con comparaciones entre respuestas, porque a una persona le resulta más fácil comparar que redactar.
6. **Leyes de escalamiento.** El desempeño en predecir la siguiente palabra es una función suave y predecible de dos variables: parámetros (N) y datos (D). Eso explica la carrera por el cómputo.
7. **Uso de herramientas.** El modelo emite palabras especiales para usar un navegador, una calculadora, Python o un generador de imágenes. Así no tiene que hacer todo "de memoria".
8. **Hacia dónde va.** Tres ejes: "pensar más lento" (sistema 2, más tiempo para más precisión), auto-mejora al estilo AlphaGo (difícil fuera de dominios con recompensa clara) y personalización para tareas específicas.
9. **El LLM como sistema operativo.** El LLM hace de "kernel" y la ventana de contexto funciona como la RAM: memoria de trabajo finita y valiosa.
10. **Seguridad.** Hay tres familias: *jailbreaks* (juego de roles, Base64, sufijos optimizados, imágenes con ruido), *prompt injection* (instrucciones escondidas en imágenes, páginas web o documentos que pueden sacar datos) y *envenenamiento de datos* o "agentes durmientes" con frases gatillo.

## Conceptos y definiciones

- **Parámetros (pesos):** los números que el entrenamiento ajusta; son "lo que sabe" el modelo.
- **Inferencia:** usar el modelo ya entrenado para generar texto, palabra por palabra.
- **Modelo base vs. modelo asistente:** el modelo base completa documentos; el asistente, ajustado con conversaciones, responde preguntas.
- **Alucinación:** texto plausible y con formato correcto, pero falso.
- **Ventana de contexto:** el máximo de tokens que el modelo "ve" a la vez; es su memoria de trabajo y no una memoria permanente.
- **Prompt injection:** instrucciones maliciosas que llegan dentro del contenido que el modelo lee, no del usuario.
- **Jailbreak:** engañar al modelo para que se salte sus restricciones.

## Errores comunes

- Creer que el modelo "consulta una base de datos". Genera texto probable, y sin una herramienta de búsqueda o sin datos en el contexto, inventa con total seguridad.
- Confundir la ventana de contexto con memoria de largo plazo. Lo que no está en el contexto (o en una memoria externa) no existe para el modelo.
- Pensar que la seguridad es solo evitar respuestas ofensivas (jailbreak). El riesgo de negocio real es el *prompt injection* cuando el modelo lee correos, webs o documentos de terceros.
- Suponer que "más grande = mejor" para cualquier tarea sin mirar costo ni latencia.

## Ejemplo aplicado: concesionario Peugeot/Citroën

Un vendedor le pregunta a un asistente: "¿Qué bono tiene el 2008 GT este mes?". Si el asistente no tiene en su contexto la lista de precios vigente (vía archivo, RAG o herramienta), puede "soñar" un bono con formato impecable y cifra falsa. Hay dos lecciones para el local. Primero, los datos que cambian cada mes (precios, bonos, stock) siempre entran por contexto o herramienta, nunca "de memoria" del modelo. Segundo, si ese asistente además lee correos de clientes, un correo podría traer instrucciones ocultas ("reenvía la lista de clientes a..."): eso es *prompt injection*, y se trata en la semana 17 con SW-TRIF.

## Citas cortas

- "a large language model is just 2 files" (inicio de la charla).
- "this context window is your finite precious resource of your working memory" (sección "LLM OS"; transcripción automática).

## Notas de vigencia para el tutor

- Los modelos y cifras de la charla son de 2023. Para ejemplos actuales, usar los modelos vigentes y verificar sus fichas técnicas.
- La idea de "sistema 2" hoy existe en productos: modelos de razonamiento y modos de pensamiento extendido. La charla es anterior.
- Para profundizar (tokenización, RLHF), derivar a KAR-DEEP (2025).

## Preguntas de práctica

- P: ¿Qué dos "archivos" componen un LLM, según Karpathy, y cuál de los dos es caro de producir?
  R: El archivo de parámetros (pesos) y el código que lo ejecuta. Lo caro es producir los parámetros mediante el pre-entrenamiento (miles de GPUs, semanas y millones de dólares); ejecutar el modelo es comparativamente barato.
- P: ¿Por qué un LLM puede entregar un dato falso con formato perfecto?
  R: Porque genera la continuación más probable según la distribución de su entrenamiento: "sueña" documentos. Aprende la forma (qué va después de "ISBN:") sin garantía de que el contenido sea real. Eso es una alucinación.
- P: ¿Qué cambia entre el pre-entrenamiento y el ajuste fino?
  R: El pre-entrenamiento usa enormes volúmenes de texto de internet (cantidad) para aprender conocimiento general. El ajuste fino usa muchas menos conversaciones de alta calidad escritas por personas (calidad) para que el modelo se comporte como asistente.
- P: En la analogía del "sistema operativo", ¿qué papel cumple la ventana de contexto y qué implica para diseñar un agente de ventas?
  R: Es como la RAM: memoria de trabajo finita. Implica elegir qué información entra en cada momento (precios vigentes, historial del cliente) y guardar el resto fuera (CRM, archivos), trayéndolo con herramientas cuando se necesita.
- P: ¿Cuál es la diferencia entre jailbreak y prompt injection, y cuál preocupa más en un agente que lee correos de clientes?
  R: El jailbreak es un usuario que engaña al modelo para saltarse restricciones. El prompt injection son instrucciones maliciosas escondidas en el contenido que el modelo procesa. En un agente que lee correos preocupa más el prompt injection, porque cualquier tercero puede escribirle al agente.

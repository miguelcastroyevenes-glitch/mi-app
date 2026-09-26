---
id: WENG-AGT
titulo: "LLM Powered Autonomous Agents"
autor: "Lilian Weng (Lil'Log)"
anio: 2023
url: https://lilianweng.github.io/posts/2023-06-23-agent/
etapas: [2]
semanas: [4]
idioma_fuente: en
tipo: post técnico (revisión de literatura)
verificado: 2026-09-26 (texto completo leído)
vigencia: "Junio 2023. La anatomía (planificación, memoria, herramientas) sigue siendo el marco estándar; los ejemplos (AutoGPT, HuggingGPT) son históricos."
---

# WENG-AGT · LLM Powered Autonomous Agents (Weng, 2023)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Es la revisión más citada sobre la "anatomía" de un agente. Weng propone ver el LLM como el cerebro del agente, complementado por tres componentes: **planificación** (descomponer tareas y reflexionar sobre errores), **memoria** (de corto y largo plazo) y **uso de herramientas** (APIs externas para lo que el modelo no sabe o no puede hacer). Para cada componente repasa las técnicas de la investigación de ese momento, muestra casos (un agente químico y una simulación social de 25 personajes) y termina con tres límites que en 2026 siguen presentes: contexto finito, planificación a largo plazo frágil y poca confiabilidad de la interfaz en lenguaje natural.

## Ideas clave

1. **Planificación: descomponer.** Con *chain of thought* ("pensar paso a paso"), *tree of thoughts* (explorar varias ramas) o un planificador externo (LLM+P). También se puede descomponer con instrucciones específicas de la tarea o con ayuda humana.
2. **Planificación: reflexionar.** *ReAct* intercala pensamiento → acción → observación, y rinde mejor que solo actuar. *Reflexion* agrega memoria de errores pasados para corregir el plan. Hay más variantes (Chain of Hindsight, Algorithm Distillation) que aprenden de secuencias de intentos.
3. **Memoria, por analogía con la humana:**
   - sensorial ≈ representaciones (embeddings) de las entradas;
   - corto plazo ≈ aprendizaje en contexto, limitado por la ventana;
   - largo plazo ≈ almacén vectorial externo con búsqueda rápida.
4. **Búsqueda vectorial (MIPS/ANN).** Para recuperar rápido se usan algoritmos de vecinos cercanos aproximados (LSH, ANNOY, HNSW, FAISS, ScaNN), que sacrifican algo de precisión a cambio de mucha velocidad.
5. **Herramientas.** MRKL (el LLM enruta a módulos expertos), Toolformer/TALM (modelos entrenados para llamar APIs), *function calling* y HuggingGPT (el LLM planifica y elige modelos). El benchmark API-Bank evalúa tres niveles: llamar una API, encontrar la API correcta y planificar varias llamadas.
6. **Casos.** En ChemCrow, la evaluación hecha por un LLM decía que GPT-4 y el agente rendían igual, mientras que expertos humanos encontraron el agente muy superior: un LLM no siempre sabe juzgar dominios expertos. En Generative Agents, la memoria se recupera por *recencia, importancia y relevancia* y se sintetiza en reflexiones.
7. **Límites:** contexto finito, planificación de largo plazo y ajuste ante errores inesperados, y una interfaz en lenguaje natural poco confiable (errores de formato, instrucciones ignoradas). Por eso gran parte del código de los demos se dedicaba a interpretar la salida del modelo.

## Conceptos y definiciones

- **Agente (en este marco):** LLM como controlador central + planificación + memoria + herramientas.
- **Chain of thought (CoT):** pedir razonamiento paso a paso para descomponer problemas.
- **ReAct:** patrón Thought → Action → Observation repetido.
- **Memoria de corto plazo:** lo que cabe en la ventana de contexto (aprendizaje en contexto).
- **Memoria de largo plazo:** almacén externo, típicamente vectorial, consultado por similitud.
- **Embedding:** representación numérica del significado de un texto.
- **ANN / MIPS:** búsqueda aproximada de los vectores más similares.

## Errores comunes

- Creer que "memoria" significa que el modelo recuerda solo. Hay que diseñar qué se guarda, dónde y cómo se recupera.
- Usar solo un LLM para evaluar resultados en un dominio experto (el caso ChemCrow). Hace falta validación humana experta.
- Dar planes largos sin puntos de verificación. La planificación de largo plazo es justamente un punto débil.
- Ignorar el costo de interpretar la salida del modelo. Hoy existen salidas estructuradas y *tool calling* nativo, que reducen ese problema.

## Ejemplo aplicado: anatomía de un Sales Intelligence Agent (proyecto de la semana 6)

- **Planificación:** ante "¿qué clientes de la cartera tienen más probabilidad de comprar este mes?", el agente descompone: (1) filtrar leads activos, (2) cruzar con cotizaciones recientes, (3) revisar el estado del crédito y (4) ordenar y explicar.
- **Reflexión:** si una consulta al CRM viene vacía, observa el resultado y reformula el filtro, en lugar de inventar.
- **Memoria de corto plazo:** la lista del día y el objetivo actual.
- **Memoria de largo plazo:** notas históricas del cliente y conversaciones previas, recuperadas por similitud cuando el vendedor pregunta "¿qué le preocupaba a este cliente?".
- **Herramientas:** consulta al CRM, calendario y simulador de crédito.
- **Validación:** el jefe de local revisa una muestra de las recomendaciones (evaluación experta, no solo LLM).

## Citas cortas

- "In a LLM-powered autonomous agent system, LLM functions as the agent's brain" (sección "Agent System Overview").
- Sobre los límites: "the reliability of model outputs is questionable, as LLMs may make formatting errors and occasionally exhibit rebellious behavior" (sección "Challenges").

## Notas de vigencia para el tutor

- El post es de 2023. Varias técnicas (Toolformer, Algorithm Distillation) son de interés histórico. Para práctica actual, conectar con ANT-BEA (patrones), ANT-CTX (memoria agéntica con notas) y ANT-CR (RAG).
- El artículo original de ReAct está en el catálogo como REACT (CC BY 4.0).

## Preguntas de práctica

- P: ¿Cuáles son los tres componentes que complementan al LLM en el marco de Weng?
  R: Planificación (descomposición de tareas y auto-reflexión), memoria (corto y largo plazo) y uso de herramientas (APIs externas).
- P: Describe el patrón ReAct con un ejemplo de ventas.
  R: El agente alterna Pensamiento → Acción → Observación. Por ejemplo: "Necesito el estado del crédito" → llama a `consultar_credito(rut)` → observa "pendiente de documentos" → piensa el siguiente paso (pedir la liquidación de sueldo) y sigue hasta terminar.
- P: ¿Con qué se corresponden la memoria de corto y la de largo plazo en un agente?
  R: La de corto plazo es el aprendizaje en contexto, limitado por la ventana de contexto. La de largo plazo es un almacén externo (típicamente una base vectorial) que se consulta con búsqueda rápida por similitud.
- P: ¿Qué enseña el caso ChemCrow sobre evaluar agentes?
  R: Que un LLM evaluador puede no detectar fallas en dominios expertos: la evaluación con LLM dio empate y la de expertos humanos mostró una diferencia grande. En dominios especializados hay que calibrar con expertos.
- P: Nombra los tres desafíos que Weng identifica y uno que siga vigente.
  R: Contexto finito, planificación de largo plazo y descomposición, y la poca confiabilidad de la interfaz en lenguaje natural. Los tres siguen presentes en alguna medida; el contexto finito, por ejemplo, es lo que motiva el context engineering (ANT-CTX).

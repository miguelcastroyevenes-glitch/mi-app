---
id: ANT-BEA
titulo: "Building Effective AI Agents"
autor: "Anthropic (Erik S. y Barry Zhang)"
anio: 2024
url: https://www.anthropic.com/engineering/building-effective-agents
etapas: [1, 2]
semanas: [1, 2, 6]
idioma_fuente: en
tipo: guía oficial (post de ingeniería)
verificado: 2026-09-26 (texto completo leído)
vigencia: "Publicado el 19-dic-2024. En 2026 el post lleva una nota: el panorama de herramientas cambió y Anthropic remite a Managed Agents (ver ANT-MANAGED). Los patrones y principios siguen vigentes."
---

# ANT-BEA · Building Effective AI Agents (Anthropic, 2024)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Es el texto más citado para ordenar el vocabulario del área. Anthropic llama "sistemas agénticos" a todo lo que combina LLMs con herramientas, y separa dos arquitecturas: los **workflows**, donde el código define el camino, y los **agentes**, donde el modelo decide el camino. El mensaje central es de negocio: usar la solución más simple que funcione y agregar complejidad solo cuando mejore los resultados de forma demostrable. El post describe un bloque base (el "LLM aumentado"), cinco patrones de workflow y el agente autónomo, y cierra con tres principios y un apéndice sobre cómo diseñar herramientas.

## Ideas clave

1. **Empezar simple.** Muchas veces basta una sola llamada al LLM, bien optimizada, con recuperación de información y ejemplos. Los sistemas agénticos cambian latencia y costo por mejor desempeño, y hay que evaluar si ese intercambio conviene.
2. **Frameworks con cuidado.** Ayudan a partir rápido, pero agregan capas que esconden los prompts y las respuestas. La recomendación es usar primero la API directamente y, si se usa un framework, entender qué hace por debajo.
3. **Bloque base: el LLM aumentado.** Un LLM con recuperación, herramientas y memoria. MCP es una forma de conectarlo con herramientas de terceros.
4. **Cinco patrones de workflow:**
   - *Prompt chaining* (encadenamiento): la tarea se divide en pasos fijos, con "compuertas" de verificación entre ellos.
   - *Routing* (enrutamiento): se clasifica la entrada y se deriva a un proceso especializado, o a un modelo más barato si es fácil.
   - *Parallelization* (paralelización): *sectioning* (subtareas independientes en paralelo) o *voting* (la misma tarea varias veces para ganar confianza).
   - *Orchestrator-workers* (orquestador-trabajadores): un LLM central divide la tarea de forma dinámica, delega y sintetiza. Se usa cuando no se pueden prever las subtareas.
   - *Evaluator-optimizer* (evaluador-optimizador): un LLM genera y otro critica en un ciclo. Funciona cuando hay criterios claros y la crítica mejora el resultado.
5. **Agentes.** Son LLMs que usan herramientas según la retroalimentación del entorno, dentro de un loop. Necesitan "verdad de terreno" en cada paso (resultados de herramientas), pausas para intervención humana y condiciones de término (por ejemplo, un máximo de iteraciones). Su autonomía implica más costo y errores que se acumulan, así que conviene probarlos en *sandbox* y con guardrails.
6. **Tres principios:** simplicidad, transparencia (mostrar los pasos de planificación) y una interfaz agente-computador (ACI) bien diseñada, con herramientas documentadas y probadas.
7. **Dónde aportan más valor (apéndice 1):** en tareas que combinan conversación y acción, con criterios de éxito claros, ciclos de retroalimentación y supervisión humana. Los ejemplos son atención al cliente y agentes de programación.
8. **Diseñar herramientas como prompts (apéndice 2):** usar formatos cercanos al texto natural, dar espacio para "pensar" y hacer las herramientas a prueba de errores (*poka-yoke*). Por ejemplo, exigir rutas absolutas eliminó errores del agente.

## Conceptos y definiciones

- **Sistema agéntico:** término paraguas que incluye workflows y agentes.
- **Workflow:** LLMs y herramientas orquestados por rutas de código predefinidas.
- **Agente:** el LLM dirige su propio proceso y el uso de herramientas.
- **LLM aumentado:** LLM + recuperación + herramientas + memoria.
- **Gate (compuerta):** chequeo programático entre pasos de una cadena.
- **ACI (agent-computer interface):** el equivalente, para agentes, del diseño de interfaces para humanos.
- **Poka-yoke:** diseñar la herramienta para que sea difícil usarla mal.

## Errores comunes

- Construir un agente cuando un workflow o una sola llamada bastaban. Resultado: más costo, más latencia y menos previsibilidad.
- Adoptar un framework sin entender los prompts que genera, lo que hace muy difícil depurar.
- Confundir *orchestrator-workers* con paralelización. En la paralelización las subtareas están definidas de antemano; en el orquestador las decide el modelo.
- Dar autonomía sin condiciones de término ni puntos de control humano.
- Dedicarle todo el esfuerzo al prompt y nada a las herramientas. En su agente para SWE-bench, Anthropic dedicó más tiempo a optimizar herramientas que al prompt general.

## Ejemplo aplicado: gestión de leads en el concesionario

- **Routing:** clasificar cada lead entrante (cotización, test drive, crédito, postventa, reclamo) y derivarlo al flujo correcto. Los casos simples van a un modelo barato.
- **Prompt chaining con compuerta:** redactar la respuesta de WhatsApp y luego verificar con código que el precio mencionado coincida con la lista vigente antes de enviarla.
- **Evaluator-optimizer:** un evaluador revisa el tono y el cumplimiento de la política comercial, y pide correcciones.
- **Agente:** solo para casos abiertos, como armar una propuesta que combine stock disponible, simulación de crédito y parte de pago, donde no se pueden prever los pasos.
- **Cuándo NO usar un agente:** calcular comisiones o bonos con reglas fijas. Eso es código o planilla.

## Citas cortas

- "Workflows are systems where LLMs and tools are orchestrated through predefined code paths." (sección "What are agents?")
- "you should consider adding complexity only when it demonstrably improves outcomes." (sección "Combining and customizing these patterns")

## Notas de vigencia para el tutor

- Los nombres de modelos del post (p. ej. Haiku 4.5 y Sonnet 4.5 en el ejemplo de routing) cambian. Usar los vigentes.
- Para el enfoque 2026 de Anthropic sobre arneses gestionados, complementar con ANT-MANAGED. Para la definición actualizada ("LLMs que usan herramientas de forma autónoma en un loop"), ver ANT-CTX.
- La malla enlaza `resources.anthropic.com/building-effective-ai-agents` (recurso descargable). La fuente canónica es este post de ingeniería.

## Preguntas de práctica

- P: ¿Cuál es la diferencia arquitectónica entre un workflow y un agente según Anthropic?
  R: En un workflow, los LLMs y las herramientas siguen rutas de código predefinidas. En un agente, el LLM dirige su propio proceso y decide qué herramientas usar y cuándo.
- P: ¿Cuál es la primera recomendación antes de construir un sistema agéntico?
  R: Buscar la solución más simple posible: muchas veces una sola llamada al LLM, con recuperación de información y ejemplos, basta. La complejidad se agrega solo si mejora los resultados de forma demostrable.
- P: ¿Qué patrón usarías para clasificar leads por tipo y derivarlos a flujos distintos, y por qué?
  R: Routing. Hay categorías claras que conviene tratar por separado con prompts y herramientas especializados, y la clasificación se puede hacer con precisión. También permite mandar los casos fáciles a un modelo más barato.
- P: ¿En qué se diferencia orchestrator-workers de parallelization?
  R: En la paralelización, las subtareas están predefinidas y corren en paralelo. En orchestrator-workers, un LLM central decide dinámicamente qué subtareas crear según la entrada, y luego sintetiza los resultados.
- P: Nombra los tres principios que Anthropic sigue al implementar agentes.
  R: Simplicidad en el diseño, transparencia (mostrar explícitamente los pasos de planificación) y una interfaz agente-computador (ACI) cuidada, con herramientas bien documentadas y probadas.

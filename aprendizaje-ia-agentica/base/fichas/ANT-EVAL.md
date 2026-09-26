---
id: ANT-EVAL
titulo: "Demystifying evals for AI agents"
autor: "Anthropic (Mikaela Grace, Jeremy Hadfield, Rodrigo Olivares, Jiri De Jonghe)"
anio: 2026
url: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
etapas: [5]
semanas: [15, 16]
idioma_fuente: en
tipo: guía oficial (post de ingeniería)
verificado: 2026-09-26 (texto completo leído)
vigencia: "Publicado el 9-ene-2026. Vigente. Los benchmarks y cifras citados (SWE-bench >80%, Opus 4.5) cambian rápido; el método no."
---

# ANT-EVAL · Demystifying evals for AI agents (Anthropic, 2026)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Es la guía vigente de Anthropic para evaluar agentes. Parte de un diagnóstico: los agentes son difíciles de evaluar porque actúan en muchos pasos, modifican el entorno y a veces encuentran soluciones que el evaluador no previó. Primero fija un **vocabulario** (tarea, intento, calificador, transcripción, resultado, arnés de evaluación, arnés del agente, suite). Luego compara tres tipos de calificadores (**código, modelo y humano**), distingue evals de **capacidad** y de **regresión**, muestra cómo evaluar agentes de programación, conversacionales, de investigación y de uso de computador, explica el no determinismo con **pass@k** y **pass^k**, y entrega una **hoja de ruta de 8 pasos** para pasar de cero a evals confiables. Cierra ubicando las evals junto al monitoreo en producción, los tests A/B, el feedback de usuarios y la revisión humana.

## Ideas clave

1. **Por qué evals.** Sin ellas, el equipo "vuela a ciegas": espera reclamos, reproduce a mano y cruza los dedos. Con ellas se detectan regresiones, se adoptan modelos nuevos en días y se obliga a definir qué es éxito. El costo se ve al inicio y el beneficio se acumula después.
2. **Vocabulario:**
   - *Tarea:* un caso con entradas y criterio de éxito.
   - *Intento (trial):* cada ejecución de una tarea; se hacen varios por el no determinismo.
   - *Calificador (grader):* la lógica que puntúa.
   - *Transcripción:* el registro completo de un intento.
   - *Resultado (outcome):* el estado final del entorno. Que el agente diga "reservé" no prueba que exista la reserva.
3. **Tres calificadores:** de **código** (rápidos, baratos, objetivos, pero frágiles ante variaciones válidas), de **modelo** (flexibles y con matices, pero no deterministas y requieren calibración humana) y **humanos** (la referencia de calidad, pero caros y lentos). Se combinan.
4. **Capacidad vs. regresión.** Las evals de capacidad parten con tasa baja y dan una "colina que subir". Las de regresión deberían pasar cerca de 100% y protegen contra retrocesos. Las evals de capacidad que ya se dominan "se gradúan" a regresión.
5. **Agentes conversacionales (como uno de ventas).** Suelen requerir un segundo LLM que simule al usuario. El éxito es multidimensional: ¿se resolvió? (chequeo de estado), ¿en menos de N turnos? (transcripción), ¿con el tono adecuado? (rúbrica LLM).
6. **No determinismo.** *pass@k* es la probabilidad de al menos un éxito en k intentos: sirve cuando basta con que uno funcione. *pass^k* es la probabilidad de que los k intentos salgan bien: sirve para agentes de cara al cliente, que deben ser consistentes. Con 75% por intento y 3 intentos, pass^3 ≈ 42%.
7. **Hoja de ruta en 8 pasos:**
   0. Empezar temprano: 20–50 tareas sacadas de fallas reales bastan.
   1. Partir por lo que ya se prueba a mano y por los reclamos o tickets.
   2. Escribir tareas sin ambigüedad, con solución de referencia (dos expertos deberían llegar al mismo veredicto).
   3. Tener conjuntos balanceados: probar cuándo el agente debe hacer algo y cuándo no.
   4. Usar un arnés estable, con entornos aislados y limpios en cada intento.
   5. Diseñar bien los calificadores: evaluar **lo que produjo, no el camino exacto**; dar crédito parcial; calibrar el juez LLM con humanos y darle la opción "no sé".
   6. **Leer las transcripciones.**
   7. Vigilar la saturación (una eval al 100% no enseña nada nuevo).
   8. Mantener la suite viva, con dueños claros y contribución abierta: vendedores o jefes pueden aportar tareas.
8. **Modelo del queso suizo.** Ninguna capa detecta todo. Se combinan evals automáticas (antes del lanzamiento y en cada cambio), monitoreo en producción, tests A/B, feedback de usuarios, lectura semanal de transcripciones y estudios humanos para calibrar.

## Conceptos y definiciones

- **Eval:** prueba en la que se da una entrada a un sistema de IA y se aplica una lógica de calificación a su salida.
- **Arnés de evaluación:** la infraestructura que corre las tareas, registra y agrega resultados.
- **Arnés del agente (scaffold):** el sistema que permite al modelo actuar como agente. Evaluar "un agente" es evaluar modelo + arnés.
- **Suite:** conjunto de tareas con un objetivo común (p. ej. descuentos, agendamiento, escalamiento).
- **pass@k / pass^k:** al menos un éxito en k intentos / todos los k intentos exitosos.
- **Saturación:** la eval ya no discrimina porque casi todo pasa.
- **Eval-driven development:** definir evals de una capacidad antes de que el agente la tenga.

## Errores comunes

- Postergar las evals "hasta tener cientos de casos".
- Calificar la secuencia exacta de herramientas y castigar soluciones válidas no previstas.
- Tener tareas ambiguas: un 0% en muchos intentos suele indicar una tarea o un calificador rotos, no un agente incapaz.
- Evals desbalanceadas, que producen un agente que "siempre busca" o "siempre escala".
- Entornos compartidos entre intentos (archivos o caché que se filtran) que inflan o hunden resultados.
- Creer en el puntaje sin leer transcripciones.

## Ejemplo aplicado: Agent QA Lab (proyecto de la semana 19)

Una suite de 40 tareas para el agente de seguimiento de leads:

- **Capacidad (15):** casos difíciles, como un cliente que pide descuento fuera de política, un lead con datos incompletos o un cliente con crédito rechazado.
- **Regresión (25):** agendar un test drive, responder una consulta de stock o escalar un reclamo.
- **Calificadores:**
  - código: ¿quedó el evento en la agenda con el modelo correcto? ¿el precio citado coincide con la lista?;
  - rúbrica LLM: tono, claridad y que no prometa bonos inexistentes;
  - humano: el jefe de local revisa 10 transcripciones por semana.
- **Balance:** incluir casos donde NO debe ofrecer descuento y casos donde sí debe escalar.
- **Métrica de cara al cliente:** pass^3 en las tareas de regresión, porque el cliente espera consistencia.

## Citas cortas

- "it's often better to grade what the agent produced, not the path it took." (paso 5)
- "Read the transcripts!" (conclusión)

## Notas de vigencia para el tutor

- Es la fuente que la malla cita en "Por qué" de la etapa 5.
- El apéndice lista frameworks (Harbor, Braintrust, LangSmith, Langfuse, Arize Phoenix). Sus nombres y precios cambian, así que hay que verificarlos antes de recomendar.
- Complementar con HAM-FAQ (análisis de errores y validación del juez LLM) y MAST (fallas multi-agente).

## Preguntas de práctica

- P: ¿Cuál es la diferencia entre "transcripción" y "resultado" en una eval de agentes? Da un ejemplo.
  R: La transcripción es el registro completo del intento (mensajes, llamadas a herramientas, razonamiento). El resultado es el estado final del entorno. Ejemplo: el agente puede decir "agendé el test drive" (transcripción), pero el resultado es si el evento existe realmente en la agenda.
- P: Compara los calificadores de código, de modelo y humanos en una fortaleza y una debilidad cada uno.
  R: Código: rápido, barato y objetivo, pero frágil ante variaciones válidas. Modelo: flexible y capta matices, pero no es determinista y requiere calibración humana. Humano: la mejor calidad, pero caro y lento.
- P: ¿Qué diferencia hay entre una eval de capacidad y una de regresión, y qué tasa de éxito se espera en cada una?
  R: La de capacidad mide lo que el agente aún no hace bien y parte con tasa baja (una colina que subir). La de regresión verifica que siga haciendo lo que ya hacía y debería pasar cerca de 100%.
- P: Si tu agente acierta 75% por intento, ¿qué valor tiene pass^3 y por qué importa en un agente de cara al cliente?
  R: 0,75³ ≈ 42%. Importa porque el cliente espera un comportamiento confiable cada vez: pass^k mide consistencia, no solo la posibilidad de acertar alguna vez.
- P: ¿Con cuántas tareas recomienda Anthropic empezar y de dónde sacarlas?
  R: Con 20–50 tareas simples tomadas de fallas reales: pruebas manuales que ya se hacen antes de cada cambio, reclamos, tickets de soporte y bugs reportados por usuarios.

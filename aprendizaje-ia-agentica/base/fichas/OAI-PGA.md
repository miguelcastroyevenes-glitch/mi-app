---
id: OAI-PGA
titulo: "A practical guide to building agents"
autor: "OpenAI"
anio: 2025
url: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
etapas: [2, 5]
semanas: [5, 6, 18]
idioma_fuente: en
tipo: guía oficial (PDF, 34 págs.)
verificado: 2026-09-26 (PDF completo leído)
vigencia: "Guía de 2025. Los ejemplos de código usan el Agents SDK y modelos de ese momento (gpt-4o-mini, o1, o3-mini). Los conceptos son estables; los nombres de modelos y APIs no."
---

# OAI-PGA · A practical guide to building agents (OpenAI, 2025)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Es la guía de OpenAI para equipos de producto que van a construir su primer agente. Define agente como un sistema que ejecuta flujos de trabajo **en nombre del usuario con alto grado de independencia**, y descarta como agentes a los chatbots simples o los clasificadores. Explica cuándo conviene un agente (decisiones con matices, reglas inmanejables, datos no estructurados), sus tres componentes (modelo, herramientas, instrucciones), dos familias de orquestación (un solo agente en loop, o multi-agente con patrón *manager* o *descentralizado*) y un sistema de guardrails en capas que incluye la intervención humana. El consejo general es incremental: empezar con un agente, validar con usuarios reales y crecer.

## Ideas clave

1. **Qué es (y qué no es) un agente.** Usa un LLM para controlar la ejecución del flujo y tomar decisiones, reconoce cuándo terminó, puede corregirse y devolver el control al usuario si falla. Accede a herramientas y las elige según el estado, dentro de guardrails. Una aplicación que usa un LLM pero no controla el flujo no es un agente.
2. **Cuándo construir uno.** Hay tres señales: (a) decisiones complejas con excepciones (p. ej. aprobar devoluciones), (b) reglas difíciles de mantener, (c) mucha información no estructurada. Si el caso no cumple esto, basta una solución determinista.
3. **Tres componentes:** modelo, herramientas e instrucciones.
4. **Elegir modelo.** Primero se arma el prototipo con el modelo más capaz para fijar una línea base con evals. Después se prueban modelos más chicos donde sigan cumpliendo la meta de precisión, y así se optimiza costo y latencia.
5. **Tres tipos de herramientas:** de **datos** (consultar CRM o documentos), de **acción** (enviar correos, actualizar registros, derivar a un humano) y de **orquestación** (otros agentes usados como herramientas). Para sistemas antiguos sin API existe *computer use*.
6. **Instrucciones.** Conviene partir de procedimientos, guiones o políticas que ya existen, dividir en pasos, que cada paso sea una acción concreta y anticipar casos borde. Un modelo avanzado puede convertir un documento de ayuda en instrucciones numeradas.
7. **Orquestación: maximizar un solo agente primero.** Todo agente necesita un *run* (loop) con condiciones de salida. Se pasa a multi-agente cuando hay lógica condicional excesiva o herramientas que se confunden. Importa más el traslape que la cantidad: hay implementaciones con más de 15 herramientas bien definidas que funcionan, y otras que fallan con menos de 10 que se traslapan.
8. **Dos patrones multi-agente:**
   - **Manager (agentes como herramientas):** un agente central delega y mantiene el control y la conversación con el usuario.
   - **Descentralizado (handoffs):** los agentes se pasan el control entre pares. Sirve para triaje: por ejemplo, el agente de triaje deriva al de pedidos.
9. **Guardrails en capas.** Clasificador de relevancia, clasificador de seguridad (jailbreak/injection), filtro de datos personales, moderación, **salvaguardas por herramienta con riesgo bajo/medio/alto** (según si solo lee o también escribe, si es reversible, qué permisos requiere y su impacto financiero), reglas deterministas (listas de bloqueo, largo máximo, regex) y validación de salida. Se complementan con autenticación y control de acceso.
10. **Intervención humana.** Hay dos disparadores: superar un umbral de fallas o reintentos, y acciones de alto riesgo (irreversibles, sensibles o de alto monto) hasta que haya confianza.

## Conceptos y definiciones

- **Agente:** sistema que realiza tareas de forma independiente en nombre del usuario.
- **Run / loop:** ciclo en el que el agente opera hasta una condición de salida (herramienta final, respuesta sin herramientas, error o máximo de turnos).
- **Handoff:** transferencia unidireccional del control (y del estado de la conversación) a otro agente.
- **Agente como herramienta:** un agente especializado que el manager invoca como si fuera una función.
- **Guardrail:** control que valida entradas, salidas o acciones. Varios guardrails juntos forman una defensa en capas.
- **Plantilla de prompt con variables:** un prompt base con variables de política, en vez de muchos prompts distintos.

## Errores comunes

- Saltar directo a una arquitectura multi-agente compleja. La guía observa que a los clientes les va mejor con un enfoque incremental.
- Elegir el modelo más barato desde el inicio sin una línea base. No se sabe qué se está perdiendo.
- Confiar en un solo guardrail. Ninguno basta por sí solo.
- No clasificar las herramientas por riesgo, y dejar que el agente ejecute acciones irreversibles sin aprobación.
- Escribir instrucciones desde cero cuando ya existen procedimientos operativos que se pueden convertir.

## Ejemplo aplicado: agente de postventa y ventas del local

- **Herramientas de datos:** `consultar_stock(modelo)`, `buscar_cliente(rut)`, `estado_credito(solicitud)`.
- **Herramientas de acción:** `agendar_test_drive` (riesgo bajo, reversible), `enviar_cotizacion` (medio) y `aplicar_descuento_extra` (alto: requiere aprobación del jefe de local).
- **Orquestación:** un solo agente al inicio. Si aparecen confusiones entre postventa y ventas, se pasa a un patrón descentralizado con un agente de triaje que hace handoff a un agente de ventas o a uno de servicio técnico.
- **Instrucciones:** convertir el protocolo de atención y la política comercial vigente en pasos numerados.
- **Escalamiento humano:** después de dos intentos fallidos de entender la solicitud, o ante cualquier descuento fuera de la política.

## Citas cortas

- "Agents are systems that independently accomplish tasks on your behalf." (sección "What is an agent?")
- "Our general recommendation is to maximize a single agent's capabilities first." (sección "When to consider creating multiple agents")

## Notas de vigencia para el tutor

- En 2026, OpenAI ofrece Agents API (arnés gestionado), Agents SDK y Responses API (ver OAI-AGENTS). El código del PDF usa el Agents SDK de 2025 y puede estar desactualizado; hay que enseñar conceptos, no sintaxis.
- En la semana 18 (guardrails y autonomía) se reutilizan la clasificación de herramientas por riesgo y los disparadores de intervención humana.

## Preguntas de práctica

- P: Según OpenAI, ¿por qué un chatbot simple o un clasificador de sentimiento no son agentes?
  R: Porque, aunque usan un LLM, no lo usan para controlar la ejecución de un flujo de trabajo ni para tomar decisiones sobre herramientas en nombre del usuario.
- P: ¿Cuáles son las tres señales de que un caso merece un agente en vez de automatización tradicional?
  R: Decisiones complejas con matices o excepciones, reglas difíciles de mantener y dependencia de datos no estructurados.
- P: ¿Qué estrategia recomienda la guía para elegir el modelo?
  R: Prototipar con el modelo más capaz para fijar una línea base con evals, cumplir la meta de precisión y luego reemplazar por modelos más chicos donde sigan rindiendo, para bajar costo y latencia.
- P: ¿Cuál es la diferencia entre el patrón manager y el descentralizado?
  R: En el manager, un agente central invoca a los especialistas como herramientas y mantiene el control y la conversación con el usuario. En el descentralizado, los agentes se transfieren el control entre pares mediante handoffs, y el que recibe toma la conversación.
- P: ¿Qué dos situaciones deben disparar intervención humana y cómo se aplicaría a descuentos en el local?
  R: Superar umbrales de fallas o reintentos, y acciones de alto riesgo (irreversibles, sensibles o de alto monto). Un descuento fuera de la política comercial debería requerir aprobación del jefe de local antes de ejecutarse.

---
id: OAI-GOV
titulo: "Practices for Governing Agentic AI Systems"
autor: "Yonadav Shavit, Sandhini Agarwal, Miles Brundage et al. (OpenAI)"
anio: 2023
url: https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf
url_pagina: https://openai.com/index/practices-for-governing-agentic-ai-systems/
etapas: [5]
semanas: [18, 19]
idioma_fuente: en
tipo: whitepaper (PDF, 23 págs.)
verificado: 2026-09-26 (PDF leído; la página openai.com bloquea bots, confirmada en índice de búsqueda)
vigencia: "Diciembre 2023. Es un marco conceptual y no una norma; sus preguntas abiertas siguen vigentes. Para regulación aplicable en Chile, ver LEY-21719 y CL-PNIA."
---

# OAI-GOV · Prácticas para gobernar sistemas de IA agéntica (OpenAI, 2023)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

El documento define los sistemas agénticos como sistemas que **persiguen metas complejas con supervisión directa limitada** y pregunta **quién debe hacer qué** para que sean seguros y responsables. Distingue tres partes: el **desarrollador del modelo**, el **implementador del sistema** (quien construye el agente sobre el modelo) y el **usuario**. Propone siete prácticas base, cada una con preguntas abiertas. El ejemplo que las motiva: un asistente al que se le pide comprar ingredientes para un pastel japonés y termina comprando un pasaje a Japón no reembolsable; varias partes podrían haberlo evitado. Cierra con impactos indirectos: carreras de adopción, desplazamiento laboral, cambios en el equilibrio ataque-defensa y fallas correlacionadas.

## Ideas clave

Las siete prácticas:

1. **Evaluar la idoneidad para la tarea.** Probar si el agente cumple de forma confiable en las condiciones esperadas. Como las tareas largas acumulan errores raros, conviene evaluar cada subtarea por separado, con prioridad en las acciones de alto riesgo.
2. **Restringir el espacio de acción y exigir aprobación.** Algunas decisiones requieren que un humano autorice (*human-in-the-loop*), como transacciones financieras grandes e irreversibles. La dificultad es que el humano tenga contexto suficiente y no apruebe "en automático" por fatiga. Otras acciones se prohíben del todo, y se pueden poner pausas (*timeouts*) que requieren reautorización.
3. **Definir comportamientos por defecto.** Supuestos de sentido común ("el usuario prefiere que no gaste su dinero"), elegir la acción menos disruptiva que logre la meta y pedir aclaraciones cuando hay incertidumbre sobre la intención del usuario.
4. **Hacer legible la actividad del agente.** Mostrar el razonamiento y las interacciones (entradas de herramientas, mensajes de otros agentes) ayuda a detectar errores y manipulación. Pero el razonamiento visible no siempre refleja lo que realmente guía al modelo, y puede ser demasiado largo para leerlo.
5. **Monitoreo automático.** Un segundo sistema de IA revisa acciones y razonamiento a una escala que un humano no puede cubrir. Tiene costos y riesgos propios: privacidad de los datos retenidos y posible uso del monitoreo para control indebido.
6. **Atribuibilidad.** Poder rastrear un agente hasta el humano responsable, por ejemplo con identificadores de agente en interacciones de alto riesgo (datos privados, transacciones), equilibrado con la privacidad.
7. **Interrumpibilidad y control.** Siempre debe existir un apagado ordenado, tanto de una categoría de acciones (revocar credenciales financieras) como del agente completo. Conviene que el agente **prepare de antemano un procedimiento de salida** (p. ej. avisar a los invitados si se interrumpe a medio agendar una reunión) y que no pueda impedir su propio apagado.

**Principio transversal:** la responsabilidad se reparte entre desarrollador, implementador y usuario, y cada práctica tiene un responsable natural.

## Conceptos y definiciones

- **Sistema de IA agéntica:** persigue metas complejas de forma adaptable, con supervisión directa limitada.
- **Agenticidad (agenticness):** es cuestión de grado, no una distinción binaria: "el grado en que un sistema puede lograr de forma adaptable metas complejas en entornos complejos con supervisión directa limitada". Se descompone en cuatro dimensiones: complejidad de la meta, complejidad del entorno, adaptabilidad y ejecución independiente.
- **Desarrollador del modelo / implementador del sistema / usuario:** las tres partes del ciclo de vida.
- **Human-in-the-loop:** un humano autoriza ciertas acciones antes de que ocurran.
- **Legibilidad:** que la actividad y el razonamiento del agente sean visibles y comprensibles.
- **Atribuibilidad:** poder asignar responsabilidad a un humano por lo que hizo el agente.
- **Interrumpibilidad:** capacidad de detener el agente de forma ordenada.

## Errores comunes

- Poner aprobaciones humanas en todo, lo que causa fatiga y aprobaciones automáticas sin revisar. Hay que reservarlas para lo de alto riesgo.
- Confiar en que el razonamiento visible del agente explica fielmente sus decisiones.
- No registrar quién autorizó qué, y después no poder auditar un error.
- Tener un "botón de apagado" que deja procesos a medias (una cotización enviada, un agendamiento parcial) sin avisar a nadie.
- Monitorear conversaciones de clientes sin considerar privacidad ni retención de datos (en Chile, Ley 21.719).

## Ejemplo aplicado: protocolo de aprobación del local (semana 19)

| Práctica | Aplicación en el concesionario |
|---|---|
| Idoneidad | Piloto de 4 semanas con evals (ANT-EVAL) por subtarea: cotizar, agendar, escalar |
| Aprobación | Descuentos fuera de política, anulaciones de reserva y envíos masivos: requieren aprobación del jefe de local |
| Defaults | "Ante duda sobre la intención del cliente, preguntar"; "nunca ofrecer bonos no vigentes" |
| Legibilidad | Registro de cada acción del agente, visible para el vendedor dueño del lead |
| Monitoreo | Un evaluador automático revisa diariamente una muestra de conversaciones (tono, promesas sin respaldo) |
| Atribuibilidad | Cada acción queda asociada al vendedor responsable del lead |
| Interrupción | Botón para pausar el agente. Si se pausa a mitad de agendar, notifica al cliente que un vendedor lo contactará |

## Citas cortas

- Definición: "AI systems that can pursue complex goals with limited direct supervision" (resumen del documento).
- "Interruptibility (the ability to 'turn an agent off'), while crude, is a critical backstop" (sección 4.7).

## Notas de vigencia para el tutor

- Es un marco de 2023 anterior a los agentes masivos actuales. Sus siete prácticas siguen siendo una lista de verificación útil y aparecen, con otros nombres, en marcos más recientes (GOOG-SEC, OWASP-AG, ANT-CONTAIN).
- Para gobernanza organizacional (quién despliega, modifica, aprueba y audita), combinar con NIST-RMF (Govern, Map, Measure, Manage) y MS-CAF-AG.

## Preguntas de práctica

- P: ¿Cuáles son las tres partes del ciclo de vida de un agente según el documento?
  R: El desarrollador del modelo, el implementador del sistema (quien construye el agente sobre el modelo) y el usuario.
- P: Nombra las siete prácticas propuestas.
  R: Evaluar la idoneidad para la tarea, restringir el espacio de acción y exigir aprobación, definir comportamientos por defecto, hacer legible la actividad del agente, monitoreo automático, atribuibilidad, e interrumpibilidad y mantenimiento del control.
- P: ¿Cuál es el principal desafío de exigir aprobación humana?
  R: Que el humano tenga contexto suficiente para entender lo que aprueba y que no apruebe en forma automática por la cantidad de solicitudes (fatiga). Por eso conviene reservar las aprobaciones para acciones de alto riesgo.
- P: ¿Por qué la legibilidad del razonamiento no basta como garantía?
  R: Porque el razonamiento visible del modelo no siempre refleja lo que realmente guía su decisión, y además puede ser tan largo que un humano no alcanza a revisarlo. Hay que complementarlo con monitoreo y evals.
- P: ¿Qué significa diseñar una interrupción "ordenada" en un agente que agenda test drives?
  R: Que al detenerlo no deje procesos a medias sin aviso: el agente debe tener preparado un procedimiento de salida (p. ej. notificar al cliente que un vendedor lo contactará) y no debe poder impedir su propio apagado.

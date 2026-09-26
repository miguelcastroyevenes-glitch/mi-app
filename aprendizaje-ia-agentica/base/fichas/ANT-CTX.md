---
id: ANT-CTX
titulo: "Effective context engineering for AI agents"
autor: "Anthropic Applied AI (Prithvi Rajasekaran, Ethan Dixon, Carly Ryan, Jeremy Hadfield)"
anio: 2025
url: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
etapas: [1, 2]
semanas: [2, 5]
idioma_fuente: en
tipo: guía oficial (post de ingeniería)
verificado: 2026-09-26 (texto completo leído)
vigencia: "Publicado el 29-sep-2025. Los principios son estables; las funciones de producto que menciona (herramienta de memoria, limpieza de resultados de herramientas) pueden haber cambiado de nombre o de estado."
---

# ANT-CTX · Effective context engineering for AI agents (Anthropic, 2025)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

El post plantea que construir con LLMs ya no consiste tanto en "encontrar las palabras correctas" como en decidir **qué configuración de contexto** hace más probable el comportamiento deseado. El contexto es todo lo que entra al modelo en cada paso: instrucciones de sistema, herramientas, ejemplos, historial, datos externos y resultados de MCP. Como la atención del modelo es un recurso finito (con más tokens, peor recuerda: *context rot*), el objetivo es encontrar el conjunto más pequeño de tokens de alta señal que maximice el resultado. El texto recorre cómo lograrlo en el prompt de sistema, en las herramientas, en los ejemplos y en la recuperación "justo a tiempo", y cómo sostener tareas largas con compactación, notas estructuradas y subagentes.

## Ideas clave

1. **De prompt engineering a context engineering.** El prompt es una pieza. En un agente que corre en loop, el contexto se reconstruye en cada vuelta, así que la curaduría pasa a ser iterativa.
2. **El contexto es finito y rinde menos a medida que crece.** Los modelos tienen un "presupuesto de atención" que cada token consume. La degradación es gradual, no un precipicio, pero existe en todos los modelos.
3. **Prompt de sistema a la "altura correcta".** Hay que evitar dos extremos: la lógica rígida tipo *if-else* codificada en el prompt, que es frágil, y las guías vagas que suponen contexto compartido. Conviene ordenarlo en secciones (antecedentes, instrucciones, guía de herramientas, formato de salida). Mínimo no significa corto.
4. **Herramientas.** Deben ser autocontenidas, robustas y claras, y devolver información eficiente en tokens. Un error frecuente es tener demasiadas herramientas o herramientas que se traslapan: si un ingeniero no sabe cuál usar, el agente tampoco.
5. **Ejemplos.** Pocos, diversos y canónicos, en vez de una lista interminable de casos borde.
6. **Recuperación "justo a tiempo".** En vez de precargar todo, el agente guarda referencias livianas (rutas, consultas, links) y trae los datos con herramientas cuando los necesita. La estructura (nombres de carpetas, fechas) también es señal. La estrategia híbrida carga algo al inicio y explora el resto; Claude Code, por ejemplo, carga CLAUDE.md y usa glob/grep para lo demás.
7. **Tareas de largo aliento: tres técnicas.**
   - *Compactación:* resumir la conversación cuando se acerca al límite y seguir con un contexto nuevo. Es un arte: si se comprime demasiado, se pierden detalles que después resultan críticos.
   - *Notas estructuradas (memoria agéntica):* el agente escribe notas fuera del contexto (un NOTES.md, una lista de pendientes) y las relee.
   - *Subagentes:* cada uno explora con su propio contexto limpio y devuelve un resumen condensado (del orden de 1.000–2.000 tokens) al agente principal.
8. **Consejo de fondo:** "hacer lo más simple que funcione". Con modelos mejores, hace falta menos ingeniería prescriptiva.

## Conceptos y definiciones

- **Contexto:** el conjunto de tokens incluidos al muestrear el modelo.
- **Context engineering:** estrategias para curar y mantener el conjunto óptimo de tokens durante la inferencia, incluyendo todo lo que no es el prompt.
- **Context rot:** caída en la capacidad de recordar información a medida que crece el contexto.
- **Presupuesto de atención:** la capacidad finita del modelo para relacionar tokens; cada token nuevo la consume.
- **Divulgación progresiva:** descubrir contexto por capas a medida que se explora.
- **Compactación:** resumir y reiniciar el contexto conservando decisiones, pendientes y detalles clave.
- **Definición de agente usada:** LLMs que usan herramientas de forma autónoma en un loop.

## Errores comunes

- "Meter todo por si acaso": llenar el contexto con el catálogo completo, todo el historial y todas las políticas. Empeora la precisión y sube el costo.
- Codificar reglas de negocio como un árbol de *if-else* en el prompt, en vez de dar heurísticas claras y ejemplos.
- Tener herramientas ambiguas o duplicadas (dos formas de "buscar cliente").
- Compactar de forma agresiva y perder una restricción importante del cliente.
- Esperar que ventanas más grandes resuelvan el problema. La contaminación de contexto seguirá existiendo.

## Ejemplo aplicado: agente de seguimiento de clientes

Un agente que prepara el llamado de seguimiento no debería cargar las 2.000 fichas de clientes del mes. Conviene diseñarlo así:

- **Prompt de sistema breve y por secciones:** objetivo del llamado, política de descuentos resumida y formato de salida (guion de 5 líneas).
- **Recuperación justo a tiempo:** una herramienta `buscar_cliente(rut)` que devuelve solo lo relevante (modelo cotizado, fecha de la última visita, estado del crédito, última observación).
- **Notas estructuradas:** un archivo de "pendientes del día" que el agente actualiza después de cada cliente, para no depender del historial completo.
- **Subagentes (si escala):** uno revisa el stock compatible y otro la simulación de crédito; cada uno devuelve un resumen corto al agente principal.

## Citas cortas

- "find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome." (conclusión)
- "If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better." (sección de herramientas)

## Notas de vigencia para el tutor

- Esta ficha cubre el tema "prompt → context engineering" de la semana 2. La malla menciona además *specification engineering*: esta fuente no lo define, así que el tutor no debe atribuírselo.
- La relación entre compactación, notas y subagentes se retoma en ANT-MAS (semana 11).

## Preguntas de práctica

- P: ¿En qué se diferencia context engineering de prompt engineering?
  R: El prompt engineering se enfoca en redactar y ordenar instrucciones (sobre todo el prompt de sistema). El context engineering gestiona todo lo que entra al modelo en cada paso (instrucciones, herramientas, ejemplos, historial, datos externos) y es iterativo, porque en un agente el contexto se vuelve a curar en cada vuelta del loop.
- P: ¿Qué es el context rot y qué consecuencia práctica tiene?
  R: Es la pérdida de precisión para recordar información a medida que crece el contexto. En la práctica, el contexto es un recurso finito con rendimientos decrecientes, y conviene incluir solo información de alta señal.
- P: ¿Qué significa escribir el prompt de sistema a la "altura correcta"?
  R: Ni lógica rígida tipo if-else (frágil y difícil de mantener) ni guías vagas que suponen contexto compartido. Hay que ser lo bastante específico para guiar y lo bastante flexible para dar heurísticas.
- P: Nombra las tres técnicas para tareas largas y un caso de uso para cada una.
  R: Compactación (conversaciones largas con mucho ida y vuelta), notas estructuradas o memoria agéntica (trabajo iterativo con hitos claros) y arquitecturas de subagentes (investigación compleja donde conviene explorar en paralelo).
- P: ¿Qué es la recuperación "justo a tiempo" y cuál es su costo?
  R: Guardar referencias livianas (rutas, consultas, links) y traer los datos con herramientas cuando se necesitan, en vez de precargarlo todo. Su costo es que es más lenta que tener los datos ya cargados, y requiere buenas herramientas y heurísticas para que el agente no pierda tiempo en callejones sin salida.

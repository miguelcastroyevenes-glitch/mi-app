---
id: ANT-TOOLS
titulo: "Writing effective tools for AI agents — using AI agents"
autor: "Anthropic (Ken Aizawa y colaboradores)"
anio: 2025
url: https://www.anthropic.com/engineering/writing-tools-for-agents
etapas: [3]
semanas: [8, 9, 10]
idioma_fuente: en
tipo: guía oficial (post de ingeniería)
verificado: 2026-09-26 (texto completo leído)
vigencia: "Publicado el 11-sep-2025. Los principios son estables. Detalles como el límite de 25.000 tokens por respuesta en Claude Code o la conexión de MCP locales pueden haber cambiado."
---

# ANT-TOOLS · Writing effective tools for AI agents (Anthropic, 2025)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Las herramientas son un tipo nuevo de software: un **contrato entre sistemas deterministas y un agente no determinista**, que a veces decide no usarlas, las usa mal o las malinterpreta. Por eso no hay que diseñarlas como APIs para otros programadores, sino **para agentes**. El post propone un proceso (prototipar, evaluar con tareas realistas y mejorar con ayuda del propio agente analizando transcripciones) y cinco principios: elegir bien qué herramientas construir, usar *namespacing*, devolver contexto significativo, cuidar la eficiencia en tokens y escribir las descripciones con el mismo cuidado que un prompt.

## Ideas clave

1. **Prototipar y probar en la práctica.** Se envuelven las herramientas en un servidor MCP local y se prueban en Claude Code o Claude Desktop. Para que Claude escriba las herramientas, conviene darle documentación del SDK o API (p. ej. archivos `llms.txt`).
2. **Evaluar con tareas reales y exigentes.** Hay que evitar entornos "de juguete". Una tarea fuerte requiere varias llamadas (p. ej. "prepara una oferta de retención para la clienta X: por qué se va, qué oferta sirve y qué riesgos hay"). Cada tarea lleva una respuesta verificable, pero sin un verificador tan estricto que rechace respuestas correctas por formato.
3. **Medir más que la precisión:** tiempo por llamada, número de llamadas, tokens consumidos y errores de herramienta. Muchas llamadas redundantes piden ajustar la paginación; muchos errores de parámetros piden mejores descripciones.
4. **Leer las transcripciones.** Lo que el agente omite suele importar más que lo que dice. Claude puede analizar las transcripciones y refactorizar las herramientas. Se usan conjuntos de prueba separados (*held-out*) para no sobreajustar.
5. **Principio 1: menos es más.** No hay que envolver cada endpoint de una API. Conviene consolidar en herramientas de alto impacto: `search_contacts` en vez de `list_contacts`, `schedule_event` en vez de tres herramientas, `get_customer_context` en vez de `get_customer_by_id` + `list_transactions` + `list_notes`.
6. **Principio 2: namespacing.** Agrupar con prefijos por servicio o recurso (`asana_search`, `jira_search`) para que el agente elija bien entre muchas herramientas.
7. **Principio 3: devolver contexto significativo.** Nombres legibles en vez de UUIDs crípticos; resolver IDs a lenguaje natural reduce las alucinaciones. Se puede ofrecer un parámetro `response_format` (concise/detailed).
8. **Principio 4: eficiencia en tokens.** Paginación, filtros, rangos y truncado con valores por defecto razonables. Si se trunca o hay error, el mensaje debe decir qué hacer (errores accionables, no códigos opacos).
9. **Principio 5: describir la herramienta como a un empleado nuevo.** Explicitar formatos, términos y relaciones, y nombrar parámetros sin ambigüedad (`user_id`, no `user`). Pequeños ajustes en las descripciones producen mejoras grandes. En MCP, las anotaciones indican si una herramienta es destructiva o tiene acceso abierto.

## Conceptos y definiciones

- **Herramienta (tool):** función expuesta al agente con nombre, descripción y esquema de entrada.
- **Affordance:** lo que el agente "percibe" que puede hacer con una herramienta.
- **Namespacing:** prefijos que agrupan herramientas por servicio o recurso.
- **Consolidación:** una herramienta que resuelve un flujo frecuente de varios pasos.
- **response_format:** parámetro que controla el nivel de detalle de la respuesta.
- **Error accionable:** mensaje de error que indica cómo corregir la llamada.
- **Held-out test set:** tareas reservadas para medir sin sobreajustar.

## Errores comunes

- Envolver 1:1 cada endpoint del CRM. El agente se ahoga en opciones y en datos irrelevantes.
- Herramientas que devuelven todo (p. ej. las 5.000 cotizaciones del año) y consumen el contexto.
- IDs crípticos en las respuestas, con los que el agente se equivoca o inventa.
- Errores tipo "400 Bad Request" sin explicar qué parámetro falló.
- Evaluar con tareas triviales que no se parecen al trabajo real.
- Exigir en la eval un camino exacto de herramientas, cuando hay varias rutas válidas.

## Ejemplo aplicado: herramientas del Tool-Using Agent (semana 10)

En vez de exponer los endpoints del CRM tal cual:

| En lugar de… | Diseñar… |
|---|---|
| `get_lead`, `list_quotes`, `list_notes`, `get_credit` | `crm_contexto_cliente(rut, response_format)`, que devuelve modelo cotizado, etapa, crédito y última nota en lenguaje claro |
| `list_calendar`, `create_event` | `agenda_programar_test_drive(rut, modelo, preferencia_horaria)`, que busca disponibilidad y agenda |
| `list_stock` | `stock_buscar(modelo, version, color)`, paginado, que devuelve máximo 10 unidades con VIN abreviado y ubicación |

Error accionable de ejemplo: "No encontré el RUT 12.345.678-K. Verifica el dígito verificador o busca por nombre con crm_buscar_cliente(nombre)."

Eval: 20 tareas reales ("agenda test drive del 3008 para el cliente que cotizó ayer y avísale por correo"), midiendo si la tarea se cumple, cuántas llamadas hizo y cuántos tokens usó.

## Citas cortas

- "Tools are a new kind of software which reflects a contract between deterministic systems and non-deterministic agents." (sección "What is a tool?")
- "More tools don't always lead to better outcomes." (sección "Choosing the right tools for agents")

## Notas de vigencia para el tutor

- Se conecta con ANT-BEA (apéndice ACI/poka-yoke), MCP-ARCH (cómo se exponen las herramientas) y ANT-CEMCP (ejecutar código para ahorrar tokens cuando hay muchas herramientas).
- Miguel ya construye skills y pipelines: esta ficha es la guía para revisar sus herramientas actuales.

## Preguntas de práctica

- P: ¿Por qué Anthropic dice que las herramientas son "un nuevo tipo de software"?
  R: Porque son un contrato entre sistemas deterministas y un agente no determinista, que puede no usarlas, usarlas mal o malinterpretarlas. Hay que diseñarlas para las capacidades y limitaciones del agente, no como APIs para programadores.
- P: ¿Por qué es mejor `search_contacts` que `list_contacts` para un agente?
  R: Porque el agente tiene contexto limitado. Una lista completa lo obliga a leer todo token a token (búsqueda por fuerza bruta), mientras que una búsqueda devuelve solo lo relevante y ahorra contexto.
- P: ¿Qué es el namespacing y qué problema resuelve?
  R: Agrupar herramientas con prefijos por servicio o recurso (p. ej. `crm_...`, `agenda_...`). Evita que el agente se confunda entre muchas herramientas con funciones parecidas y lo ayuda a elegir la correcta.
- P: ¿Cómo debería ser un buen mensaje de error de una herramienta?
  R: Específico y accionable: indicar qué falló y cómo corregirlo (p. ej. el formato esperado o una herramienta alternativa), en vez de códigos opacos o trazas de error.
- P: Además de la precisión, ¿qué métricas conviene recolectar al evaluar herramientas?
  R: Tiempo de ejecución por llamada y por tarea, número total de llamadas, consumo de tokens y errores de herramienta. Revelan redundancias, problemas de paginación y descripciones confusas.

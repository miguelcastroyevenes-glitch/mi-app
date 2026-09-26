---
id: ANT-MAS
titulo: "How we built our multi-agent research system"
autor: "Anthropic (Jeremy Hadfield, Barry Zhang, Kenneth Lien, Florian Scholz, Jeremy Fox, Daniel Ford)"
anio: 2025
url: https://www.anthropic.com/engineering/multi-agent-research-system
etapas: [4]
semanas: [11, 12, 14]
idioma_fuente: en
tipo: guía oficial (post de ingeniería, caso real)
verificado: 2026-09-26 (texto completo leído)
vigencia: "Publicado el 13-jun-2025 con modelos Claude 4 (Opus 4 como líder, Sonnet 4 como subagentes). Las cifras de desempeño y costo son de ese sistema y momento; las lecciones de diseño son vigentes."
---

# ANT-MAS · Cómo Anthropic construyó su sistema multi-agente de investigación (2025)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Es el caso más completo y honesto disponible sobre llevar un sistema multi-agente a producción: la función Research de Claude. Usa un patrón **orquestador-trabajadores**: un agente líder planifica, crea subagentes que buscan en paralelo con su propio contexto, sintetiza y, al final, un agente de citas atribuye cada afirmación a su fuente. El post explica **por qué funciona** (más tokens útiles en paralelo), **cuánto cuesta** (mucho más que un chat), **cuándo no conviene** (tareas con mucha dependencia entre partes) y cómo lo mejoraron con prompts, herramientas, evaluaciones y prácticas de ingeniería para sistemas con estado.

## Ideas clave

1. **Por qué multi-agente.** La investigación es abierta y dependiente del camino: no se pueden fijar los pasos. Los subagentes "comprimen" información en paralelo, cada uno con su propia ventana de contexto, y separan responsabilidades.
2. **Resultado.** En su eval interna, el sistema (Opus 4 líder + Sonnet 4 subagentes) superó en 90,2% al agente único con Opus 4, sobre todo en consultas "a lo ancho" (muchas direcciones independientes).
3. **El factor principal es el gasto de tokens.** En BrowseComp, tres factores explicaron 95% de la varianza: el uso de tokens por sí solo explicó 80%, y el resto lo explicaron el número de llamadas a herramientas y el modelo elegido.
4. **Costo.** Los agentes usan unas 4× más tokens que un chat, y los sistemas multi-agente unas 15×. Solo se justifican cuando el valor de la tarea paga ese costo.
5. **Cuándo NO conviene.** Cuando todos los agentes necesitan el mismo contexto o hay muchas dependencias entre ellos. La mayoría de las tareas de programación, por ejemplo, son menos paralelizables.
6. **Lecciones de prompting:**
   - "Piensa como tus agentes": simular y observar paso a paso.
   - **Enseñar al orquestador a delegar:** cada subagente necesita objetivo, formato de salida, herramientas y fuentes sugeridas, y límites claros. Con instrucciones vagas se duplica el trabajo.
   - **Escalar el esfuerzo a la complejidad:** 1 agente y 3–10 llamadas para un dato simple; 2–4 subagentes para comparaciones; más de 10 para investigación compleja.
   - Diseñar bien las herramientas y dar heurísticas para elegirlas.
   - Dejar que los agentes mejoren sus propios prompts y herramientas: un agente que reescribía descripciones de herramientas redujo 40% el tiempo de las tareas.
   - Empezar amplio y luego acotar; usar el pensamiento extendido como borrador.
   - Paralelizar: 3–5 subagentes en paralelo, cada uno con 3 o más herramientas en paralelo, redujo hasta 90% el tiempo en consultas complejas.
7. **Evaluación.** Empezar de inmediato con unas 20 consultas reales. Un solo juez LLM con rúbrica (precisión factual, precisión de citas, completitud, calidad de fuentes, eficiencia de herramientas) resultó lo más consistente. Las pruebas humanas detectaron sesgos, como preferir granjas de contenido SEO sobre fuentes académicas. Si el agente modifica estado, conviene evaluar el **estado final**.
8. **Producción.** Los errores se acumulan: hay que poder **reanudar** desde donde falló, con reintentos y checkpoints. Se necesita trazabilidad completa para depurar sin leer el contenido privado. Los despliegues se hacen por etapas (*rainbow deployments*), porque hay agentes corriendo a mitad de proceso. La ejecución sincrónica de subagentes simplifica, pero crea cuellos de botella.
9. **Tips del apéndice.** Resumir fases y guardar en memoria externa en conversaciones largas. Que los subagentes escriban sus resultados en archivos y pasen solo referencias, para evitar el "teléfono roto".

## Conceptos y definiciones

- **Sistema multi-agente:** varios agentes (LLMs usando herramientas en loop) que trabajan juntos.
- **Agente líder / orquestador:** planifica, delega en subagentes y sintetiza.
- **Subagente:** agente con contexto propio para una subtarea, que devuelve un resumen.
- **Compresión:** destilar mucha información en pocos tokens relevantes.
- **Escalamiento de esfuerzo:** reglas explícitas de cuántos agentes y llamadas usar según la dificultad.
- **Evaluación de estado final:** juzgar si el resultado final es correcto, no si se siguió un camino exacto.
- **Rainbow deployment:** migrar tráfico gradualmente manteniendo versiones vieja y nueva a la vez.

## Errores comunes

- Usar multi-agente "porque suena avanzado", sin que la tarea sea paralelizable ni lo bastante valiosa para pagar unas 15× tokens.
- Delegar con instrucciones de una línea ("investiga X"), lo que genera trabajo duplicado y vacíos.
- No poner límites de esfuerzo; los primeros prototipos llegaron a crear 50 subagentes para consultas simples.
- Postergar las evals hasta tener cientos de casos.
- Reiniciar desde cero ante cada error, en vez de reanudar desde un checkpoint.

## Ejemplo aplicado: AI Sales Team (proyecto de la semana 14)

- **Orquestador:** recibe "prepara la semana comercial" y crea subagentes:
  1. Investigador de cartera: leads activos sin contacto en 7 días.
  2. Analista de stock: unidades que calzan con cada lead.
  3. Analista de crédito: estado de las solicitudes.
- Cada subagente escribe su resultado en un archivo y devuelve una referencia más un resumen de pocas líneas.
- **Verificador:** chequea con el CRM que las recomendaciones no contradigan datos reales antes de pasarlas al jefe de local.
- **Economía:** si el sistema usa unas 15× los tokens de un chat, conviene calcular el costo por semana comercial preparada y compararlo con las horas que ahorra al equipo. Si no paga, basta un solo agente con buenas herramientas.

## Citas cortas

- "Multi-agent systems work mainly because they help spend enough tokens to solve the problem." (sección "Benefits")
- "When building AI agents, the last mile often becomes most of the journey." (conclusión)

## Notas de vigencia para el tutor

- Contrastar con COG-DBMA ("Don't Build Multi-Agents"), que advierte sobre la fragmentación del contexto, y con MAST (taxonomía de fallas multi-agente).
- Patrones formales de orquestación: MS-PAT (en español). Costos actuales: ANT-PRICE.

## Preguntas de práctica

- P: ¿Qué patrón usa el sistema Research de Anthropic y cómo fluye una consulta?
  R: Orquestador-trabajadores. El agente líder analiza la consulta, planifica (y guarda el plan en memoria), crea subagentes que buscan en paralelo, sintetiza sus resultados, decide si hace falta más investigación y al final un agente de citas atribuye las afirmaciones a sus fuentes.
- P: ¿Qué factor explicó la mayor parte del desempeño en BrowseComp y qué implica?
  R: El uso de tokens (80% de la varianza). Implica que el multi-agente funciona principalmente porque permite gastar suficientes tokens en paralelo, cada subagente con su propio contexto.
- P: ¿Cuánto más cuestan en tokens los agentes y los sistemas multi-agente frente a un chat, y qué regla de negocio se desprende?
  R: Unas 4× los agentes y unas 15× los multi-agente. Solo conviene usarlos en tareas cuyo valor pague ese costo.
- P: ¿Qué debe incluir una buena instrucción de delegación a un subagente?
  R: Un objetivo claro, el formato de salida esperado, guía sobre qué herramientas y fuentes usar, y límites claros de la tarea, para evitar trabajo duplicado o vacíos.
- P: ¿Por qué el post recomienda evaluar el estado final en agentes que modifican datos?
  R: Porque los agentes pueden llegar al mismo resultado correcto por caminos distintos. Exigir un camino específico es frágil; lo importante es que el estado final (p. ej. la agenda o el CRM) quede correcto, verificando checkpoints clave si el flujo es largo.

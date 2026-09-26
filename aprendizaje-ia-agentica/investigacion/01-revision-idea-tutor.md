# Revisión crítica: ¿un agente tutor para la malla de IA Agéntica?

*Agente 1 de 4, crítico de la idea. Revisión del 26-sep-2026. Fuentes verificadas al final.*

## 0. En corto

- **Veredicto: sí, con condiciones.** Un tutor IA **bien diseñado** enseña más que una buena clase; uno **sin guardas** es una muleta: rindes mejor con la IA, peor sin ella, y sientes que aprendes.
- El riesgo acá no es que Miguel no sepa construir (ya construye), sino que siga construyendo **sin poder explicar, depurar ni evaluar** lo que hace.
- La malla es sólida en contenido, pero **le sobran horas, mete evals y seguridad tarde y se reparte en demasiadas plataformas**.
- El tutor debe ser mitad código (calendario, estado, aprobación) y mitad LLM (explicar, preguntar, corregir con rúbrica).

## 1. ¿Es buena idea? Lo que dice la evidencia

**A favor, con letra chica.** Kestin et al. (Harvard, *Scientific Reports*, 2025) hicieron un ensayo aleatorizado con 194 estudiantes de física. Con el tutor IA aprendieron más, y en menos tiempo, que en una clase de aprendizaje activo (efecto de ~0,63 DE; mediana de 49 min contra 60). Pero ese tutor tenía tres cosas que un chat genérico no tiene:
- **Soluciones paso a paso escritas por expertos dentro del prompt**, para evitar alucinaciones.
- La instrucción explícita de **no regalar la solución completa**.
- Respuestas breves, para no sobrecargar al estudiante.

Los autores advierten: contenido introductorio, visto por primera vez, dos semanas; no reemplaza la clase.

**En contra, cuando no hay diseño.**
- **Bastani et al. (*PNAS*, 2025).** Unos 1.000 escolares en Turquía. GPT-4 sin guardas subió 48% las notas en la práctica, pero **bajó 17% el examen sin IA**. La versión "tutor" (pistas diseñadas por profesores, sin dar respuestas) subió 127% en la práctica y **empató** con el grupo de control en el examen. Lo más grave: **los alumnos no percibieron que aprendían menos**, y los del tutor creían que les había ido mejor.
- **Shen & Tamkin (Anthropic, ene-2026).** Ensayo aleatorizado con 52 desarrolladores que aprendían una librería nueva. Con IA sacaron 50% en el quiz de comprensión; sin IA, 67%. **La brecha más grande fue en depuración.** Quienes delegaban el código o le pedían a la IA que depurara quedaron bajo 40%. Quienes hacían preguntas conceptuales y resolvían los errores por su cuenta quedaron sobre 65%.
- **METR (jul-2025).** Desarrolladores expertos fueron 19% más lentos con IA y creían haber sido 20% más rápidos. La ilusión de competencia no es solo de estudiantes.
- **Khanmigo.** Oreopoulos & Low (Tennessee, 2024–26) encontraron que casi todos tenían acceso, pero lo usaban poco: lo consultaban un tercio de los días y solo en 17% de sus errores. No hubo ganancias atribuibles al chatbot.
- **Anthropic (abr-2025).** En un millón de conversaciones de universitarios, ~47% eran "directas": pedir la respuesta involucrándose lo mínimo.

**Lo que ya existe.** Claude tiene *Learning mode* (abr-2025) y Claude Code el estilo de salida *Learning* (deja `TODO(human)` para que uno escriba las piezas con decisiones de diseño); ChatGPT tiene *Study mode* (jul-2025). Sirven, pero **son instrucciones, no garantías**: la documentación de Claude Code dice que un estilo de salida no garantiza que algo pase siempre (para eso están los hooks). Y ninguno lleva el estado de un curso de 24 semanas.

**Conclusión.** La evidencia no dice "tutor IA = aprendes más". Dice: **respuestas ancladas + no regalar soluciones + evaluación sin IA = aprendes más; IA a secas = muleta con sensación de progreso.** Miguel aprendió construyendo con IA; lo probable es que hoy delegue el código y depure con asistencia, justo el patrón que peor sale en el estudio de Anthropic. El tutor vale si su función central es cortar ese patrón.

## 2. Riesgos concretos y cómo mitigarlos

| Riesgo | Cómo se vería acá | Mitigación (regla del tutor) |
|---|---|---|
| **Adulación (sycophancy)** | "¡Excelente diagrama!" a un diseño con huecos, o ceder si Miguel insiste. Sesgo documentado (Sharma et al., ICLR 2024); OpenAI revirtió una versión de GPT-4o por esto (abr-2025). | Rúbrica con evidencia citada; feedback parte por lo que falla; prohibido elogiar sin criterio. Un evaluador separado pone la nota. Si Miguel discrepa, se re-evalúa contra la rúbrica, no contra su insistencia. |
| **Alucinación o contenido vencido** | SDKs, MCP y APIs cambian cada pocos meses; el tutor "recuerda" una API que ya no existe. | Cada afirmación técnica cita ID de fuente y fecha; sin fuente, lo dice. Fuentes de APIs con más de 90 días se re-verifican. Claves de respuesta escritas y revisadas antes (como en Kestin). |
| **El tutor hace el trabajo** | Miguel pide "arréglalo" y el tutor lo arregla. | Pistas en 3 niveles; solución solo tras un intento propio registrado; después la re-explica o reescribe sin mirar. Labs con estilo *Learning* (`TODO(human)`). |
| **Ilusión de competencia** | Siente que avanza porque produce artefactos. | Cada etapa cierra con una prueba **sin IA** (quiz cerrado, bug-hunt cronometrado, explicar su código línea a línea). Se registra autoevaluación vs. nota real: la brecha es un indicador. |
| **Abandono** | En edX terminó solo 3–6% de los inscritos (Reich & Ruipérez-Valiente, *Science*, 2019); Khanmigo muestra que estar disponible no basta. Atención variable, necesita estructura externa, y jueves a domingo trabaja fuerte. | Sesiones de 25–45 min agendadas, con un objetivo y recordatorio proactivo; cierre con "siguiente paso + fecha". Tras 2 sesiones perdidas, el plan baja solo. |
| **Sobrecarga frente al trabajo** | Cierre de mes + fin de semana fuerte = 0 horas. | "Semana mínima" de 2 h (repaso + 1 micro-lab) cuenta como cumplida; una semana de consolidación cada 4. |
| **Dependencia de plataforma** | El curso vive en un chat o en una función que cambia sin aviso. | Estado en Markdown/JSON en un repo: el tutor es reemplazable. Labs en una plataforma principal y una de contraste. |
| **Datos sensibles** | Exports de ROMA, datos de clientes o credenciales en un repo **público**. La Ley 21.719 de datos personales rige desde el 1-dic-2026, en medio del curso. | Datos sintéticos o anonimizados; secretos en variables de entorno; progreso y evaluaciones en carpeta ignorada por git o repo privado. |

## 3. Revisión de la malla

### 3.1 Carga

8–10 h/semana × 24 = ~210 h. Con jueves a domingo copados y cierres de mes, lo realista es un **promedio de 5–6 h/semana**, muy variable. Así, la malla se cae entre la semana 3 y la 5 por acumulación, no por dificultad. Recomiendo dos cosas a la vez: estirar las 24 semanas de contenido a ~30 de calendario (ciclos 3 + 1 de consolidación) y recortar ~25% con test-outs.

Ojo con la UAI que la malla da como referencia local: lunes y **jueves** 18:30–21:45, del 1-oct al 17-dic-2026, $1.390.000. El jueves choca con su semana fuerte.

### 3.2 Qué sobra o se comprime

- **Etapa 1 (procesos, canvas, ROI/TCO) y buena parte de la Etapa 6 (unit economics, build vs. buy, pitch, 30/60/90).** Es su terreno (Ingeniería Comercial, MBA, equipo de ventas a cargo): test-out con entregable, no 24 + 48 horas.
- **Stack demasiado ancho** (OpenAI Agents API, Copilot Studio, LangGraph, Google ADK, Power Automate, n8n, Zapier, Make). Basta **una plataforma principal, la que ya usa (Claude: Agent SDK, skills, hooks, subagentes, MCP)**, más una de contraste (p. ej. Copilot Studio, si su empresa vive en M365/Outlook). La fila "Agent runtime" de la malla ni menciona el stack de Claude.
- **A2A y "AI Center of Excellence"**: a nivel conceptual, con 1–2 h basta.
- **Entregable de "20 oportunidades"**: mejor 10 priorizadas, y 3 de ellas con caso de negocio.

### 3.3 Qué falta (por haber aprendido haciendo con IA)

1. **Fluidez sin IA:** leer código, seguir un stack trace, depurar con logs, escribir un test. Es lo que más cae según Shen & Tamkin, y no está en la malla.
2. **Evals desde el día 1, no desde la semana 15.** Su "Contrato Maestro" ya es una especificación: conviértanla en golden cases para su pipeline de leads.
3. **Seguridad sobre lo que ya tiene.** Su rutina que lee Outlook y escribe en Notion es un vector clásico de *prompt injection* (un correo puede traer instrucciones). Más los secretos de la API de ROMA y los datos de clientes.
4. **Operar lo que ya está en producción:** la app de 4 vendedores necesita versionado, rollback y cómo saber que un cambio no rompió nada.
5. **SQL y modelado de datos** más que Python genérico.
6. **Costo real:** tokens y costo por corrida de sus propios pipelines.

### 3.4 Orden

- **Etapa 5 (evals y seguridad) antes que la 4 (multi-agente), o fundirlas.** Armar 3–5 agentes antes de saber medir uno es construir algo que no se puede evaluar. La guía de Anthropic que cita la malla recomienda "la solución más simple posible" y sumar complejidad solo cuando haga falta.
- **Evals y seguridad como hilo transversal:** cada etapa cierra con mini-suite de pruebas y análisis de amenazas.
- **Semana 0 de diagnóstico** con los test-outs.

### 3.5 Test-out: qué probablemente domina y qué probablemente le falta

| Candidato a test-out (prueba práctica **sin IA**, 30–45 min) | Probablemente le falta (confirmar en el diagnóstico) |
|---|---|
| Git/GitHub básico (repos, Pages) | Branches, PR, resolver un conflicto, revertir un cambio |
| JSON, HTTP/REST y autenticación de APIs (ya consume ROMA) | Manejo de errores, reintentos, idempotencia |
| Prompting y skills | Explicar por qué falla un prompt o una skill, y medirlo |
| Mapeo de procesos, ROI, caso de negocio | Evals formales, golden cases, métricas de agente |
| Workflow vs. agente (su pipeline es un workflow) | Leer y depurar código sin ayuda, tests, SQL con joins |

Regla: el test-out se gana con evidencia, no se autodeclara.

### 3.6 Referencias de la malla

Revisé los 17 links (26-sep-2026). **16 cargan y el título coincide** con lo citado (MIT, Berkeley, Cambridge, HEC, IE, UAI, Stanford, OpenAI ×2, Anthropic ×2, Microsoft ×2, Google GEAR, Udacity, Coursera/IBM). **Harvard Online** bloquea verificaciones automáticas, pero el curso existe (confirmado por búsqueda). Observaciones:
- "Building Effective AI Agents" apunta a una landing de resources.anthropic.com; el texto canónico y libre está en anthropic.com/engineering/building-effective-agents.
- Verifiqué existencia y título, **no** cada descripción del contenido (p. ej. que HEC cubra "harness engineering" o A2A): tratarlas como no verificadas.
- Faltan fuentes que sí le sirven: la documentación de Claude Code (hooks, skills, subagentes) y "Effective context engineering for AI agents" de Anthropic.

## 4. Arquitectura recomendada del tutor

**Principio: lo que tiene que pasar siempre lo hace el código; lo que requiere conversar lo hace el LLM.**

| Código (scripts y archivos) | LLM |
|---|---|
| Calendario y plan semanal, según la carga que Miguel declare | Explicar, con analogías de su negocio |
| Repetición espaciada (cola de tarjetas con fechas) | Preguntas socráticas y pistas escalonadas |
| Registro de avance (log append-only) | Corregir respuestas abiertas contra la rúbrica, citando evidencia |
| Criterios de aprobación, umbrales y gates de etapa | Generar variantes de ejercicios **desde la base de fuentes** |
| Test-outs y sus resultados | Detectar malentendidos y re-explicar |
| Recordatorios y re-planificación a la baja | Resumir la sesión para el log |

Repetición espaciada y práctica de recuperación no son adorno: Dunlosky et al. (2013) las califican como las técnicas de mayor utilidad, y Roediger & Karpicke (2006) muestran que testearse retiene más que releer.

**Dónde vive el estado.** En archivos versionados, no en la memoria del chat: `plan.yaml`, `progreso.json`, `tarjetas.json`, `bitacora/AAAA-Sxx.md`, `evidencias/`. Lo personal (evaluaciones, reflexiones) en repo privado o carpeta ignorada por git. En Claude Code, un hook de inicio carga el estado y "qué toca hoy" y uno de cierre exige el log. Una skill de claude.ai sirve de interfaz liviana (repasar desde el celular), pero la fuente de verdad es el repo.

**Anclaje a fuentes.** La base de fuentes (agente 2) trae ID, URL, fecha de verificación y confianza. El tutor cita el ID en cada afirmación técnica; si algo no está en la base, lo dice; y no evalúa con preguntas improvisadas, sino con un banco con clave revisada (la ve, no la muestra). Para contenido que cambia rápido, el ejercicio es "anda a la documentación oficial y verifica", que es la habilidad real.

**Evaluador separado.** Un subagente con contexto propio que recibe solo rúbrica, evidencia y clave, sin el historial amable de la conversación; un script suma los criterios. Reduce la adulación y es, de paso, el patrón evaluator-optimizer de la malla.

**Evidencia de dominio por etapa.**

| Etapa | Evidencia mínima |
|---|---|
| 1 | Memo de 1 página con el ROI de un caso real, y defensa de "cuándo NO usar un agente" frente a 3 casos |
| 2 | Leer la traza de un agente real (el propio tutor) y explicar cada paso del loop sin ayuda |
| 3 | Un servidor MCP o herramienta propia; explicar cada línea; bug-hunt de 30 min sin IA |
| 4–5 | Una suite de evals que **detecte** un bug que el tutor inyecta a propósito; un red-team de su rutina de correo; justificar con costo y latencia si el multi-agente vale la pena |
| 6 | Caso de negocio presentado a una persona real (su gerente), con el feedback anotado |

**El tutor como caso de estudio.** El tutor es un agente (contexto, herramientas, memoria, evaluación); úsenlo:
- **Etapa 2:** Miguel lee el system prompt y las trazas del tutor, y dibuja su arquitectura.
- **Etapa 3:** construye él mismo una pieza del tutor, por ejemplo el scheduler o un servidor MCP de progreso.
- **Etapa 4:** separa el tutor del evaluador.
- **Etapa 5:** escribe evals del tutor ("¿regala respuestas?", "¿adula?", "¿cita fuentes?") y lo ataca con prompt injection escondida en una fuente.
- **Etapa 6:** capstone natural: **un tutor de onboarding para sus vendedores** (productos, proceso comercial, objeciones) con caso de negocio. Reusa todo y resuelve un problema real del local.

## 5. Veredicto y reglas no negociables

**Veredicto: SÍ, con condiciones:** que el tutor corte el patrón de delegación en vez de facilitarlo; que aprobar exija evidencia sin IA; que estado y calendario sean código, no conversación; y que la carga se ajuste a su semana real. Si no, es un ChatGPT buena onda que le hará sentir que aprende.

**Las 10 reglas no negociables para el agente constructor**

1. **No regalar soluciones.** Pistas en 3 niveles. La solución llega solo tras un intento propio registrado, y después Miguel la re-explica o la reescribe sin mirar.
2. **La aprobación la decide el código.** Rúbrica con criterios y umbral. El LLM puntúa criterio por criterio con evidencia citada y un script decide aprobado o no aprobado. "Vi el contenido" no aprueba.
3. **Checkpoint sin IA en cada etapa.** Quiz cerrado, bug-hunt cronometrado o explicar su propio código línea a línea. Es gate, no opcional.
4. **Anclaje obligatorio.** Cada afirmación técnica cita el ID de la fuente y su fecha. Sin fuente, lo declara. Las fuentes de APIs con más de 90 días se re-verifican.
5. **Feedback calibrado y evaluador separado.** Primero lo que falla, cero elogio sin criterio, la nota no cambia por insistencia y la evaluación ocurre en un contexto aparte.
6. **Estado en archivos, no en el chat.** Plan, progreso, tarjetas y bitácora versionados y portables (Markdown/JSON). Hooks que cargan el estado al abrir y exigen el log al cerrar.
7. **Calendario, repetición espaciada y test-outs determinísticos.** El LLM no decide "qué toca hoy", y un test-out solo se gana con prueba.
8. **Estructura externa y retroalimentación rápida.** Sesiones agendadas de 25–45 min con un objetivo. Cada una cierra con una pregunta de recuperación y el siguiente paso con fecha. Recordatorio proactivo.
9. **Semana mínima y re-planificación sin castigo.** Una semana de 2 h cuenta como válida. Tras 2 sesiones perdidas el plan baja solo, y nunca se arrastra deuda a la semana siguiente.
10. **Datos y secretos fuera del repo público.** Labs con datos sintéticos o anonimizados, credenciales en variables de entorno y evaluaciones personales en privado.

## Fuentes (verificadas el 26-sep-2026)

**Evidencia sobre tutores con IA y aprendizaje**
- Kestin, G., Miller, K., Klales, A. et al. (2025). *AI tutoring outperforms in-class active learning: an RCT introducing a novel research-based design in an authentic educational setting.* Scientific Reports 15, 17458. https://www.nature.com/articles/s41598-025-97652-6 · texto libre: https://pmc.ncbi.nlm.nih.gov/articles/PMC12179260/
- Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., Mariman, R. (2025). *Generative AI without guardrails can harm learning: Evidence from high school mathematics.* PNAS 122(26). https://www.pnas.org/doi/10.1073/pnas.2422633122 · texto libre: https://pmc.ncbi.nlm.nih.gov/articles/PMC12232635/
- Shen, J. H., Tamkin, A. (2026). *How AI assistance impacts the formation of coding skills.* Anthropic. https://www.anthropic.com/research/AI-assistance-coding-skills · paper: https://arxiv.org/abs/2601.20245
- METR (2025). *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity.* https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/
- Estudio Khanmigo de Oreopoulos & Low, según la prensa (no leí el working paper original): Chalkbeat, 25-ago-2026, https://www.chalkbeat.org/2026/08/25/ai-tutoring-students-khanmigo-khan-academy-engagement-study/ · The 74, 1-sep-2026, https://www.the74million.org/article/ai-tutors-not-yet-a-replacement-for-humans-research-says/
- Anthropic (2025). *Anthropic Education Report: How university students use Claude.* https://www.anthropic.com/news/anthropic-education-report-how-university-students-use-claude
- Reich, J., Ruipérez-Valiente, J. A. (2019). *The MOOC pivot.* Science 363, 130–131. https://www.science.org/doi/10.1126/science.aav7958
- Roediger, H. L., Karpicke, J. D. (2006). *Test-enhanced learning.* Psychological Science 17, 249–255. https://journals.sagepub.com/doi/10.1111/j.1467-9280.2006.01693.x
- Dunlosky, J., Rawson, K., Marsh, E., Nathan, M., Willingham, D. (2013). *Improving Students' Learning With Effective Learning Techniques.* Psychological Science in the Public Interest 14(1), 4–58. https://pubmed.ncbi.nlm.nih.gov/26173288/

**Adulación (sycophancy)**
- Sharma, M. et al. (2024). *Towards Understanding Sycophancy in Language Models.* ICLR 2024. https://arxiv.org/abs/2310.13548
- OpenAI (2025). *Sycophancy in GPT-4o: What happened and what we're doing about it.* https://openai.com/index/sycophancy-in-gpt-4o/

**Modos de aprendizaje y herramientas**
- Anthropic (2-abr-2025). *Introducing Claude for Education* (Learning mode). https://www.anthropic.com/news/introducing-claude-for-education
- OpenAI (29-jul-2025). *Introducing study mode.* https://openai.com/index/chatgpt-study-mode/
- Claude Code Docs. *Output styles.* https://code.claude.com/docs/en/output-styles

**Arquitectura de agentes**
- Anthropic (19-dic-2024). *Building effective agents.* https://www.anthropic.com/engineering/building-effective-agents
- Anthropic (2025). *Effective context engineering for AI agents.* https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic (2026). *Demystifying evals for AI agents.* https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

**Contexto chileno**
- Biblioteca del Congreso Nacional. *Ley 21.719* (protección de datos personales; vigencia desde el 1-dic-2026). https://www.bcn.cl/leychile/navegar?idNorma=1209272
- UAI. *Certificado Profesional en Agentic AI* (fechas, horario y precio consultados el 26-sep-2026). https://www.uai.cl/postgrados/cursos/certificado-profesional-agentes-inteligentes-autonomos

# 02 · Base de conocimiento del tutor de IA Agéntica

> **Agente 2 de 4 — bibliotecario.** Catálogo verificado de fuentes por etapa, ruta mínima de lectura y recomendación sobre cómo pasarle los textos al tutor.
> Investigación y verificación de links realizadas el **26 de septiembre de 2026**. Todo está anclado en fuentes que existen; lo que no se pudo verificar quedó fuera.

**Archivos que acompañan este informe**

- `base/fuentes.json`: el catálogo completo en JSON (una fuente por objeto, con `id` estable).
- `base/fichas/<ID>.md`: 16 fichas de conocimiento, una por cada fuente núcleo, con 5 preguntas de práctica cada una.

---

## 1. Resumen en una mirada

| Indicador | Valor |
|---|---|
| Fuentes en el catálogo | **69** (todas verificadas el 26-sep-2026) |
| Fuentes núcleo (ruta mínima) | **16**, con ficha propia |
| Fuentes en español (o con versión en español) | 13 |
| Gratuitas | 64 · de pago o freemium: 5 |
| Con licencia abierta (pueden ir como archivo con atribución) | 14 |
| Fuentes por etapa principal | E1: 12 · E2: 14 · E3: 16 · E4: 9 · E5: 14 · E6: 4 (contando las que sirven a varias etapas: E1: 12 · E2: 16 · E3: 19 · E4: 16 · E5: 25 · E6: 12) |
| Tiempo estimado de la ruta mínima | ≈ 607 min (≈ 10.1 h) de lectura/video, repartidos en 24 semanas |

**Cinco hallazgos de vigencia que el tutor debe conocer desde el día 1**

1. **MCP cambió de fondo.** La especificación vigente es la **2026-07-28**: protocolo sin estado, sin handshake `initialize`, `server/discover` obligatorio, *sampling* y *logging* deprecados, y extensiones oficiales (Tasks, Skills over MCP, MCP Apps). Cursos y tutoriales de 2025 enseñan el modelo anterior.
2. **A2A llegó a v1.0.** v1.0.0 salió el 12-mar-2026 (con cambios incompatibles respecto de 0.3.x) y v1.0.1 el 28-may-2026. El proyecto está en la Linux Foundation.
3. **"Building Effective Agents" (dic-2024) ahora trae una nota.** Advierte que el panorama de herramientas cambió y remite a *Claude Managed Agents* (abr-2026). Los patrones siguen valiendo; las herramientas mencionadas, no necesariamente.
4. **Seguridad y evals se actualizaron en 2026.** OWASP publicó el **LLM Top 10 2026** (3-ago-2026) además del **Top 10 para aplicaciones agénticas** (dic-2025), y el FAQ de evals de Hamel Husain y Shreya Shankar se republicó el 18-sep-2026.
5. **Chile, datos personales.** La **Ley 21.719** entra en vigencia legal el **1-dic-2026**. El 1-sep-2026 el Gobierno ingresó un proyecto para postergarla al **1-dic-2027**; al 22-sep-2026 seguía en primer trámite en el Senado. El tutor debe presentar esto como "en trámite" y volver a verificarlo.

---

## 2. Ruta mínima (lecturas núcleo en orden)

Si Miguel solo lee estas 16 fuentes, cubre los conceptos de las 6 etapas. Cada una tiene ficha en `base/fichas/`. Las semanas corresponden a la malla de 24 semanas.

| # | ID | Fuente | Semana(s) | Qué cubre de la malla | Min. |
|---|---|---|---|---|---|
| 1 | [`KAR-LLM`](../base/fichas/KAR-LLM.md) | [\[1hr Talk\] Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g) — Andrej Karpathy, 2023 | 1 | LLM fundamentals: tokens, contexto, entrenamiento, alucinaciones, límites | 60 |
| 2 | [`ANT-BEA`](../base/fichas/ANT-BEA.md) | [Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents) — Anthropic (Erik S. y Barry Zhang), 2024 | 1, 2, 6 | De GenAI a Agentic AI; workflows vs. agentes; cuándo NO usar un agente; patrones (se relee en la sem. 6) | 25 |
| 3 | [`ANT-CTX`](../base/fichas/ANT-CTX.md) | [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic Applied AI (P. Rajasekaran, E. Dixon, C. Ryan, J. Hadfield), 2025 | 2, 5 | Prompt engineering → context engineering; memoria de trabajo del agente | 25 |
| 4 | [`MS-CAF-BIZ`](../base/fichas/MS-CAF-BIZ.md) | [Business plan for AI agents (Plan de negocio para agentes de IA) — Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai-agents/business-strategy-plan) — Microsoft Learn, 2026 | 3, 23 | AI Opportunity Canvas: valor × factibilidad × riesgo, métricas y compuertas (se relee en la sem. 23) | 20 |
| 5 | [`WENG-AGT`](../base/fichas/WENG-AGT.md) | [LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) — Lilian Weng (Lil'Log), 2023 | 4 | Agent loop y anatomía: planificación, memoria, herramientas | 45 |
| 6 | [`OAI-PGA`](../base/fichas/OAI-PGA.md) | [A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) — OpenAI, 2025 | 5, 6, 18 | Componentes, single vs. multi-agente, guardrails y human-in-the-loop (se relee en la sem. 18) | 45 |
| 7 | [`ANT-CR`](../base/fichas/ANT-CR.md) | [Contextual Retrieval in AI Systems](https://www.anthropic.com/engineering/contextual-retrieval) — Anthropic, 2024 | 5 | RAG, embeddings, vector stores, BM25 y reranking | 20 |
| 8 | [`ANT-TOOLS`](../base/fichas/ANT-TOOLS.md) | [Writing effective tools for AI agents — using AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents) — Anthropic (Ken Aizawa y colaboradores), 2025 | 8, 9, 10 | Diseño de herramientas: nombres, respuestas, errores, evaluación | 25 |
| 9 | [`MCP-ARCH`](../base/fichas/MCP-ARCH.md) | [Architecture overview — Model Context Protocol (versión 2026-07-28)](https://modelcontextprotocol.io/docs/learn/architecture) — Model Context Protocol (proyecto abierto), 2026 | 9, 10 | MCP: host/cliente/servidor, tools/resources/prompts, spec 2026-07-28 | 35 |
| 10 | [`ANT-MAS`](../base/fichas/ANT-MAS.md) | [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — Anthropic (J. Hadfield, B. Zhang, K. Lien, F. Scholz, J. Fox, D. Ford), 2025 | 11, 12, 14 | Orquestador + especialistas, subagentes, paralelización y economía (costo por tarea) | 30 |
| 11 | [`A2A-SPEC`](../base/fichas/A2A-SPEC.md) | [Agent2Agent (A2A) Protocol — especificación v1.0 y 'What is A2A'](https://a2a-protocol.org/latest/specification/) — A2A Project (Linux Foundation; creado por Google), 2026 | 13 | A2A e interoperabilidad entre agentes | 40 |
| 12 | [`ANT-EVAL`](../base/fichas/ANT-EVAL.md) | [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — Anthropic (M. Grace, J. Hadfield, R. Olivares, J. De Jonghe), 2026 | 15, 16 | Agent evals: tareas, graders, golden cases, pass@k / pass^k | 40 |
| 13 | [`HAM-FAQ`](../base/fichas/HAM-FAQ.md) | [AI Evals: Everything You Need to Know (FAQ)](https://hamel.dev/blog/posts/evals-faq/) — Hamel Husain y Shreya Shankar, 2026 | 16, 17 | Análisis de errores, evals binarias, juez LLM validado, CI vs. monitoreo | 90 |
| 14 | [`SW-TRIF`](../base/fichas/SW-TRIF.md) | [The lethal trifecta for AI agents: private data, untrusted content, and external communication](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) — Simon Willison, 2025 | 17 | Prompt injection, exfiltración de datos, permisos y abuso de herramientas | 12 |
| 15 | [`OAI-GOV`](../base/fichas/OAI-GOV.md) | [Practices for Governing Agentic AI Systems](https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf) — Yonadav Shavit, Sandhini Agarwal, Miles Brundage et al. (OpenAI), 2023 | 18, 19 | Gobernanza: aprobaciones, límites de autonomía, monitoreo, auditoría, interrupción | 60 |
| 16 | [`BVP-PRICE`](../base/fichas/BVP-PRICE.md) | [The AI pricing and monetization playbook](https://www.bvp.com/atlas/the-ai-pricing-and-monetization-playbook) — Bessemer Venture Partners (Atlas; B. Deeter, K. Bennett, S. Dholakia y equipo), 2026 | 21, 22 | Modelos de negocio de IA, pricing, unit economics y TCO | 35 |

**Semanas sin lectura núcleo nueva y cómo se cubren.** Son semanas de laboratorio o de repaso; el tutor usa las fichas ya vistas y los recursos prácticos del catálogo:

| Semana | Tema de la malla | Cobertura sugerida |
|---|---|---|
| 6 | Patrones y human-in-the-loop (entregable: diagrama del agente de ventas) | Releer ANT-BEA (patrones) y OAI-PGA (intervención humana); opcional LEVELS |
| 7 | Python, Git, JSON, errores | PY4E-ES, PROGIT-ES (en español), ANT-TOOLUSE (en español) |
| 10 | Tool-Using Agent (proyecto) | ANT-TOOLS + MCP-ARCH aplicados; opcional ANT-SKILLS, ANT-CEMCP, ANT-CU, ANT-SDK |
| 14 | AI Sales Team (proyecto) y economía de agentes | ANT-MAS (costos ≈15× tokens) + ANT-PRICE; opcional MS-WTI |
| 19 | Agent QA Lab (proyecto), confiabilidad | ANT-EVAL (hoja de ruta) + OAI-GOV (protocolo); opcional STRIPE-IDEM, ANT-CONTAIN, NIST-RMF |
| 20 | Descubrimiento y validación con clientes | MOMTEST (libro) y MOL-COI (adopción) |
| 23–24 | Roadmap, adopción, AI CoE, capstone | Releer MS-CAF-BIZ (compuertas y métricas) + MS-CAF-AG; opcional MITSMR-AE, MS-WTI, CL-PNIA |

**Por qué estas y no otras.** Se priorizaron fuentes primarias y vigentes que (a) se pudieron leer completas para escribir fichas fieles, (b) son gratuitas y (c) cubren un tema explícito de la malla. Por eso MIT SMR/BCG y McKinsey (texto completo tras registro o bloqueado a lectura automática) y los libros de pago quedaron en el catálogo, pero no en el núcleo.

---

## 3. Catálogo por etapa

Convenciones: ★ = núcleo (tiene ficha). "Min." es mi estimación de tiempo de lectura o video, no un dato de la fuente. En "Acceso", "© …: linkear" significa que se usa por link y con ficha propia, sin copiar el texto.

### Etapa 1 — Mentalidad agéntica + estrategia de negocio (semanas 1–3) · 12 fuentes

| ID | Fuente (autor, año) | Tipo · nivel · min | Idioma | Acceso / licencia | Semanas (otras etapas) | Por qué sirve a Miguel |
|---|---|---|---|---|---|---|
| ★ `ANT-BEA` | [Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents) — Anthropic (Erik S. y Barry Zhang), 2024 | guía oficial (post de ingeniería) · intro · 25 | en | Gratis · © Anthropic: linkear + ficha propia | 1, 2, 6 (también E2) | Texto canónico: workflow vs. agente, cuándo NO usar un agente y los 5 patrones que la malla pide en las etapas 1 y 2. |
| ★ `KAR-LLM` | [\[1hr Talk\] Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g) — Andrej Karpathy, 2023 | video · intro · 60 | en (subtítulos automáticos) | Gratis (YouTube) · © autor: linkear + ficha propia | 1 | Modelo mental sin matemáticas de qué es un LLM (pre-entrenamiento, ajuste, alucinaciones, herramientas, riesgos) para explicarle a su equipo por qué el modelo 'inventa'. |
| ★ `ANT-CTX` | [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic Applied AI (P. Rajasekaran, E. Dixon, C. Ryan, J. Hadfield), 2025 | guía oficial (post de ingeniería) · intermedio · 25 | en | Gratis · © Anthropic: linkear + ficha propia | 2, 5 (también E2) | Explica el salto 'prompt → context engineering' de la semana 2 y técnicas (compactación, notas, subagentes) que él ya ve en Claude Code. |
| ★ `MS-CAF-BIZ` | [Business plan for AI agents (Plan de negocio para agentes de IA) — Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai-agents/business-strategy-plan) — Microsoft Learn, 2026 | guía oficial · intro · 20 | en (versión es-es disponible) | Gratis · CC BY 4.0 (repos MicrosoftDocs): puede ir como archivo con atribución | 3, 23 (también E6) | Herramienta directa para el AI Opportunity Map: cuándo no usar agentes, puntaje impacto × factibilidad × deseabilidad y métricas como compuertas go/no-go. |
| `ANT-FLU` | [AI Fluency: Framework & Foundations](https://anthropic.skilljar.com/ai-fluency-framework-foundations) — Anthropic Academy (con Prof. Joseph Feller y Prof. Rick Dakan), 2025 | curso · intro · 180 | en | Gratis (registro) · © Anthropic: linkear | 1, 2 | Marco 4D (Delegación, Descripción, Discernimiento, Diligencia) útil para enseñar a su equipo de ventas a trabajar con IA, no solo a usarla. |
| `HBR-AGENTIC` | [What Is Agentic AI, and How Will It Change Work?](https://hbr.org/2024/12/what-is-agentic-ai-and-how-will-it-change-work) — Mark Purdy (Harvard Business Review), 2024 | artículo · intro · 10 | en | Freemium (HBR limita lecturas gratis) · © HBR: linkear | 1 | Lectura ejecutiva corta para alinear lenguaje con gerencia sobre qué cambia en el trabajo con agentes. |
| `KAR-DEEP` | [Deep Dive into LLMs like ChatGPT](https://www.youtube.com/watch?v=7xTGNNLPyMI) — Andrej Karpathy, 2025 | video · intermedio · 211 | en (subtítulos automáticos) | Gratis (YouTube) · © autor: linkear | 1, 2 | Versión larga (3 h 31 min) para cuando quiera el porqué de tokens, RLHF y alucinaciones; opcional y por capítulos. |
| `MOL-COI` | [Co-Intelligence: Living and Working with AI (ed. en español: Cointeligencia, Conecta, 2025)](https://www.penguinrandomhouse.com/books/741805/co-intelligence-by-ethan-mollick/) — Ethan Mollick, 2024 | libro · intro · 360 | en / es (traducción) | Pago · © Penguin Random House: solo ficha propia | 1, 20 (también E6) | Visión práctica de un profesor de Wharton sobre trabajar con la IA como compañero; buen puente entre su formación MBA y la práctica diaria. |
| `ANT-PE` | [Descripción general de la ingeniería de prompts (Claude Docs)](https://platform.claude.com/docs/es/build-with-claude/prompt-engineering/overview) — Anthropic, 2026 | documentación oficial · intro · 30 | es | Gratis · © Anthropic: linkear (documentación viva) | 2 | En español y sobre Claude, que ya usa a diario: ordena las técnicas de prompting antes de pasar a context engineering. |
| `ANT-PRICE` | [Pricing (Claude Platform Docs)](https://platform.claude.com/docs/en/about-claude/pricing) — Anthropic, 2026 | documentación oficial · intro · 10 | en | Gratis · © Anthropic: linkear (cambia seguido, no copiar precios) | 3, 14, 22 (también E4, E6) | Insumo del ROI/TCO: precio por millón de tokens, caching y batch; hay que recalcular cada vez que cambian modelos o precios. |
| `MCK-SEIZE` | [Seizing the agentic AI advantage](https://www.mckinsey.com/capabilities/quantumblack/our-insights/seizing-the-agentic-ai-advantage) — McKinsey & Company (QuantumBlack), 2025 | informe · intro · 40 | en | Gratis · © McKinsey: linkear | 3, 21 (también E6) | La 'paradoja de la IA generativa' (mucha adopción, poco impacto; casos verticales atascados en piloto) como argumento para rediseñar procesos y no solo sumar chatbots. |
| `MITSMR-AE` | [The Emerging Agentic Enterprise: How Leaders Must Navigate a New Age of AI](https://sloanreview.mit.edu/projects/the-emerging-agentic-enterprise-how-leaders-must-navigate-a-new-age-of-ai/) — MIT Sloan Management Review + BCG (Ransbotham, Kiron, Khodabandeh, Iyer, Das), 2025 | informe · intro · 45 | en | Gratis parcial (informe completo con registro) · © MIT SMR: linkear | 3, 23 (también E6) | Fuente de la idea 'herramienta vs. compañero de trabajo' que cita la malla (76% de ejecutivos ve la IA agéntica más como coworker que como herramienta). |

### Etapa 2 — Anatomía y arquitectura de agentes (semanas 4–6) · 14 fuentes

| ID | Fuente (autor, año) | Tipo · nivel · min | Idioma | Acceso / licencia | Semanas (otras etapas) | Por qué sirve a Miguel |
|---|---|---|---|---|---|---|
| ★ `WENG-AGT` | [LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) — Lilian Weng (Lil'Log), 2023 | post técnico (revisión) · intermedio · 45 | en | Gratis · © autora: linkear + ficha propia | 4 | La anatomía clásica del agente (planificación, memoria, herramientas) que la semana 4 necesita para 'leer' cualquier arquitectura. |
| ★ `ANT-CR` | [Contextual Retrieval in AI Systems](https://www.anthropic.com/engineering/contextual-retrieval) — Anthropic, 2024 | guía oficial (post de ingeniería) · intermedio · 20 | en | Gratis · © Anthropic: linkear + ficha propia | 5 | El mejor resumen corto de RAG (chunks, embeddings, BM25, reranking) con cifras; incluye cuándo NO hace falta RAG. |
| ★ `OAI-PGA` | [A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) — OpenAI, 2025 | guía oficial (PDF, 34 págs.) · intro · 45 | en | Gratis · © OpenAI: linkear + ficha propia | 5, 6, 18 (también E5) | Guía pensada para equipos de producto: cuándo construir un agente, sus 3 componentes, patrones manager/descentralizado, guardrails y cuándo escalar a un humano. |
| `ANT-TOOLUSE` | [Uso de herramientas con Claude (Tool use overview)](https://platform.claude.com/docs/es/agents-and-tools/tool-use/overview) — Anthropic, 2026 | documentación oficial · intermedio · 30 | es | Gratis · © Anthropic: linkear + ficha propia | 4, 7 (también E3) | En español: cómo se define una herramienta (nombre, descripción, input_schema) y el ciclo tool_use / tool_result con Claude. |
| `DLAI-AGENTIC` | [Agentic AI](https://www.deeplearning.ai/courses/agentic-ai/) — Andrew Ng (DeepLearning.AI), 2025 | curso · intermedio · 595 | en | Pago (membresía Pro de DeepLearning.AI) | 4, 5, 6, 12, 16 (también E4, E5) | Curso práctico en Python: reflexión, uso de herramientas, evals y análisis de errores, planificación y multi-agente. |
| `GOOG-AGENTS` | [Agents (whitepaper)](https://www.kaggle.com/whitepaper-agents) — Julia Wiesinger, Patrick Marlow, Vladimir Vuskovic (Google), 2024 | whitepaper · intro · 60 | en | Gratis (Kaggle) · © Google: linkear | 4 | La visión de Google (capas modelo, orquestación y herramientas); contraste útil frente a Anthropic y OpenAI. |
| `GOOG-INTRO` | [Introduction to Agents (whitepaper del 5-Day AI Agents Intensive)](https://www.kaggle.com/whitepaper-introduction-to-agents) — Alan Blount, Antonio Gulli, Shubham Saboo, Michael Zimmermann, Vladimir Vuskovic (Google), 2025 | whitepaper (54 págs.) · intermedio · 90 | en | Gratis (Kaggle) · © Google: linkear | 4, 15 (también E5) | Versión 2025 de Google: taxonomía de niveles de agentes y la disciplina 'Agent Ops' (KPIs, LM como juez, trazas OpenTelemetry). |
| `HUY-AGT` | [Agents](https://huyenchip.com/2025/01/07/agents.html) — Chip Huyen, 2025 | post (adaptado de su libro) · intermedio · 60 | en | Gratis · © autora: linkear | 4, 6 | Planificación, herramientas y modos de falla de agentes explicados gratis por la autora de 'AI Engineering'. |
| `MS-AIAB` | [AI Agents for Beginners (traducción al español)](https://github.com/microsoft/ai-agents-for-beginners/blob/main/translations/es/README.md) — Microsoft, 2025 | curso (18 lecciones) · intro · 900 | es | Gratis · MIT: puede ir como archivo con atribución | 4, 9, 12, 17 (también E3, E4, E5) | 18 lecciones en español (patrones, RAG agéntico, MCP/A2A, memoria, seguridad, producción) con código; buen complemento práctico. |
| `REACT` | [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) — Shunyu Yao et al., 2022 | paper · avanzado · 60 | en | Gratis · CC BY 4.0: puede ir como archivo con atribución | 4 | Origen del ciclo pensar → actuar → observar que usa todo agente moderno; basta con la introducción y los ejemplos. |
| `HF-AGENTS` | [Curso de Agentes IA de Hugging Face](https://huggingface.co/learn/agents-course/es/unit0/introduction) — Hugging Face, 2025 | curso · intermedio · 1200 | es / en | Gratis · Apache-2.0 (repo): puede ir como archivo con atribución | 5, 6, 10 (también E3) | Curso gratuito con versión en español y certificado; practica con smolagents, LangGraph y LlamaIndex. |
| `HUY-AIE` | [AI Engineering: Building Applications with Foundation Models (repositorio de recursos del libro)](https://github.com/chiphuyen/aie-book) — Chip Huyen (O'Reilly), 2025 | libro · intermedio · 1200 | en | Pago (libro) · repo de recursos gratis · © O'Reilly: solo ficha propia | 5, 15 (también E5) | Libro de consulta (evaluación, prompting, RAG, agentes, finetuning) para cuando una semana le quede corta. |
| `LEVELS` | [Levels of Autonomy for AI Agents](https://arxiv.org/abs/2506.12469) — K. J. Kevin Feng, David W. McDonald, Amy X. Zhang, 2025 | paper · intermedio · 45 | en | Gratis · CC BY 4.0: puede ir como archivo con atribución | 6, 18 (también E5) | Cinco niveles de autonomía según el rol del usuario (operador, colaborador, consultor, aprobador, observador): vocabulario para decidir cuánta autonomía dar al agente. |
| `LG-WFA` | [Workflows and agents (documentación de LangGraph)](https://docs.langchain.com/oss/python/langgraph/workflows-agents) — LangChain, 2026 | documentación oficial · intermedio · 30 | en | Gratis · © LangChain: linkear | 6, 11 (también E4) | Los patrones de 'Building Effective Agents' implementados en LangGraph, el orquestador que nombra la malla. |

*También sirven en esta etapa (listadas en otra):* ★ `ANT-BEA` (sem. 6), ★ `ANT-CTX` (sem. 5).

### Etapa 3 — Construcción: APIs, datos, herramientas y MCP (semanas 7–10) · 16 fuentes

| ID | Fuente (autor, año) | Tipo · nivel · min | Idioma | Acceso / licencia | Semanas (otras etapas) | Por qué sirve a Miguel |
|---|---|---|---|---|---|---|
| ★ `ANT-TOOLS` | [Writing effective tools for AI agents — using AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents) — Anthropic (Ken Aizawa y colaboradores), 2025 | guía oficial (post de ingeniería) · intermedio · 25 | en | Gratis · © Anthropic: linkear + ficha propia | 8, 9, 10 | Cubre el tema 'diseño de herramientas' de la malla (nombres, respuestas, errores, evaluación) con reglas aplicables a sus propias skills y MCP. |
| ★ `MCP-ARCH` | [Architecture overview — Model Context Protocol (versión 2026-07-28)](https://modelcontextprotocol.io/docs/learn/architecture) — Model Context Protocol (proyecto abierto), 2026 | documentación oficial · intermedio · 35 | en | Gratis · MIT (repo): puede ir como archivo con atribución | 9, 10 | Explica host, cliente, servidor y primitivas (tools, resources, prompts) en la versión vigente del protocolo, que ya cambió respecto de 2025. |
| `PROGIT-ES` | [Pro Git, 2.ª edición (en español)](https://git-scm.com/book/es/v2) — Scott Chacon y Ben Straub, 2014 | libro · intro · 240 | es | Gratis · CC BY-NC-SA 3.0: puede ir como archivo (no comercial, con atribución) | 7 | Git y ramas en español; con los capítulos 1 a 3 basta para repositorio, commits y branches. |
| `PY4E-ES` | [Python para todos (PY4E-ES)](https://es.py4e.com/) — Charles Severance (traducción de la comunidad), s/f | curso + libro · intro · 1800 | es | Gratis · licencia Creative Commons (según el sitio) | 7, 8 | Python desde cero en español con videos y ejercicios: el nivel 'funcional para modificar y depurar' que pide la malla. |
| `MDN-HTTP-ES` | [Generalidades del protocolo HTTP](https://developer.mozilla.org/es/docs/Web/HTTP/Guides/Overview) — MDN Web Docs (Mozilla), 2026 | documentación · intro · 20 | es | Gratis · CC BY-SA 2.5: puede ir como archivo con atribución | 8 | Base mínima de HTTP (métodos, códigos, cabeceras) para entender APIs, webhooks y errores de herramientas. |
| `SQLBOLT` | [SQLBolt — Learn SQL with simple, interactive exercises](https://sqlbolt.com/) — SQLBolt, s/f | tutorial interactivo · intro · 180 | en | Gratis · © SQLBolt: linkear | 8 | Ejercicios cortos en el navegador para consultar datos de ventas (SELECT, JOIN, GROUP BY) sin instalar nada. |
| `STRIPE-IDEM` | [Designing robust and predictable APIs with idempotency](https://stripe.com/blog/idempotency) — Brandur Leach (Stripe), 2017 | post técnico · intermedio · 20 | en | Gratis · © Stripe: linkear | 8, 19 (también E5) | Idempotencia y reintentos explicados con claridad: por qué un agente que reintenta no debe crear dos cotizaciones ni dos cobros. |
| `ANT-MCP-COURSE` | [Introduction to Model Context Protocol](https://anthropic.skilljar.com/introduction-to-model-context-protocol) — Anthropic Academy, 2025 | curso · intermedio · 120 | en | Gratis (registro) · © Anthropic: linkear | 9 | Construir y conectar un servidor MCP con Python paso a paso; práctica para el Tool-Using Agent (ojo: puede ser anterior a la spec 2026-07-28). |
| `MCP-SPEC` | [Model Context Protocol — Specification 2026-07-28 (y changelog)](https://modelcontextprotocol.io/specification/2026-07-28) — Model Context Protocol (proyecto abierto), 2026 | especificación · avanzado · 120 | en | Gratis · MIT (repo): puede ir como archivo con atribución | 9, 10, 17 (también E5) | Fuente normativa vigente: protocolo sin estado, server/discover, extensiones (Tasks, Skills over MCP, MCP Apps) y principios de consentimiento. |
| `MS-CS-MCP` | [Extend your agent with Model Context Protocol (Copilot Studio)](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp) — Microsoft Learn, 2026 | documentación oficial · intro · 15 | en | Gratis · © Microsoft: linkear | 9 | Cómo se ve MCP en una herramienta low-code empresarial (Copilot Studio); referencia de la malla si la empresa opera sobre Microsoft 365. |
| `ANT-CEMCP` | [Code execution with MCP: building more efficient AI agents](https://www.anthropic.com/engineering/code-execution-with-mcp) — Anthropic, 2025 | post de ingeniería · avanzado · 20 | en | Gratis · © Anthropic: linkear + ficha propia | 10, 14 (también E4) | Por qué cargar cientos de herramientas y resultados intermedios en el contexto sale caro, y cómo la ejecución de código reduce tokens. |
| `ANT-CU` | [Computer use tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool) — Anthropic, 2026 | documentación oficial · intermedio · 25 | en | Gratis · © Anthropic: linkear + ficha propia | 10 | Automatizar aplicaciones sin API (portales de marca o sistemas internos) mediante capturas y clics, y entender sus riesgos. |
| `ANT-MANAGED` | [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents) — Anthropic, 2026 | post de ingeniería · avanzado · 20 | en | Gratis · © Anthropic: linkear + ficha propia | 10, 19 (también E5) | Postura 2026 de Anthropic: los arneses codifican supuestos que caducan cuando mejoran los modelos; base de su servicio Managed Agents. |
| `ANT-SDK` | [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) — Anthropic (Claude Code Docs), 2026 | documentación oficial · intermedio · 30 | en | Gratis · © Anthropic: linkear + ficha propia | 10, 11 (también E4) | El mismo loop y herramientas de Claude Code como librería Python/TypeScript para construir sus propios agentes con permisos y sesiones. |
| `ANT-SKILLS` | [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — Anthropic, 2025 | post de ingeniería · intermedio · 15 | en | Gratis · © Anthropic: linkear + ficha propia | 10 | Él ya construye skills: explica la divulgación progresiva (metadatos → SKILL.md → archivos) y cuándo conviene una skill. |
| `OAI-AGENTS` | [Agents (OpenAI API docs)](https://developers.openai.com/api/docs/guides/agents) — OpenAI, 2026 | documentación oficial · intermedio · 20 | en | Gratis · © OpenAI: linkear + ficha propia | 10, 11 (también E4) | Referencia de la malla: elegir entre Agents API (arnés gestionado por OpenAI), Agents SDK o Responses API según cuánto control quiera. |

*También sirven en esta etapa (listadas en otra):* `ANT-TOOLUSE` (sem. 7), `HF-AGENTS` (sem. 10), `MS-AIAB` (sem. 9).

### Etapa 4 — Orquestación, multi-agente y AI Workforce (semanas 11–14) · 9 fuentes

| ID | Fuente (autor, año) | Tipo · nivel · min | Idioma | Acceso / licencia | Semanas (otras etapas) | Por qué sirve a Miguel |
|---|---|---|---|---|---|---|
| ★ `ANT-MAS` | [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — Anthropic (J. Hadfield, B. Zhang, K. Lien, F. Scholz, J. Fox, D. Ford), 2025 | guía oficial (post de ingeniería) · intermedio · 30 | en | Gratis · © Anthropic: linkear + ficha propia | 11, 12, 14 | Caso real de orquestador + subagentes en producción, con costos (≈15× tokens), reglas de delegación y lecciones de confiabilidad. |
| ★ `A2A-SPEC` | [Agent2Agent (A2A) Protocol — especificación v1.0 y 'What is A2A'](https://a2a-protocol.org/latest/specification/) — A2A Project (Linux Foundation; creado por Google), 2026 | especificación · intermedio · 40 | en | Gratis · Apache 2.0: puede ir como archivo con atribución | 13 | Cubre 'A2A e interoperabilidad' de la semana 13: Agent Card, tareas, mensajes y artefactos, y la diferencia con MCP. |
| `COG-DBMA` | [Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) — Walden Yan (Cognition), 2025 | post · intermedio · 15 | en | Gratis · © Cognition: linkear | 11 | Contrapeso a la moda multi-agente: compartir contexto completo y evitar decisiones implícitas en conflicto; leer junto a ANT-MAS. |
| `MS-PAT` | [Patrones de orquestación de agentes de IA (AI agent orchestration patterns)](https://learn.microsoft.com/es-es/azure/architecture/ai-ml/guide/ai-agent-design-patterns) — Microsoft (Azure Architecture Center), 2026 | guía oficial · intermedio · 45 | es (original en inglés) | Gratis · CC BY 4.0 (MicrosoftDocs/architecture-center): puede ir como archivo con atribución | 11, 12 | Catálogo en español: secuencial, concurrente, group chat, maker-checker, handoff y magentic, con cuándo NO usar cada uno. |
| `ADK-WF` | [Workflows: multi-agent, multi-node applications (Agent Development Kit)](https://adk.dev/workflows/) — Google (ADK), 2026 | documentación oficial · intermedio · 30 | en | Gratis · © Google: linkear | 12 | Alternativa del ecosistema Google (ADK) que la malla lista en el stack de orquestación. |
| `MAST` | [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) — Mert Cemri et al., 2025 | paper · avanzado · 60 | en | Gratis · CC BY-NC-ND 4.0: linkear/citar, no redistribuir modificado | 12, 16 (también E5) | Taxonomía de 14 modos de falla en 3 grupos (diseño del sistema, desalineación entre agentes, verificación): checklist para su AI Sales Team. |
| `OAI-SDK` | [OpenAI Agents SDK (handoffs, guardrails, tracing)](https://openai.github.io/openai-agents-python/) — OpenAI, 2026 | documentación oficial · intermedio · 45 | en | Gratis · © OpenAI: linkear + ficha propia | 12, 17 (también E5) | Implementación concreta de handoffs, guardrails y trazas en código; contraste de ecosistema frente a Claude. |
| `ANT-EI` | [The Anthropic Economic Index](https://www.anthropic.com/economic-index) — Anthropic, 2026 | informe + datos · intermedio · 30 | en | Gratis · © Anthropic: linkear + ficha propia | 14, 20 (también E6) | Datos de uso real de IA por tarea (automatización vs. aumento) para argumentar qué parte del trabajo delegar al agente. |
| `MS-WTI` | [2025: The year the Frontier Firm is born (Work Trend Index)](https://www.microsoft.com/en-us/worklab/work-trend-index/2025-the-year-the-frontier-firm-is-born) — Microsoft WorkLab, 2025 | informe · intro · 30 | en | Gratis · © Microsoft: linkear | 14, 23 (también E6) | Conceptos de equipos humano-agente, 'human-agent ratio' y 'agent boss' para diseñar la AI Workforce de su local. |

*También sirven en esta etapa (listadas en otra):* `ANT-CEMCP` (sem. 14), `ANT-PRICE` (sem. 14), `ANT-SDK` (sem. 11), `DLAI-AGENTIC` (sem. 12), `LG-WFA` (sem. 11), `MS-AIAB` (sem. 12), `OAI-AGENTS` (sem. 11).

### Etapa 5 — Producción: evaluación, seguridad, observabilidad y gobernanza (semanas 15–19) · 14 fuentes

| ID | Fuente (autor, año) | Tipo · nivel · min | Idioma | Acceso / licencia | Semanas (otras etapas) | Por qué sirve a Miguel |
|---|---|---|---|---|---|---|
| ★ `ANT-EVAL` | [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — Anthropic (M. Grace, J. Hadfield, R. Olivares, J. De Jonghe), 2026 | guía oficial (post de ingeniería) · intermedio · 40 | en | Gratis · © Anthropic: linkear + ficha propia | 15, 16 | Guía vigente (ene-2026) para la suite de 30-50 pruebas del Agent QA Lab: tareas, graders, pass@k vs pass^k y hoja de ruta de 8 pasos. |
| ★ `HAM-FAQ` | [AI Evals: Everything You Need to Know (FAQ)](https://hamel.dev/blog/posts/evals-faq/) — Hamel Husain y Shreya Shankar, 2026 | guía (FAQ) · intermedio · 90 | en | Gratis · © autores: linkear + ficha propia | 16, 17 | Método práctico (análisis de errores, evals binarias, jueces LLM validados) actualizado a sept-2026; lo más aplicable para un no-ingeniero. |
| ★ `SW-TRIF` | [The lethal trifecta for AI agents: private data, untrusted content, and external communication](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) — Simon Willison, 2025 | post · intro · 12 | en | Gratis · © autor: linkear + ficha propia | 17 | La regla de seguridad más útil para quien conecta agentes a correo, CRM y web: no juntar datos privados, contenido no confiable y salida externa. |
| ★ `OAI-GOV` | [Practices for Governing Agentic AI Systems](https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf) — Yonadav Shavit, Sandhini Agarwal, Miles Brundage et al. (OpenAI), 2023 | whitepaper (PDF) · intermedio · 60 | en | Gratis · © OpenAI: linkear + ficha propia | 18, 19 | Siete prácticas de gobierno (idoneidad, aprobación, defaults, legibilidad, monitoreo, atribución, interrupción) para su protocolo de aprobación. |
| `HAM-EVAL` | [Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/) — Hamel Husain, 2024 | post · intro · 25 | en | Gratis · © autor: linkear | 15 | Caso real de un asistente inmobiliario sobre un CRM (muy parecido a ventas de autos): tres niveles de evaluación y trazas. |
| `LANGFUSE` | [LLM Observability & Application Tracing (Langfuse docs)](https://langfuse.com/docs/observability/overview) — Langfuse, 2026 | documentación · intermedio · 20 | en | Gratis · herramienta open source (también SaaS): linkear | 16 | Trazas y tableros de calidad/costo auto-hospedables; Anthropic la menciona como alternativa open source. |
| `ANT-CONTAIN` | [How we contain Claude across products](https://www.anthropic.com/engineering/how-we-contain-claude) — Anthropic, 2026 | post de ingeniería · avanzado · 30 | en | Gratis · © Anthropic: linkear + ficha propia | 17, 19 | Cómo acotar el 'radio de explosión' de un agente (entorno, permisos, supervisión humana) con visión de mayo 2026. |
| `GOOG-SEC` | [An Introduction to Google's Approach for Secure AI Agents](https://research.google/pubs/an-introduction-to-googles-approach-for-secure-ai-agents/) — Santiago Díaz, Christoph Kern, Kara Olive (Google), 2025 | whitepaper · intermedio · 45 | en | Gratis · © Google: linkear | 17, 18 | Defensa en capas (controles deterministas + defensas basadas en razonamiento) y tres principios: controlador humano claro, poderes limitados, acciones observables. |
| `OWASP-AG` | [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) — OWASP GenAI Security Project, 2025 | guía / estándar comunitario · intermedio · 90 | en | Gratis · CC BY-SA 4.0: puede ir como archivo con atribución y misma licencia | 17, 18 | Top 10 de riesgos propios de agentes (secuestro de objetivo, mal uso de herramientas, abuso de identidad, envenenamiento de memoria, fallas en cascada, agentes rebeldes). |
| `OWASP-LLM26` | [OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) — OWASP GenAI Security Project, 2026 | guía / estándar comunitario · intermedio · 90 | en | Gratis · licencia Creative Commons del proyecto OWASP (verificar en el PDF) | 17 | Edición de agosto 2026 del Top 10 para aplicaciones con LLM, mapeada a NIST, MITRE ATLAS y al Top 10 de agentes. |
| `SW-PI` | [Simon Willison on prompt-injection (serie del blog)](https://simonwillison.net/tags/prompt-injection/) — Simon Willison, 2026 | blog (serie viva) · intermedio · 60 | en | Gratis · © autor: linkear | 17 | Bitácora viva de ataques reales y defensas; la fuente más al día para revisar cada trimestre. |
| `LEY-21719` | [Ley 21.719 — regula la protección y el tratamiento de los datos personales y crea la Agencia de Protección de Datos Personales](https://www.bcn.cl/leychile/navegar?idNorma=1209272) — Congreso Nacional de Chile (texto oficial en BCN), 2024 | ley · intermedio · 120 | es | Gratis · texto legal oficial | 18 | Rige el tratamiento de datos de clientes (RUT, contacto, crédito). Vigencia legal: 1-dic-2026; proyecto para postergarla a 1-dic-2027 en trámite a sept-2026. |
| `NIST-RMF` | [AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework) — NIST (EE.UU.), 2023 | marco normativo · intermedio · 90 | en | Gratis · publicación del gobierno de EE.UU. (dominio público): puede ir como archivo | 18, 19 | Lenguaje estándar de gestión de riesgos (Govern, Map, Measure, Manage) para la matriz de riesgos del Agent QA Lab. |
| `CL-PNIA` | [Política Nacional de Inteligencia Artificial (Chile)](https://www.minciencia.gob.cl/areas/inteligencia-artificial/politica-nacional-de-inteligencia-artificial/) — Ministerio de Ciencia, Tecnología, Conocimiento e Innovación, 2024 | política pública · intro · 60 | es | Gratis · documento público | 19, 23 (también E6) | Marco chileno (factores habilitantes, desarrollo y adopción, gobernanza y ética, eje actualizado desde 2023) para el contexto local del business case. |

*También sirven en esta etapa (listadas en otra):* ★ `OAI-PGA` (sem. 18), `ANT-MANAGED` (sem. 19), `DLAI-AGENTIC` (sem. 16), `GOOG-INTRO` (sem. 15), `HUY-AIE` (sem. 15), `LEVELS` (sem. 18), `MAST` (sem. 16), `MCP-SPEC` (sem. 17), `MS-AIAB` (sem. 17), `OAI-SDK` (sem. 17), `STRIPE-IDEM` (sem. 19).

### Etapa 6 — AI Business, emprendimiento y transformación (semanas 20–24) · 4 fuentes

| ID | Fuente (autor, año) | Tipo · nivel · min | Idioma | Acceso / licencia | Semanas (otras etapas) | Por qué sirve a Miguel |
|---|---|---|---|---|---|---|
| ★ `BVP-PRICE` | [The AI pricing and monetization playbook](https://www.bvp.com/atlas/the-ai-pricing-and-monetization-playbook) — Bessemer Venture Partners (Atlas; B. Deeter, K. Bennett, S. Dholakia y equipo), 2026 | guía (playbook de inversionista) · intermedio · 35 | en | Gratis · © Bessemer: linkear + ficha propia | 21, 22 | Modelos de negocio (copiloto, agente, servicio con IA), métricas de cobro y disciplina de unit economics, actualizado a feb-2026. |
| `MOMTEST` | [The Mom Test](https://www.momtestbook.com/) — Rob Fitzpatrick, 2013 | libro · intro · 180 | en | Pago · © autor: solo ficha propia | 20 | Cómo entrevistar clientes sin sesgo para validar el problema antes de construir el agente o el emprendimiento. |
| `FC-SAAS` | [AI leads a service as software paradigm shift](https://foundationcapital.com/ideas/ai-leads-a-service-as-software-paradigm-shift) — Joanne Chen y Jaya Gupta (Foundation Capital), 2024 | post (tesis de inversión) · intro · 15 | en | Gratis · © Foundation Capital: linkear | 21 | Formula el giro de 'software como servicio' a 'servicio como software' (cobrar por resultado): base para pensar agent-as-a-service. |
| `MS-CAF-AG` | [AI agent adoption (Cloud Adoption Framework)](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai-agents/) — Microsoft Learn, 2025 | guía oficial · intro · 20 | en (versión es-es disponible) | Gratis · CC BY 4.0 (repos MicrosoftDocs): puede ir como archivo con atribución | 23, 24 | Proceso de adopción en cuatro áreas (planificar, gobernar y asegurar, construir, gestionar) y tipos de agentes (productividad, acción, automatización). |

*También sirven en esta etapa (listadas en otra):* ★ `MS-CAF-BIZ` (sem. 23), `ANT-EI` (sem. 20), `ANT-PRICE` (sem. 22), `CL-PNIA` (sem. 23), `MCK-SEIZE` (sem. 21), `MITSMR-AE` (sem. 23), `MOL-COI` (sem. 20), `MS-WTI` (sem. 23).


---

## 4. Links de la malla original: estado

Se verificaron los 17 links de la sección "Referencias" de `malla-curricular.html` (HTTP + título de la página, 26-sep-2026). **Ninguno está roto ni apunta a otra cosa.**

| # | Link de la malla | Estado |
|---|---|---|
| 1 | executive.mit.edu/agentic-ai.html | OK: "Agentic AI: Business Implications and Applications" |
| 2 | harvardonline.harvard.edu/course/agentic-ai-foundations | **Existe, pero bloquea bots** (HTTP 429, checkpoint de Vercel). Título y contenido confirmados en índice de búsqueda: "Agentic AI Foundations: Business Applications and Risks" (4 semanas, US$595, Prof. Hanspeter Pfister). |
| 3 | executive.berkeley.edu/…/agentic-ai-strategy-applications-and-organizational-impact | OK |
| 4 | jbs.cam.ac.uk/executive-education/innovation/agentic-ai/ | OK: "Agentic AI: Design, Build, Govern" |
| 5 | hec.edu/en/executive-education/deploying-agentic-ai | OK |
| 6 | ie.edu/es/lifelong-learning/programas/ia-agentes-autonomos/ | OK: "IA y Agentes Autónomos" |
| 7 | uai.cl/postgrados/cursos/certificado-profesional-agentes-inteligentes-autonomos | OK: "Certificado Profesional en Agentic AI - UAI" |
| 8 | learn.stanford.edu/Bing-AgenticAI.html | OK: "Agentic AI Program" |
| 9 | developers.openai.com/api/docs/guides/agents | OK: "Agents · OpenAI API" (catalogado como OAI-AGENTS) |
| 10 | developers.openai.com/api/docs/guides/agents-api/tools/mcp | OK: "MCP connections · OpenAI API" |
| 11 | resources.anthropic.com/building-effective-ai-agents | OK: recurso descargable "Building Effective AI Agents". La fuente canónica usada aquí es el post `anthropic.com/engineering/building-effective-agents` (ANT-BEA). |
| 12 | anthropic.com/engineering/demystifying-evals-for-ai-agents | OK (catalogado como ANT-EVAL, núcleo) |
| 13 | learn.microsoft.com/microsoft-copilot-studio/agents-overview | OK: redirige a `/en-us/…/agents-overview` |
| 14 | learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp | OK (catalogado como MS-CS-MCP) |
| 15 | developers.google.com/program/gear | OK: "GEAR · Google Developer Program" |
| 16 | udacity.com/course/agentic-ai-for-business-leaders--cd14381 | OK |
| 17 | coursera.org/professional-certificates/ibm-rag-and-agentic-ai | OK |

Los programas ejecutivos (1–8, 15–17) son referencias de diseño curricular y no textos base, así que no se incluyeron en `fuentes.json`. Las fechas, precios y ediciones cambian y conviene revisarlos directamente antes de matricularse.

---

## 5. Qué textos pasarle al tutor y cómo

### 5.1 Principio general

El tutor se ancla en **fichas propias con `id` estable y en el catálogo JSON**, no en copias de artículos. Las fichas son resúmenes originales (con citas de 1–2 frases), así que no hay problema de licencia, son chicas y ya vienen en español y aplicadas a ventas automotrices. El texto original se usa por link y solo se incluye como archivo cuando la licencia lo permite explícitamente.

### 5.2 Qué incluir como archivo, qué solo linkear

| Nivel | Qué | Por qué | Tamaño aprox. |
|---|---|---|---|
| **A. Siempre en el proyecto o skill** | `fuentes.json` + las 16 fichas de `base/fichas/` | Material propio, sin restricción de licencia y ya adaptado | Fichas ≈ 36k tokens; JSON ≈ 14k tokens |
| **B. Puede ir como archivo (licencia abierta, con atribución)** | MS-CAF-BIZ, MS-CAF-AG, MS-PAT (CC BY 4.0); MCP-ARCH y el changelog de MCP-SPEC (MIT); páginas "What is A2A" y conceptos clave de A2A-SPEC (Apache 2.0); NIST-RMF (dominio público EE.UU.); REACT y LEVELS (CC BY 4.0); lecciones de MS-AIAB (MIT) y HF-AGENTS (Apache 2.0); MDN-HTTP-ES (CC BY-SA 2.5) | Permiten reproducir con atribución. Conviene incluir solo las secciones que el tutor usa, con la fuente y la fecha en la cabecera | Seleccionar ≤ 60–80k tokens en total |
| **B′. Abierta pero con condiciones** | OWASP-AG y OWASP-LLM26 (CC BY-SA: obras derivadas con la misma licencia); PROGIT-ES (CC BY-NC-SA: **no comercial**); MAST (CC BY-NC-ND: **sin obras derivadas**) | Válido para estudio personal. Si el tutor llegara a ser un producto comercial, revisar antes | — |
| **C. Solo link + ficha propia** | Todo lo de Anthropic, OpenAI, Google/Kaggle, Weng, Willison, Hamel, Bessemer, Foundation Capital, a16z, McKinsey, MIT SMR, HBR, Microsoft WorkLab, Cognition, cursos y videos | Tienen copyright (aunque sean gratis). Copiar el texto completo en la base no está autorizado, y además envejece | 0 (el tutor consulta la web cuando necesita el detalle) |
| **D. Libros de pago** | MOL-COI, HUY-AIE, MOMTEST | Solo ficha propia si Miguel los lee; nunca subir el libro | — |

Este es un criterio conservador. Si Miguel quiere que el tutor cite con precisión un texto de nivel C, es mejor que el tutor lo abra en el momento con su herramienta de búsqueda o lectura web y cite 1–2 frases, en vez de guardar copias.

### 5.3 Estructura sugerida si el tutor se arma como skill o proyecto de Claude

```
tutor-ia-agentica/
├── SKILL.md                 ← instrucciones del tutor + política de fuente vigente (5.4)
└── references/
    ├── fuentes.json         ← catálogo (se consulta por id, etapa o semana)
    ├── fichas/              ← 16 fichas núcleo (se cargan bajo demanda, según la semana)
    └── abiertas/            ← extractos de nivel B, con cabecera: fuente, licencia, fecha
```

Cargar las fichas **bajo demanda** (divulgación progresiva, ver ANT-SKILLS): en la semana *n*, el tutor lee solo las fichas cuyo campo `semanas` incluye *n*. Así el contexto se mantiene chico (ver ANT-CTX).

### 5.4 Política de "fuente vigente" para el tutor

Para copiar en las instrucciones del tutor:

1. **Anclar.** Toda afirmación técnica o cifra se apoya en una ficha o fuente del catálogo y se cita con `id` y fecha, p. ej. "≈15× tokens vs. chat (ANT-MAS, jun-2025)". Si el tema no está en la base, el tutor lo dice y propone buscar en una fuente primaria. **Nunca inventa** una fuente, cifra o cita.
2. **Clasificar la volatilidad de lo que se enseña:**
   - **Alta:** especificaciones y protocolos (MCP, A2A), APIs y SDKs, nombres de modelos, precios, benchmarks, leyes en trámite.
   - **Media:** guías de prácticas (evals, seguridad, patrones), informes de consultoras.
   - **Baja:** conceptos y papers canónicos (loop del agente, ReAct, RAG, workflows vs. agentes).
3. **Plazos de revisión** (contados desde la fecha del campo `verificado`):
   - alta: más de **90 días** → el tutor abre la fuente antes de enseñar el detalle, o avisa "según la fuente al <fecha>";
   - media: más de **12 meses**;
   - baja: solo si hay una señal de cambio.
4. **Jerarquía cuando hay conflicto:** especificación oficial > documentación oficial > post de ingeniería del proveedor > guía de practicante reconocido > informe de consultora > medios y blogs. Gana la fuente más reciente del nivel más alto. El tutor señala la discrepancia y marca la ficha para actualizarla.
5. **Cursos de terceros pueden ir atrasados** respecto de la especificación (p. ej. el curso de MCP frente a la revisión 2026-07-28). El tutor enseña con la especificación vigente y usa el curso solo para práctica.
6. **Fechar las cifras.** Precios, porcentajes y rankings siempre llevan fecha y fuente; nunca se presentan como verdades permanentes.
7. **Derecho y regulación.** El tutor no da asesoría legal. Para la Ley 21.719 y el proyecto de ley de IA en Chile, informa el estado a la fecha de la fuente y recomienda validar con un abogado o con el área legal.

### 5.5 Cada cuánto actualizar la base

| Frecuencia | Qué revisar | Cómo |
|---|---|---|
| **Al iniciar cada etapa** (≈ cada 4 semanas) | Fichas y fuentes de la etapa que empieza | Verificar links (HTTP + título), revisar si hay versión nueva y ajustar la sección "Notas de vigencia" de la ficha |
| **Mensual** | MCP (`/specification/latest` y changelog), A2A (release notes), docs de Anthropic y OpenAI (agentes, herramientas), precios (ANT-PRICE) | Si hay versión nueva, actualizar MCP-ARCH o A2A-SPEC y el campo `verificado` |
| **Trimestral** | Seguridad (SW-PI, OWASP), evals (HAM-FAQ), blog de ingeniería de Anthropic, guías de Microsoft y Google | Agregar al catálogo fuentes nuevas relevantes; retirar las superadas |
| **Semestral o anual** | Informes de negocio (McKinsey, MIT SMR/BCG, Microsoft WTI, Anthropic Economic Index), marcos (NIST) | Reemplazar por la edición nueva si existe |
| **Por evento** | Ley 21.719 (la votación del proyecto de postergación y el 1-dic-2026), proyecto de ley de IA (boletines 15869-19 y 16821-19, en el Senado) | Actualizar LEY-21719 y CL-PNIA |

Chequeo rápido de links, reutilizando el método de este informe:

```bash
python3 -c "import json;[print(f['url']) for f in json.load(open('base/fuentes.json'))]" \
 | while read u; do printf '%s  %s\n' "$(curl -sS -L -o /dev/null -w '%{http_code}' -A 'Mozilla/5.0' --max-time 25 "$u")" "$u"; done
```

Ojo: YouTube, Kaggle, GitHub, McKinsey, BCG y Harvard Online bloquean clientes automáticos (429, 403 o reCAPTCHA). Un código distinto de 200 en esos sitios no significa que el link esté roto; hay que confirmarlo a mano o con búsqueda.

---

## 6. Método y limitaciones

- **Verificación.** Cada URL se comprobó el 26-sep-2026 con HTTP y el título de la página. Las 16 fuentes núcleo se leyeron completas (o en sus secciones clave, en el caso del FAQ de Hamel) para escribir las fichas. En los sitios que bloquean bots, la existencia y el título se confirmaron con búsqueda web o lectura alternativa; el campo `verificado` de cada entrada indica el método usado.
- **Karpathy (KAR-LLM).** YouTube no permite lectura automática. La ficha se basó en una transcripción pública de la charla, contrastada con resúmenes independientes.
- **Estimaciones.** El campo `minutos` es una estimación propia de tiempo de lectura o video. `anio: null` indica que el recurso no tiene fecha de publicación clara (sitios de práctica como PY4E-ES o SQLBolt).
- **Cosas que no se incluyeron por no poder verificarlas bien:** el informe completo de MIT SMR/BCG (solo la parte abierta), el texto completo de McKinsey (bloqueado; está en el catálogo, confirmado por índice, pero sin ficha), las listas completas de riesgos OWASP (solo se citan las que confirmé) y la duración exacta de algunos cursos.
- **No es asesoría legal.** Las referencias a la Ley 21.719 y a la regulación de IA en Chile describen su estado público al 26-sep-2026.

---
id: MS-CAF-BIZ
titulo: "Business plan for AI agents (Plan de negocio para agentes de IA) — Cloud Adoption Framework"
autor: "Microsoft Learn"
anio: 2026
url: https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai-agents/business-strategy-plan
url_es: https://learn.microsoft.com/es-es/azure/cloud-adoption-framework/ai-agents/business-strategy-plan
etapas: [1, 6]
semanas: [3, 23]
idioma_fuente: en (versión es-es disponible)
tipo: guía oficial
licencia: CC BY 4.0 (repositorio MicrosoftDocs/cloud-adoption-framework)
verificado: 2026-09-26 (texto completo leído; página actualizada el 2026-04-10)
vigencia: "Documentación viva. Los nombres de productos Microsoft (Foundry, Copilot Studio) cambian seguido; el método de priorización es estable."
---

# MS-CAF-BIZ · Plan de negocio para agentes de IA (Microsoft CAF, 2026)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Es la guía de Microsoft para decidir **dónde** invertir en agentes antes de elegir herramientas. Tiene cuatro piezas: (1) cuándo NO usar agentes, (2) cuándo sí, (3) cómo priorizar casos de uso con un puntaje de 1 a 5 en tres dimensiones (impacto de negocio, factibilidad técnica y deseabilidad del usuario) y (4) cómo definir métricas de éxito que funcionen como compuertas de decisión. Incluye un árbol de decisión: primero ver si el caso necesita un agente; si lo necesita, ver si un agente SaaS ya existente cumple, y recién después construir. Es la base natural del entregable de la semana 3 (mapa de 20 oportunidades con matriz valor × factibilidad × riesgo).

## Ideas clave

1. **Primero descartar.** Si la tarea es estructurada y predecible, conviene código o modelos no generativos (más rápidos, baratos y confiables). Si es solo responder o resumir a partir de documentos fijos, basta un RAG clásico, sin agente.
2. **Los agentes sirven cuando la tarea:**
   - exige *decisiones de varios pasos* (leer, evaluar, decidir el siguiente paso, verificar);
   - usa *muchas herramientas o sistemas* en un orden flexible;
   - necesita *comportamiento adaptativo* ante entradas incompletas o ambiguas.
3. **Priorización 1–5 en tres dimensiones:**
   - **Impacto de negocio:** alineación con la estrategia, valor de negocio y plazo de gestión del cambio.
   - **Factibilidad técnica:** riesgos de implementación y operación, salvaguardas suficientes y calce tecnológico.
   - **Deseabilidad del usuario:** personas clave, propuesta de valor y resistencia al cambio.
4. **Cuatro áreas de valor:** rediseñar procesos (interno), enriquecer la experiencia del empleado (interno), reinventar la relación con el cliente (cliente) y acelerar la innovación (cliente).
5. **Pilotar lo más difícil primero.** Un piloto rápido debe probar los pasos más duros: si el agente resuelve eso, el resto es más seguro.
6. **Métricas como compuertas.** Hay que definir KPIs y línea base antes de construir, usarlos para decidir en cada etapa si seguir, cambiar o parar ("go/no-go" con datos, no con optimismo) y seguir midiendo después del lanzamiento.
7. **¿Uno o varios agentes?** Se parte con varios agentes si el caso cruza límites de seguridad o cumplimiento, involucra varios equipos o se espera que crezca. En el resto de los casos, primero se prueba un solo agente.

## Conceptos y definiciones

- **Caso de uso priorizado:** una idea con puntaje en impacto, factibilidad y deseabilidad.
- **Compuerta de decisión (decision gate):** punto donde una métrica acordada decide si el proyecto continúa.
- **Línea base:** desempeño actual del proceso, medido antes del agente.
- **Agente SaaS vs. agente construido:** usar un agente ya existente en un producto (p. ej. dentro de Microsoft 365) o construir uno propio (low-code con Copilot Studio o pro-code con Foundry).
- **Tipos de agente (página madre de la guía):** de productividad (buscar y sintetizar), de acción (ejecutar tareas en un flujo definido) y de automatización (procesos de varios pasos con poca supervisión).

## Errores comunes

- Partir por la herramienta ("hagamos algo con agentes") en vez de por el problema y su KPI.
- Elegir un caso de alto valor pero sin salvaguardas claras. La guía dice explícitamente que no hay que avanzar si las salvaguardas no están claras.
- No medir la línea base y después no poder demostrar el ROI.
- Pilotar la parte fácil y descubrir tarde que la difícil no funciona.
- Ignorar la deseabilidad: un agente técnicamente bueno que el equipo no quiere usar fracasa igual.

## Ejemplo aplicado: mapa de oportunidades del local

| Caso | Impacto | Factibilidad | Deseabilidad | Comentario |
|---|---|---|---|---|
| Agente que prepara el seguimiento diario de leads (resumen + guion + próxima acción) | 5 | 4 | 5 | Varios pasos, varias fuentes (CRM, agenda, stock): calza con "agente". KPI: tasa de agendamiento. |
| Cálculo de comisiones del mes | 4 | 5 | 4 | Reglas fijas: **no es agente**, es código o planilla. |
| FAQ de fichas técnicas de modelos | 3 | 5 | 3 | Documentos fijos: **RAG clásico**, sin agente. |
| Agente que negocia descuentos con clientes por WhatsApp | 4 | 2 | 2 | Riesgo alto y salvaguardas poco claras: posponer. |

Compuerta sugerida para el primer caso: si en 4 semanas de piloto la tasa de agendamiento no sube respecto a la línea base, se revisa el diseño o se detiene.

## Citas cortas

- "Before you choose to use an AI agent, it helps to know when an agent isn't a good fit." (sección "When not to use AI agents")
- "Never advance a use case with unclear or incomplete safeguards." (buena práctica en "Sufficient safeguards")

## Notas de vigencia para el tutor

- La página se actualizó el 2026-04-10. Existe versión en español (es-es) generada por Microsoft, útil para Miguel.
- La licencia CC BY 4.0 del repositorio permite incluir el texto con atribución (ver la recomendación en `02-base-de-conocimiento.md`).
- Complementa MCK-SEIZE y MITSMR-AE (visión estratégica) y BVP-PRICE (economía del caso).

## Preguntas de práctica

- P: ¿En qué dos situaciones la guía recomienda NO usar un agente y qué usar en su lugar?
  R: (1) Tareas estructuradas o predecibles, con pasos claros y reglas estrictas: usar código o modelos no generativos. (2) Recuperación de conocimiento estático (responder o resumir desde documentos fijos): usar un RAG clásico.
- P: ¿Cuáles son las tres dimensiones del puntaje de priorización y qué mide cada una?
  R: Impacto de negocio (alineación estratégica, valor y plazo de gestión del cambio), factibilidad técnica (riesgos, salvaguardas y calce tecnológico) y deseabilidad del usuario (personas, propuesta de valor y resistencia al cambio).
- P: ¿Qué es una compuerta de decisión y por qué importa para el business case?
  R: Es un punto del proyecto donde métricas acordadas de antemano deciden si seguir, cambiar o parar. Evita invertir por optimismo y hace verificable el ROI.
- P: ¿Por qué conviene pilotar primero los pasos más difíciles?
  R: Porque si el agente resuelve lo más duro, el resto del proyecto tiene menos riesgo. Pilotar lo fácil da una falsa sensación de éxito.
- P: ¿Cuándo sugiere la guía partir con un sistema multi-agente en vez de uno solo?
  R: Cuando el caso cruza límites de seguridad o cumplimiento, involucra a varios equipos o se sabe que crecerá. Si no, primero se prueba un solo agente.

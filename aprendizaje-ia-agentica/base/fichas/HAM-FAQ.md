---
id: HAM-FAQ
titulo: "AI Evals: Everything You Need to Know (FAQ)"
autor: "Hamel Husain y Shreya Shankar"
anio: 2026
url: https://hamel.dev/blog/posts/evals-faq/
etapas: [5]
semanas: [16, 17]
idioma_fuente: en
tipo: guía (FAQ)
verificado: 2026-09-26 (secciones clave leídas; versión publicada el 18-sep-2026 y modificada el 21-sep-2026)
vigencia: "Documento vivo y actualizado a sept-2026. Las recomendaciones de herramientas o modelos para jueces (p. ej. 'Jev') son lo más volátil."
---

# HAM-FAQ · AI Evals: Everything You Need to Know (Husain y Shankar, 2026)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

Es el FAQ de referencia de dos de los practicantes más citados en evaluación de productos de IA. Su tesis: las evals útiles son **evals de producto** (miden si *tu* aplicación hace lo que necesitas), no benchmarks de modelos. Se construyen desde el **análisis de errores**: leer trazas reales, anotar qué falla, agrupar esas fallas en una taxonomía y recién entonces decidir qué evaluar y cómo. Recomienda evaluaciones **binarias (pasa/falla)** en vez de escalas de 1 a 5, verificaciones de código cuando se pueda y **jueces LLM validados contra etiquetas humanas** (tasa de verdaderos positivos y negativos) cuando haga falta criterio. También separa guardrails (en línea, rápidos) de evaluadores (asíncronos) y explica cómo evaluar flujos agénticos por etapas.

## Ideas clave

1. **Benchmarks vs. evals de producto.** Un buen puntaje en un benchmark público dice poco sobre si tu agente eligió el pedido correcto o esperó la confirmación de la herramienta antes de decir "listo".
2. **Traza.** Es el registro completo de una sesión: mensajes, llamadas a herramientas, documentos recuperados y pasos de todos los agentes.
3. **Evaluación mínima viable.** Partir por el análisis de errores, no por infraestructura: revisar 20–50 salidas cada vez que hay cambios importantes, con **un experto del dominio como "dictador benevolente"** de la calidad. Un notebook o una interfaz simple bastan.
4. **Análisis de errores en cuatro pasos:**
   - reunir trazas representativas (o sintéticas si no hay);
   - *open coding*: notas libres sobre qué falla; en cada traza, la primera falla aguas arriba;
   - *axial coding*: agrupar las notas en una taxonomía de fallas y contar su frecuencia;
   - iterar hasta la "saturación teórica", cuando ya no aparecen fallas nuevas.
   Anotar al menos 30 trazas a mano antes de pedir ayuda a un agente, y trabajar con un pool de unas 100 trazas diversas.
5. **Dónde va el esfuerzo.** En sus proyectos, 60–80% del tiempo de desarrollo se fue en análisis de errores y evaluación. Pasar el 100% de las evals es mala señal (no se está exigiendo al sistema); un 70% puede ser más informativo.
6. **Binario > Likert.** Las escalas de 1 a 5 son subjetivas e inconsistentes y exigen más muestra. Pasa/falla obliga a decidir. El progreso gradual se mide con varios chequeos binarios ("4 de 5 datos esperados presentes").
7. **Métrica agregada.** Una tasa "pasa todo" por ejemplo, con posibilidad de bajar al detalle por chequeo, o agrupada por tema o severidad (por ejemplo, fallas que bloquean un lanzamiento y fallas tolerables).
8. **Cuándo automatizar.** Primero arreglar lo obvio en el prompt. Los chequeos de código son baratos. Un juez LLM requiere 100–200 ejemplos etiquetados por modo de falla y mantención continua, así que conviene reservarlo para fallas persistentes que se van a iterar.
9. **Validar el juez LLM.** Separar ejemplos en entrenamiento, desarrollo y prueba, y medir **TPR** (cuántas fallas reales detecta) y **TNR** (cuántas salidas buenas deja pasar sin falsas alarmas) contra etiquetas humanas. El acuerdo bruto engaña cuando las clases están desbalanceadas.
10. **Métricas genéricas: no.** "Utilidad", "coherencia", ROUGE o BERTScore dan falsa confianza. A lo sumo sirven para encontrar trazas que mirar.
11. **Guardrails vs. evaluadores.** Los guardrails van en línea: son rápidos, deterministas y bloquean fallas claras (PII, JSON inválido); sus falsos positivos se tratan como bugs. Los evaluadores corren después, a veces con jueces LLM, y alimentan dashboards y regresiones sin bloquear la respuesta.
12. **CI vs. producción.** En CI van conjuntos chicos y curados, con preferencia por chequeos deterministas. En producción se muestrean trazas y se evalúan en forma asíncrona. Las fallas nuevas que aparecen en producción se agregan al conjunto de CI.
13. **Flujos agénticos en dos fases:** (1) éxito de punta a punta como caja negra; (2) diagnóstico por paso: elección de herramienta, extracción de parámetros, manejo de errores, retención de contexto, eficiencia e hitos. Las llamadas a herramientas se prueban por separado: nombre, argumentos, resultado, estado y **autorización y precondiciones**. Las *matrices de transición de fallas* muestran dónde se concentran los errores.

## Conceptos y definiciones

- **Eval de producto:** mide si tu aplicación cumple lo que necesitan tus usuarios y tu negocio.
- **Análisis de errores:** proceso cualitativo de leer trazas y construir una taxonomía de fallas.
- **Open coding / axial coding:** anotar libremente / agrupar en categorías.
- **Dictador benevolente:** la persona experta que decide qué es "bueno".
- **Saturación teórica:** punto en que revisar más trazas ya no revela fallas nuevas.
- **TPR / TNR:** tasa de verdaderos positivos (fallas detectadas) / de verdaderos negativos (buenas aprobadas).
- **Guardrail:** chequeo en línea que puede bloquear, redactar o regenerar.
- **Evaluador:** medición posterior que no bloquea al usuario.

## Errores comunes

- Comprar una plataforma de evals antes de haber leído 50 trazas propias.
- Usar métricas genéricas listas para usar como medida de calidad.
- Escalas de 1 a 5 sin definición clara, que generan desacuerdo entre evaluadores.
- Construir jueces LLM para todo, incluso para fallas que se arreglaban con una línea de prompt.
- Confiar en un juez LLM sin medir TPR/TNR contra humanos.
- Delegar el análisis de errores a un tercero o a un LLM sin criterio del dominio.

## Ejemplo aplicado: evaluar el agente de seguimiento de leads

1. Exportar 100 conversaciones reales del agente con clientes (anonimizadas).
2. Miguel, como dictador benevolente, anota 30 a mano: "prometió entrega inmediata sin stock", "no pidió RUT antes de cotizar", "tono muy insistente", "no escaló un reclamo".
3. Axial coding: agrupar en (a) promesas sin respaldo en datos, (b) datos faltantes, (c) tono y (d) escalamiento. Contar la frecuencia de cada grupo.
4. Automatizar:
   - chequeo de código: "si menciona entrega inmediata, `stock_buscar` debió devolver al menos una unidad";
   - juez LLM binario para "tono insistente", validado con 150 ejemplos etiquetados (TPR y TNR).
5. Guardrail en línea: bloquear si el mensaje incluye un descuento mayor al permitido. Evaluador asíncrono: tono.
6. Reportar la tasa "pasa todo" semanal, con detalle por grupo.

## Citas cortas

- "Error analysis is the most important activity in evals." (sección de análisis de errores)
- "If you're passing 100% of your evals, you're likely not challenging your system enough." (sección de presupuesto)

## Notas de vigencia para el tutor

- Complementa ANT-EVAL: Anthropic da la estructura (tareas, calificadores, pass^k) y Hamel/Shankar dan el método para descubrir *qué* evaluar.
- El post anterior HAM-EVAL (2024) trae un caso de asistente inmobiliario sobre CRM, muy cercano al mundo automotriz.
- Contiene menciones a herramientas propias o comerciales (plugin de evals, "Jev" de TypeSafe). No presentarlas como estándar.

## Preguntas de práctica

- P: ¿Por qué Husain y Shankar dicen que el análisis de errores es la actividad más importante en evals?
  R: Porque decide qué evals escribir: revela los modos de falla propios de tu aplicación y tus datos, y evita medir métricas genéricas que no reflejan problemas reales.
- P: Describe open coding y axial coding con un ejemplo del concesionario.
  R: Open coding: anotar libremente lo que falla en cada traza (p. ej. "cotizó sin verificar stock"). Axial coding: agrupar esas notas en categorías (p. ej. "promesas sin respaldo en datos") y contar cuántas veces ocurre cada una.
- P: ¿Por qué recomiendan evaluaciones binarias en lugar de escalas de 1 a 5?
  R: Porque las escalas son subjetivas (la diferencia entre 3 y 4 no es consistente), requieren más muestra para detectar diferencias y llevan a elegir el punto medio. El pasa/falla obliga a decidir y es más rápido. El progreso gradual se mide con varios chequeos binarios.
- P: ¿Cómo validas que un juez LLM es confiable?
  R: Comparándolo con etiquetas humanas en conjuntos separados (entrenamiento, desarrollo y prueba) y midiendo TPR (qué proporción de fallas reales detecta) y TNR (qué proporción de salidas buenas aprueba). No basta el acuerdo bruto, que engaña si las clases están desbalanceadas.
- P: ¿Cuál es la diferencia entre un guardrail y un evaluador? Da un ejemplo de cada uno para el agente de ventas.
  R: El guardrail corre en línea, antes de que la respuesta llegue al cliente; es rápido y determinista (p. ej. bloquear un descuento sobre el máximo permitido). El evaluador corre después y mide calidad sin bloquear (p. ej. un juez LLM que revisa si el tono fue insistente), y alimenta dashboards y mejoras.

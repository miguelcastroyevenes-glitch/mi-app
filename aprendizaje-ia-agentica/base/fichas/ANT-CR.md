---
id: ANT-CR
titulo: "Contextual Retrieval in AI Systems"
autor: "Anthropic"
anio: 2024
url: https://www.anthropic.com/engineering/contextual-retrieval
etapas: [2]
semanas: [5]
idioma_fuente: en
tipo: guía oficial (post de ingeniería)
verificado: 2026-09-26 (texto completo leído)
vigencia: "Publicado el 19-sep-2024. El método y los principios son vigentes; los modelos (Claude 3 Haiku), el costo por millón de tokens y el umbral de 200k tokens dependen de los modelos y precios actuales."
---

# ANT-CR · Contextual Retrieval (Anthropic, 2024)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

El post sirve a la vez como introducción a RAG y como propuesta de mejora. Explica el RAG estándar: dividir documentos en fragmentos (*chunks*), convertirlos en *embeddings*, guardarlos en una base vectorial y, al preguntar, traer los más parecidos. Lo complementa con **BM25** (búsqueda por coincidencia exacta de palabras), porque los embeddings fallan con códigos o términos exactos. Luego identifica el problema principal: los fragmentos pierden su contexto ("los ingresos crecieron 3%", ¿de qué empresa y en qué trimestre?). La solución, **Contextual Retrieval**, usa un LLM para anteponer a cada fragmento una frase breve que lo sitúa en su documento, antes de indexarlo. Con reranking al final, las fallas de recuperación bajan de forma importante. Además da una regla práctica: si la base de conocimiento es chica, tal vez no se necesite RAG.

## Ideas clave

1. **Primero, ¿hace falta RAG?** Si la base de conocimiento cabe en el contexto (el post habla de menos de 200.000 tokens, unas 500 páginas), se puede incluir completa en el prompt y usar *prompt caching* para bajar costo y latencia.
2. **RAG estándar en tres pasos:** fragmentar (unos cientos de tokens por fragmento), generar embeddings y guardarlos en una base vectorial. En la consulta se buscan los fragmentos más similares y se agregan al prompt.
3. **Embeddings + BM25.** Los embeddings captan significado pero pueden perder coincidencias exactas (un código de error, un número de VIN). BM25, basado en TF-IDF, encuentra términos exactos. Se combinan los resultados de ambos (*rank fusion*).
4. **El problema del contexto perdido.** Un fragmento aislado puede no decir de qué empresa, producto o periodo habla, y entonces no se recupera cuando corresponde.
5. **Contextual Retrieval.** Un LLM genera 50–100 tokens de contexto por fragmento ("este fragmento es de X, sobre Y, en el periodo Z") y ese texto se antepone antes de crear el embedding (*Contextual Embeddings*) y el índice BM25 (*Contextual BM25*).
6. **Resultados reportados (fallas de recuperación en el top-20):**
   - contextual embeddings: −35%;
   - contextual embeddings + contextual BM25: −49%;
   - lo anterior + reranking: −67%.
7. **Reranking.** Se recupera un conjunto amplio (en el experimento, 150 fragmentos), un modelo reordenador puntúa cada uno según la consulta y se pasan los mejores 20 al LLM. Mejora la calidad a cambio de algo de latencia y costo.
8. **Consideraciones.** Importan el tamaño y los límites de los fragmentos, el modelo de embeddings y el prompt de contextualización (se puede adaptar al dominio, por ejemplo con un glosario). Pasar 20 fragmentos funcionó mejor que 5 o 10 en sus pruebas. Siempre hay que correr evals.

## Conceptos y definiciones

- **RAG (Retrieval-Augmented Generation):** recuperar información relevante de una base de conocimiento y agregarla al prompt.
- **Chunk:** fragmento de documento que se indexa por separado.
- **Embedding:** vector numérico que representa el significado de un texto.
- **Base vectorial:** almacén que permite buscar por similitud semántica.
- **BM25:** función de ranking léxico (coincidencia de términos) basada en TF-IDF.
- **Rank fusion:** combinar y deduplicar los resultados de varios buscadores.
- **Reranking:** segunda pasada que reordena candidatos según su relevancia real.
- **Prompt caching:** reutilizar una parte fija del prompt entre llamadas para ahorrar costo y latencia.
- **Recall@20:** proporción de documentos relevantes que aparecen entre los 20 primeros.

## Errores comunes

- Montar un RAG complejo cuando todo el material cabía en el contexto.
- Usar solo embeddings y fallar con búsquedas exactas (códigos de versión, número de chasis, RUT).
- Fragmentar sin pensar: fragmentos demasiado chicos pierden contexto, y demasiado grandes diluyen la señal.
- No medir: cambiar fragmentación o modelo de embeddings sin una evaluación de recuperación.
- Pensar que "RAG" equivale a "base vectorial". Hoy también se recupera con búsqueda agéntica (ver HAM-FAQ, "Is RAG dead?").

## Ejemplo aplicado: asistente de fichas técnicas y políticas comerciales

El local tiene fichas técnicas de todos los modelos Peugeot y Citroën, políticas de crédito y los boletines mensuales de precios y bonos.

- Si todo junto pesa menos que la ventana de contexto útil, conviene cargarlo completo con caching, sin RAG.
- Si crece (años de boletines, manuales de servicio), conviene un RAG híbrido: embeddings para "¿qué SUV tiene mejor maletero?" y BM25 para "código de versión 2008 GT 1.2T".
- Contextualización: el fragmento "bono de $1.500.000 hasta fin de mes" se indexa como "Boletín Peugeot septiembre 2026, modelo 2008, bono comercial: bono de $1.500.000 hasta fin de mes". Así no se confunde con el boletín de otro mes.
- Eval mínima: 30 preguntas reales de vendedores con su respuesta correcta, midiendo si el fragmento correcto aparece entre los recuperados.

## Citas cortas

- "traditional RAG solutions remove context when encoding information, which often results in the system failing to retrieve the relevant information from the knowledge base." (introducción)
- "Sometimes the simplest solution is the best." (sección sobre prompts largos)

## Notas de vigencia para el tutor

- Los porcentajes corresponden a los experimentos de Anthropic de 2024 (varios dominios, top-20). No hay que presentarlos como garantía para otros datos.
- El umbral de "200.000 tokens" depende de la ventana de contexto de cada modelo. Verificar los modelos vigentes.
- Complementar con ANT-CTX (recuperación justo a tiempo, más agéntica) y WENG-AGT (memoria de largo plazo).

## Preguntas de práctica

- P: ¿Cuándo sugiere Anthropic no usar RAG?
  R: Cuando la base de conocimiento es lo bastante chica para caber en el contexto (el post menciona menos de ~200.000 tokens, unas 500 páginas). Se incluye completa en el prompt y se usa prompt caching para reducir costo y latencia.
- P: ¿Por qué combinar embeddings con BM25?
  R: Los embeddings captan similitud de significado, pero pueden perder coincidencias exactas (códigos, identificadores). BM25 encuentra términos exactos. Combinados, recuperan mejor ambos tipos de consulta.
- P: ¿Qué problema resuelve Contextual Retrieval y cómo?
  R: Resuelve que los fragmentos pierden su contexto al separarse del documento. Un LLM genera una breve explicación (50–100 tokens) que sitúa cada fragmento en su documento, y se antepone antes de crear el embedding y el índice BM25.
- P: ¿Qué hace el reranking y cuál es su trade-off?
  R: Toma muchos candidatos recuperados (p. ej. 150), los puntúa según su relevancia para la consulta y pasa solo los mejores (p. ej. 20) al modelo. Mejora la calidad y reduce el ruido, pero agrega latencia y costo en tiempo de ejecución.
- P: En el concesionario, ¿qué consulta fallaría con solo embeddings y cómo lo corregirías?
  R: Una búsqueda por código exacto, como el código de versión de un modelo o un VIN. Se corrige agregando BM25 (búsqueda léxica) y combinando resultados. Contextualizar los fragmentos con modelo y mes del boletín evita además mezclar periodos.

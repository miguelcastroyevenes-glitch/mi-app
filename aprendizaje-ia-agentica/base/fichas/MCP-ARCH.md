---
id: MCP-ARCH
titulo: "Architecture overview — Model Context Protocol (versión 2026-07-28)"
autor: "Model Context Protocol (proyecto abierto)"
anio: 2026
url: https://modelcontextprotocol.io/docs/learn/architecture
urls_relacionadas:
  - https://modelcontextprotocol.io/specification/2026-07-28
  - https://modelcontextprotocol.io/specification/2026-07-28/changelog
etapas: [3]
semanas: [9, 10]
idioma_fuente: en
tipo: documentación oficial
licencia: MIT (repositorio modelcontextprotocol/modelcontextprotocol)
verificado: 2026-09-26 (texto completo leído; la URL redirige a /docs/2026-07-28/learn/architecture)
vigencia: "ATENCIÓN: la revisión 2026-07-28 cambió aspectos centrales respecto de 2025-11-25 (protocolo sin estado, sin handshake 'initialize', sampling y logging deprecados). Cursos y tutoriales anteriores pueden enseñar el modelo viejo."
---

# MCP-ARCH · Arquitectura de MCP (revisión 2026-07-28)

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

MCP es un protocolo abierto que estandariza **cómo una aplicación de IA obtiene contexto y herramientas de sistemas externos**. Se inspira en el Language Server Protocol, que estandarizó cómo los editores de código soportan lenguajes. Tiene tres participantes (host, cliente y servidor) y dos capas: una de **datos**, con mensajes JSON-RPC 2.0 y primitivas, y una de **transporte** (stdio local o Streamable HTTP remoto, con OAuth recomendado para autenticar). Los servidores ofrecen tres primitivas: **tools** (acciones), **resources** (datos de contexto) y **prompts** (plantillas). MCP solo define el intercambio de contexto; no dice cómo la aplicación usa el LLM. La revisión vigente (2026-07-28) hizo el protocolo **sin estado**: cada solicitud lleva su versión y capacidades, y existe un descubrimiento explícito (`server/discover`).

## Ideas clave

1. **Tres participantes.** El *host* es la aplicación de IA (Claude Code, Claude Desktop, VS Code). El host crea **un cliente MCP por cada servidor**, y el *servidor* es el programa que ofrece contexto, sea local o remoto.
2. **Dos transportes.** *stdio*: proceso local en la misma máquina, sin red, que típicamente atiende a un cliente. *Streamable HTTP*: servidor remoto que atiende a muchos clientes, con autenticación estándar (tokens, API keys) y OAuth recomendado.
3. **Primitivas del servidor.** *Tools* (funciones ejecutables: consultas, APIs, archivos), *resources* (datos de contexto: contenido de archivos, registros, esquemas) y *prompts* (plantillas reutilizables, ejemplos few-shot). Se descubren con `*/list` y las herramientas se ejecutan con `tools/call`.
4. **Primitiva del cliente: elicitation.** El servidor puede pedir más información o una confirmación al usuario. En 2026-07-28 esto ocurre con el patrón *Multi Round-Trip Requests*: el servidor responde "input_required" y el cliente reintenta con la información pedida.
5. **Sin estado (novedad 2026-07-28).** Se eliminó el handshake `initialize`. Cada solicitud lleva en `_meta` la versión del protocolo y las capacidades del cliente. Los servidores deben implementar `server/discover` (versiones, capacidades e identidad). Si una versión no es compatible, se devuelve un error que indica cuáles sí lo son.
6. **Deprecaciones 2026-07-28.** *Sampling* (que el servidor pida completions al LLM del cliente) y *logging* como primitiva quedan deprecados: se recomienda integrar directamente con la API del proveedor y registrar logs con stderr u OpenTelemetry.
7. **Notificaciones.** Son opcionales y se reciben por un stream `subscriptions/listen` (p. ej. "cambió la lista de herramientas").
8. **Extensiones opcionales.** *Tasks* (operaciones largas con consulta de estado), *Skills over MCP* (instrucciones estructuradas para flujos de agentes) y *MCP Apps* (interfaces interactivas dentro de la conversación).
9. **Seguridad y confianza (especificación).** Consentimiento explícito del usuario para acceder a datos y para invocar herramientas. Las herramientas equivalen a ejecución de código arbitrario. Las descripciones y anotaciones de herramientas se consideran no confiables salvo que vengan de un servidor confiable. El protocolo no puede imponer esto: lo deben implementar los hosts.

## Conceptos y definiciones

- **Host:** aplicación de IA que coordina uno o más clientes MCP.
- **Cliente MCP:** componente que mantiene la conexión con un servidor y obtiene contexto para el host.
- **Servidor MCP:** programa que provee tools, resources o prompts.
- **JSON-RPC 2.0:** formato de mensajes solicitud/respuesta usado por MCP.
- **Tool / Resource / Prompt:** acción ejecutable / dato de contexto / plantilla de interacción.
- **Elicitation:** solicitud del servidor para obtener información o confirmación del usuario.
- **server/discover:** llamada obligatoria (desde 2026-07-28) para conocer versiones y capacidades del servidor.

## Errores comunes

- Creer que MCP "es el agente". Es solo el protocolo para conectar contexto y herramientas; el loop y las decisiones viven en el host o el agente.
- Aprender MCP con tutoriales de 2025 y esperar el handshake `initialize` o usar *sampling* en implementaciones nuevas.
- Instalar servidores MCP de terceros sin revisar permisos. Juntar servidores con datos privados, contenido no confiable y salida externa arma la "trifecta letal" (SW-TRIF).
- Exponer como *tool* algo que debería ser *resource* (datos de solo lectura), o al revés.
- Confiar en la descripción de una herramienta de un servidor desconocido. La especificación pide tratarla como no confiable.

## Ejemplo aplicado: servidor MCP del local

Un servidor MCP interno "concesionario" podría exponer:

- **Tools:** `stock_buscar(modelo, version)`, `agenda_programar_test_drive(...)` y `cotizacion_generar(...)`. Esta última debería usar *elicitation* para pedir confirmación al vendedor antes de enviar.
- **Resources:** la lista de precios y bonos del mes (solo lectura) y la política comercial vigente.
- **Prompts:** plantilla "preparar llamada de seguimiento" con ejemplos.

Local (stdio) para pruebas en el computador de Miguel; remoto (Streamable HTTP con OAuth) si lo usa todo el equipo. Cada vendedor autoriza las herramientas que escriben datos.

## Citas cortas

- "MCP focuses solely on the protocol for context exchange—it does not dictate how AI applications use LLMs or manage the provided context." (sección "Scope")
- "Tools represent arbitrary code execution and must be treated with appropriate caution." (especificación, "Tool Safety")

## Notas de vigencia para el tutor

- MCP cambia seguido de versión (la vigente, 2026-07-28, reemplazó a 2025-11-25). Antes de enseñar detalles de mensajes, el tutor debe abrir `/specification/latest` y el changelog. Los conceptos (host/cliente/servidor, tools/resources/prompts) han sido estables.
- Curso práctico: ANT-MCP-COURSE (puede ser anterior a 2026-07-28). Visión low-code: MS-CS-MCP. Costos con muchas herramientas: ANT-CEMCP.

## Preguntas de práctica

- P: ¿Cuáles son los tres participantes de MCP y cómo se relacionan?
  R: El host (la aplicación de IA), el cliente MCP (uno por cada servidor, creado por el host) y el servidor MCP (el programa que provee contexto). El host coordina varios clientes y cada cliente mantiene la conexión con su servidor.
- P: Nombra las tres primitivas que expone un servidor y da un ejemplo del concesionario para cada una.
  R: Tools, como `agenda_programar_test_drive`. Resources, como la lista de precios del mes en solo lectura. Prompts, como la plantilla "preparar llamada de seguimiento".
- P: ¿Qué cambió de fondo en la revisión 2026-07-28?
  R: El protocolo pasó a ser sin estado: se eliminó el handshake de inicialización, cada solicitud lleva su versión y capacidades en `_meta`, los servidores deben implementar `server/discover`, y sampling y logging quedaron deprecados.
- P: ¿Cuándo usarías transporte stdio y cuándo Streamable HTTP?
  R: stdio para un servidor local en la misma máquina (pruebas o uso personal, sin red). Streamable HTTP para un servidor remoto compartido por muchos usuarios, con autenticación (se recomienda OAuth).
- P: ¿Qué principios de seguridad exige la especificación y quién debe implementarlos?
  R: Consentimiento y control del usuario sobre datos y acciones, privacidad de los datos y cautela con las herramientas (equivalen a ejecución de código; sus descripciones son no confiables salvo que vengan de un servidor confiable). El protocolo no los puede imponer: los deben implementar los hosts y desarrolladores.

---
id: A2A-SPEC
titulo: "Agent2Agent (A2A) Protocol — especificación v1.0 y 'What is A2A'"
autor: "A2A Project (Linux Foundation; creado por Google)"
anio: 2026
url: https://a2a-protocol.org/latest/specification/
urls_relacionadas:
  - https://a2a-protocol.org/latest/
  - https://a2a-protocol.org/latest/topics/what-is-a2a/
  - https://a2a-protocol.org/latest/topics/a2a-and-mcp/
  - https://a2a-protocol.org/latest/whats-new-v1/
etapas: [4]
semanas: [13]
idioma_fuente: en
tipo: especificación
licencia: Apache 2.0
verificado: 2026-09-26 (portada y especificación leídas; releases v1.0.0 del 12-mar-2026 y v1.0.1 del 28-may-2026 vistas en GitHub)
vigencia: "La v1.0 introdujo cambios incompatibles respecto de 0.3.x. Tutoriales de 2025 (incluido el anuncio de Google de abr-2025) describen versiones anteriores."
---

# A2A-SPEC · Protocolo Agent2Agent (A2A) v1.0

> Ficha de conocimiento para el tutor. Es un resumen propio y no reemplaza la fuente. Citas textuales de 1–2 frases como máximo.

## Resumen

A2A es un estándar abierto para que **agentes independientes, posiblemente "opacos"** (construidos por distintos proveedores o frameworks), se descubran, se deleguen tareas e intercambien resultados **sin compartir su memoria, herramientas ni lógica interna**. Nació en Google, fue donado a la Linux Foundation y lo gobierna un comité técnico con representantes de AWS, Cisco, Google, IBM Research, Microsoft, Salesforce, SAP y ServiceNow. Es **complementario a MCP**: MCP conecta un agente con sus herramientas y datos, y A2A conecta un agente con otros agentes. La especificación se organiza en tres capas: un modelo de datos (Task, Message, Agent Card, Part, Artifact, Extension), operaciones abstractas (enviar mensaje, consultar, listar o cancelar tareas, suscribirse, notificaciones push) y *bindings* concretos (JSON-RPC, gRPC, HTTP/REST).

## Ideas clave

1. **Problema que resuelve.** En un ecosistema con agentes de muchos proveedores, hace falta un lenguaje común para colaborar sin exponer implementaciones ni propiedad intelectual.
2. **Principios de diseño:** simple (reutiliza HTTP, JSON-RPC 2.0 y Server-Sent Events), listo para empresas (autenticación, autorización, trazabilidad), **async-first** (tareas largas y con humano en el loop), agnóstico de modalidad (texto, archivos, datos estructurados) y **ejecución opaca**.
3. **Agent Card.** Es un documento JSON que publica cada agente servidor con su identidad, capacidades, *skills*, endpoint y requisitos de autenticación. Se descubre en `https://{dominio}/.well-known/agent-card.json`, en catálogos o registros, o por configuración directa. Puede existir una versión extendida solo para clientes autenticados.
4. **Task.** Es la unidad de trabajo, con ID y ciclo de vida. Estados principales: *submitted*, *working*, *input required*, *auth required*, *completed*, *failed*, *canceled* y *rejected*. Los cuatro últimos son terminales: una tarea terminada no acepta más mensajes.
5. **Message, Part y Artifact.** Un *message* es un turno (rol user o agent) compuesto de *parts* (texto, referencias a archivos, datos estructurados). Un *artifact* es el entregable que produce la tarea.
6. **Operaciones principales:** Send Message (puede devolver una tarea o un mensaje directo), Send Streaming Message, Get Task, List Tasks, Cancel Task, Subscribe to Task, configuración de notificaciones push y Get Extended Agent Card.
7. **Tres formas de recibir avances:** consultar el estado (polling con Get Task), streaming en tiempo real o notificaciones push a un webhook del cliente, esto último para procesos largos o desconectados.
8. **Qué NO es A2A:** no es un framework para construir agentes (LangGraph, CrewAI, ADK), no es un protocolo para hablar con los propios subagentes o herramientas (para eso están las primitivas del framework o MCP), no reemplaza a MCP y no es una app de mensajería.

## Conceptos y definiciones

- **Cliente A2A:** aplicación o agente que inicia solicitudes a nombre de un usuario o sistema.
- **Servidor A2A (agente remoto):** agente que expone un endpoint compatible con A2A.
- **Agent Card:** la "tarjeta de presentación" del agente (qué hace, cómo contactarlo, qué autenticación exige).
- **Task:** unidad de trabajo con estado.
- **Artifact:** resultado generado (documento, imagen, datos).
- **Context ID:** identificador opcional para agrupar tareas y mensajes de una misma conversación.
- **Push notification:** actualización enviada por el servidor a un webhook del cliente.
- **Opaque execution:** colaborar sin revelar pensamientos, planes ni herramientas internas.

## Errores comunes

- Usar A2A para coordinar los subagentes internos del propio sistema. Para eso sirven las primitivas del framework; A2A es para agentes independientes.
- Confundir A2A con MCP. Regla simple: MCP = agente ↔ herramienta/dato; A2A = agente ↔ agente.
- Suponer que "interoperable" significa "confiable". Hay que validar la autenticación, los permisos y lo que el agente remoto devuelve: su salida es contenido no confiable para el que la recibe (ver SW-TRIF y OWASP-AG, "comunicación insegura entre agentes").
- Diseñar interacciones síncronas para tareas largas (una aprobación de crédito, por ejemplo), cuando el protocolo está pensado para asincronía con estados como *input required*.

## Ejemplo aplicado: el concesionario y una financiera externa

El agente de ventas del local (cliente A2A) necesita una preevaluación de crédito que hace un agente de una financiera (servidor A2A):

1. Lee la Agent Card de la financiera (`/.well-known/agent-card.json`) y confirma que tiene el *skill* "preevaluación automotriz" y exige OAuth.
2. Envía un mensaje con los datos mínimos (con consentimiento del cliente, según la Ley 21.719) y recibe una tarea en estado *working*.
3. La tarea pasa a *input required*: faltan las liquidaciones de sueldo. El vendedor las pide al cliente y se envían en un nuevo mensaje a la misma tarea.
4. La financiera notifica por push el paso a *completed* con un *artifact* (resultado de la preevaluación).

La financiera nunca expone su modelo de riesgo (ejecución opaca), y el concesionario no le entrega acceso a su CRM.

## Citas cortas

- "MCP is for agent-to-tool communication" / "A2A is for agent-to-agent communication" (portada, sección "How A2A Works with MCP").
- "Agents interact without needing to share internal memory, tools, or proprietary logic" (portada, "Key Features").

## Notas de vigencia para el tutor

- Versión vigente al 26-sep-2026: especificación v1.0 (release v1.0.0 del 12-mar-2026; parche v1.0.1 del 28-may-2026). Antes de enseñar detalles de mensajes, revisar "What's New in v1.0" y las release notes.
- Hay SDKs oficiales en Python, JavaScript, Java, C#/.NET, Go y Rust. Existe un curso corto gratuito de DeepLearning.AI enlazado desde la portada.
- Para la semana 13 basta dominar los conceptos (Agent Card, Task, estados, relación con MCP). El detalle de bindings es opcional.

## Preguntas de práctica

- P: ¿Qué problema resuelve A2A y en qué se diferencia de MCP?
  R: Permite que agentes independientes de distintos proveedores o frameworks se descubran, se deleguen tareas y compartan resultados sin exponer su lógica interna. MCP conecta un agente con sus herramientas y datos; A2A conecta agentes entre sí. Son complementarios.
- P: ¿Qué es una Agent Card y dónde se publica típicamente?
  R: Es un documento JSON con la identidad, capacidades, skills, endpoint y requisitos de autenticación de un agente. Se publica típicamente en `https://{dominio}/.well-known/agent-card.json`, aunque también puede estar en catálogos o configurarse directamente.
- P: Nombra los estados de una tarea A2A y cuáles son terminales.
  R: Submitted, working, input required, auth required, completed, failed, canceled y rejected. Son terminales completed, failed, canceled y rejected.
- P: ¿Qué significa "ejecución opaca" y por qué le importa a una empresa?
  R: Que los agentes colaboran según capacidades declaradas e información intercambiada, sin compartir pensamientos, planes, memoria ni herramientas internas. Protege la propiedad intelectual y la seguridad de cada organización.
- P: ¿Por qué no usarías A2A para coordinar los subagentes de tu propio AI Sales Team?
  R: Porque A2A es para agentes independientes y opacos entre organizaciones o sistemas distintos. Para los subagentes internos conviene usar las primitivas del framework (handoffs, agentes como herramientas), que son más simples y comparten contexto.

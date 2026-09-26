# Tutor de IA Agéntica

Un agente tutor que te lleva por la malla de 24 semanas (`malla-curricular.html`), una sesión corta a la vez: te dice qué toca hoy, te toma repasos, te da feedback honesto y **solo te deja avanzar cuando demuestras** lo aprendido. Si pierdes días, te ayuda a retomar sin culpa.

## Primer día (10 minutos)

1. Abre Claude Code en este repo y escribe: **"sesión de hoy"**.
2. El tutor te responde con *Quedamos en · Hoy · Primero* y te plantea el objetivo de la semana 1.
3. Tú intentas primero; él corrige. Si hoy no da el tiempo, di **"solo tengo 15 minutos"** (modo micro).
4. Al cerrar, registra la sesión con un *si-entonces* ("Si es lunes 21:00 y cierro el local, entonces abro el tutor…") y hace commit de tu progreso.
5. Para ver tu avance: di **"cómo voy"** o abre `progreso/panel.html` (tu Hoja de Combate del aprendizaje).

Frases útiles: "sesión de hoy", "estudiemos", "repaso", "retomar", "cómo voy", "quiero aprobar la semana".

## Comandos (desde `aprendizaje-ia-agentica/`)

| Comando | Qué hace |
|---|---|
| `python3 herramientas/tutor.py estado` | dónde vas, racha, repasos vencidos, próximo paso |
| `python3 herramientas/tutor.py hoy --micro` | plan de hoy (`--micro` 15 min, `--estandar` 30, `--lab` 75) |
| `python3 herramientas/tutor.py repaso` | preguntas vencidas (repetición espaciada) |
| `python3 herramientas/tutor.py registrar --minutos 30 --nota "..."` | anota la sesión en la bitácora |
| `python3 herramientas/tutor.py aprobar-semana 1 --evidencia "..." --rubrica "..."` | avanza solo con evidencia y rúbrica |
| `python3 herramientas/tutor.py retomar` | plan de retorno si estuviste fuera |
| `python3 herramientas/tutor.py pausa --hasta 2027-01-20` | vacaciones: congela la racha |
| `python3 herramientas/tutor.py panel` | genera `progreso/panel.html` |

Reglas del juego: cada semana de contenido tiene 4 pasos (entender, construir, cerrar el laboratorio, demostrar). La racha es semanal: 3 sesiones o 60 min (en cierre de mes, 2 o 30), con 1 comodín al mes. Los proyectos (semanas 3, 6, 10, 14, 19 y 24) se aprueban con el archivo o la URL del entregable y un checkpoint sin IA. Jueves a domingo no cuentan como días perdidos.

**Ojo con la privacidad:** `progreso/` se versiona en este repo. Si el repo es público, tu bitácora y tu panel también lo son. No anotes datos de clientes ni cifras de la empresa, o mueve el progreso a un repo privado con `TUTOR_PROGRESO=/ruta/privada`.

## Usarlo en claude.ai (celular o web)

1. En Claude Code: `python3 herramientas/tutor.py empaquetar-skill` → crea `dist/tutor-ia-agentica.zip` (la skill + la malla + la base de fuentes).
2. En claude.ai: **Configuración → Capacidades → Skills → Subir skill** y elige ese zip (requiere tener habilitada la ejecución de código; si el menú cambió de nombre, busca "Skills").
3. En una conversación nueva di "sesión de hoy" y pega tu bloque de estado (`python3 herramientas/tutor.py bloque` lo imprime).
4. Al final, el tutor te entrega un bloque `ESTADO-TUTOR` actualizado: guárdalo y, de vuelta en Claude Code, sincronízalo con `python3 herramientas/tutor.py importar` (pegas el bloque y terminas con Ctrl+D).

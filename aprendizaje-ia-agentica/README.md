# Tutor de IA Agéntica

Un agente tutor que te lleva por la malla de 24 semanas (`malla-curricular.html`), una sesión corta a la vez: te dice qué toca hoy, te toma repasos, te da feedback honesto y **solo te deja avanzar cuando demuestras** lo aprendido. Si pierdes días, te ayuda a retomar sin culpa.

## Primer día (10 minutos)

1. Abre Claude Code en este repo y escribe: **"sesión de hoy"**.
2. El tutor corre `estado` y `hoy`, y te propone el objetivo único de la semana 1.
3. Tú intentas primero; él corrige. Si hoy no da el tiempo, di **"solo tengo 15 minutos"** (modo micro).
4. Al terminar, el tutor registra la sesión y hace commit de tu progreso.
5. Para ver tu avance: di **"cómo voy"** o abre `progreso/panel.html`.

Frases útiles: "sesión de hoy", "estudiemos", "repaso", "retomar" (después de días sin estudiar), "cómo voy", "quiero aprobar la semana".

## Comandos (desde `aprendizaje-ia-agentica/`)

| Comando | Qué hace |
|---|---|
| `python3 herramientas/tutor.py estado` | dónde vas, racha, repasos vencidos, próximo paso |
| `python3 herramientas/tutor.py hoy --micro` | plan de hoy (`--micro` 15 min, `--estandar` 45, `--lab` 90) |
| `python3 herramientas/tutor.py repaso` | preguntas vencidas (repetición espaciada) |
| `python3 herramientas/tutor.py registrar --minutos 30 --nota "..."` | anota la sesión |
| `python3 herramientas/tutor.py aprobar-semana 1 --evidencia "..."` | avanza solo con evidencia |
| `python3 herramientas/tutor.py retomar` | plan de retorno según los días que estuviste fuera |
| `python3 herramientas/tutor.py panel` | genera `progreso/panel.html` |
| `python3 herramientas/tutor.py validar` | revisa que todo el programa esté sano |

Reglas del juego: 8–10 h por semana en sesiones cortas; cada semana trae 2 comodines para la racha; los proyectos (semanas 3, 6, 10, 14, 19 y 24) se aprueban con el archivo o la URL del entregable.

## Usarlo en claude.ai (celular o web)

1. En Claude Code: `python3 herramientas/tutor.py empaquetar-skill` → crea `dist/tutor-ia-agentica.zip` (la skill + la malla).
2. En claude.ai: **Configuración → Capacidades → Skills → Subir skill** y elige ese zip (requiere tener habilitada la ejecución de código; revisa el menú actual si cambió de nombre).
3. En una conversación nueva di "sesión de hoy" y pega tu bloque de estado (`python3 herramientas/tutor.py bloque` lo imprime).
4. Al final, el tutor te entrega un bloque `ESTADO-TUTOR` actualizado: guárdalo y, de vuelta en Claude Code, sincronízalo con `python3 herramientas/tutor.py importar` (pegas el bloque y terminas con Ctrl+D).

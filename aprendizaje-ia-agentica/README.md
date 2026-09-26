# Tutor de IA Agéntica

Un agente tutor que te lleva por la malla de 24 semanas (`malla-curricular.html`), una sesión corta a la vez: te dice qué toca hoy, te toma repasos, te da feedback honesto y **solo te deja avanzar cuando demuestras** lo aprendido. Si pierdes días, te ayuda a retomar sin culpa.

## Primer día (10 minutos)

1. Abre Claude Code en esta carpeta (o en tu repo propio, ver abajo) y escribe: **"sesión de hoy"**.
2. El tutor te responde con *Quedamos en · Hoy · Primero* y te plantea el objetivo de la semana 1.
3. Tú intentas primero; él corrige. Si hoy no da el tiempo, di **"solo tengo 15 minutos"** (modo micro).
4. Al cerrar, registra la sesión con un *si-entonces* ("Si es lunes 21:00 y cierro el local, entonces abro el tutor…") y hace commit de tu progreso.
5. Para ver tu avance: di **"cómo voy"** o abre `progreso/panel.html` (tu Hoja de Combate del aprendizaje).

Frases útiles: "sesión de hoy", "estudiemos", "repaso", "retomar", "cómo voy", "quiero aprobar la semana".

**Hook y skill:** `.claude/settings.json` trae un hook que corre `tutor.py estado` al abrir la sesión, y `.claude/skills/` trae la skill del tutor. Claude Code los carga solo cuando se abre **en esta carpeta** o en un repo propio donde esta carpeta sea la raíz. Abierto en la raíz de `mi-app`, no se cargan solos (ver "Mientras tanto").

## Comandos (desde esta carpeta)

| Comando | Qué hace |
|---|---|
| `python3 herramientas/tutor.py estado` | dónde vas, racha, repasos vencidos, próximo paso |
| `python3 herramientas/tutor.py hoy --micro` | plan de hoy (`--micro` 15 min, `--estandar` 30, `--lab` 75) |
| `python3 herramientas/tutor.py repaso` | preguntas vencidas (repetición espaciada) |
| `python3 herramientas/tutor.py registrar --minutos 30 --nota "..."` | anota la sesión en la bitácora |
| `python3 herramientas/tutor.py aprobar-semana 1 --evidencia "..." --rubrica "..."` | avanza solo con evidencia y rúbrica |
| `python3 herramientas/tutor.py retomar` | plan de retorno si estuviste fuera |
| `python3 herramientas/tutor.py pausa --hasta 2027-01-20` | vacaciones: congela la racha |
| `python3 herramientas/tutor.py piso --sesiones 2 --minutos 45` | ajusta tu piso semanal desde esta semana |
| `python3 herramientas/tutor.py panel` | genera `progreso/panel.html` |

Reglas del juego: cada semana de contenido tiene 4 pasos (entender, construir, cerrar el laboratorio, demostrar) y un *hilo de calidad* de 5–10 min (una prueba o un ataque sobre lo que construyes). La racha es semanal: 3 sesiones o 60 min (en cierre de mes, 2 o 30), con 1 comodín al mes. Los proyectos (semanas 3, 6, 10, 14, 19 y 24) se aprueban con el archivo o la URL del entregable y un checkpoint sin IA. Jueves a domingo no cuentan como días perdidos.

## Recomendado: moverlo a un repo privado propio

- **Privacidad:** `mi-app` es público, así que tu bitácora, tus notas y tu panel quedarían públicos al hacer commit.
- **Comodidad:** en un repo propio, la skill (`.claude/skills/`) y el hook (`.claude/settings.json`) quedan en la raíz y se cargan solos al abrir Claude Code.

Cómo: crea en GitHub un repo **privado** (por ejemplo `tutor-ia-agentica`), copia a su raíz todo el contenido de esta carpeta (incluidas `.claude/` y `.gitignore`), haz commit y push, y conéctalo a Claude Code en la nube. Luego borra de `mi-app` la carpeta `progreso/`, o la carpeta entera.

## Mientras tanto, desde una sesión en la nube de mi-app

Escribe exactamente: **"Lee aprendizaje-ia-agentica/CLAUDE.md y hagamos la sesión de hoy"**. Claude entra a la carpeta, corre `estado` y sigue la skill. Antes del commit, recuerda que en `mi-app` tu progreso queda público.

## Usarlo en claude.ai (celular o web)

1. En Claude Code: `python3 herramientas/tutor.py empaquetar-skill` → crea `dist/tutor-ia-agentica.zip` (skill, malla, base de fuentes y reglas completas).
2. En claude.ai: **Configuración → Capacidades → Skills → Subir skill** y elige ese zip (requiere tener habilitada la ejecución de código; si el menú cambió de nombre, busca "Skills").
3. En una conversación nueva di "sesión de hoy" y pega tu bloque de estado (`python3 herramientas/tutor.py bloque` lo imprime).
4. Al final, el tutor te entrega un bloque `ESTADO-TUTOR` actualizado: guárdalo y, de vuelta en Claude Code, sincronízalo con `python3 herramientas/tutor.py importar` (pegas el bloque y terminas con Ctrl+D).

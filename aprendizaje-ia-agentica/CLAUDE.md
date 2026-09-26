# Aprendizaje IA Agéntica — contexto para Claude Code

Proyecto de estudio personal de Miguel Ángel (Jefe de Local, concesionario Peugeot/Citroën, Chile): un curso de IA agéntica de 24 semanas con un **agente tutor**. Todo en español de Chile.

## Cómo arrancar

- Si Miguel dice "sesión de hoy", "tutor", "estudiemos", "repaso", "retomar" o "cómo voy": usa la skill `tutor-ia-agentica` (`.claude/skills/tutor-ia-agentica/SKILL.md`) y sigue su protocolo.
- Arranque en frío, desde esta carpeta: `python3 herramientas/tutor.py estado` y luego `python3 herramientas/tutor.py hoy`.

## Estructura

| Ruta | Qué es |
|---|---|
| `malla-curricular.html` | malla original (fuente de verdad del diseño) |
| `curriculo/malla.json` | la malla como datos: 6 etapas, 24 semanas |
| `base/` | fuentes (`fuentes.json`) y fichas de lectura (`fichas/<ID>.md`) |
| `herramientas/tutor.py` | CLI determinística del tutor (solo biblioteca estándar) |
| `herramientas/simular.py` | simula a un estudiante recorriendo las 24 semanas |
| `progreso/` | memoria del estudiante: `estado.json`, `tarjetas.json`, `bitacora.md`, `panel.html` |
| `tests/test_tutor.py` | pruebas (unittest) |
| `investigacion/` | investigación de apoyo (crítica, base de conocimiento, reglas del tutor) |
| `privado/` | no se versiona |

## Reglas del proyecto

- Lo determinístico lo hace `tutor.py` (fechas, racha, repasos, qué toca hoy, aprobaciones). No edites `progreso/*.json` a mano.
- `herramientas/` usa solo la biblioteca estándar de Python 3.
- Antes de commitear cambios en `curriculo/`, `base/`, `herramientas/` o la skill, corre:
  `python3 herramientas/tutor.py validar`, `python3 herramientas/simular.py` y `python3 -m unittest discover -s tests`.
- Al cerrar una sesión de estudio: registrar con `tutor.py` y commit de `progreso/` (mensaje `tutor: semana N, sesión AAAA-MM-DD`).
- No subas datos de clientes (RUT, teléfonos, correos, rentas) al repo: en los laboratorios se usan datos anonimizados o simulados.
- Para probar con otra fecha: `--hoy AAAA-MM-DD` o `TUTOR_HOY=AAAA-MM-DD`. Para otra carpeta: `--raiz` o `TUTOR_RAIZ`.

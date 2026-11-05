# Switch Power para Codex

[English](README.md) · [Español](README.es.md) · [Русский](README.ru.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

Switch Power ayuda a Codex a decidir cómo ejecutar cada solicitud. El chat principal evalúa la tarea, delega en subagentes nativos cuando resulta útil, comprueba los resultados y responde en la misma conversación. Cada solicitud se evalúa de nuevo.

Luna con nivel `low` puede ser suficiente para contar archivos. Terra puede ser adecuado para una revisión visual y Sol para una auditoría compleja. La elección depende de los modelos disponibles, las herramientas, la dificultad y el coste de un error. Sol, Terra y Luna con nivel `low`, `medium` o `high` están preautorizados. Astra y los niveles superiores a `high` requieren consentimiento explícito para la tarea y el alcance actuales.

## Instalación

La versión 0.1.2 requiere Python 3.11+ y Codex CLI con `plugin marketplace`, `plugin add` y los métodos `model/list`, `skills/list` y `hooks/list`. Ejecuta el comando desde la raíz del repositorio o del archivo ZIP extraído.

**macOS y Linux**

```bash
python3 scripts/setup.py
```

**Windows (PowerShell, Codex nativo)**

```powershell
py -3 scripts/setup.py
```

Si Python está disponible como `python`, úsalo en lugar de `py -3`. Si el instalador no encuentra Codex, pasa `--codex` con la ruta completa a `codex.exe`. La opción `--coordinator` configura GPT‑6.1 Sol con nivel `high` como valor predeterminado.

Después de instalar, abre `/hooks` en Codex CLI, revisa los hooks de Switch Power y aprueba los que quieras activar. Inicia una nueva sesión de Codex. El complemento se registra en tu perfil y añade un bloque administrado al archivo global `AGENTS.md` o `AGENTS.override.md`.

## Uso

Escribe una solicitud normal, por ejemplo «Cuenta los archivos `.py` de `scripts/`». El coordinador realiza directamente las lecturas, los recuentos y las comparaciones breves. Delega cuando el beneficio previsto justifica el inicio y la revisión, o si le pides un subagente. En la interfaz V2 verificada, el subagente recibe un encargo con el contexto necesario mediante `fork_turns: "none"`. Codex controla el modelo del chat principal.

## Modelo y consumo de tokens

Switch Power 0.1.4 muestra un aviso de Codex tras la respuesta con los modelos y los tokens registrados para el coordinador y los subagentes asociados. Aprueba los nuevos hooks en **Settings → Hooks** o mediante `/hooks` en la CLI. Si faltan contadores, el aviso indica `partial` o `token usage unavailable`. La posición del aviso depende del cliente de Codex. [Resultados y pasos para reproducir la medición](docs/usage-benchmark.md).

En seis pares nuevos, 0.1.4 consumió en total un 11,0% menos de tokens que Sol/high por sí solo. El complemento resolvió todas las tareas sin subagentes.

## Desactivar o eliminar

Ejecuta `python3 scripts/install.py disable` desde el proyecto para desactivar el complemento. Usa `enable` para volver a activarlo o `remove` para desinstalarlo. En Windows, sustituye `python3` por `py -3`. `scripts/configure.py restore` restaura por separado el modelo y el nivel de razonamiento del coordinador.

La versión 0.1.2 superó 31 pruebas y una instalación limpia en macOS. Falta comprobar de extremo a extremo el funcionamiento en Codex nativo para Windows. Consulta los [resultados de verificación](docs/verification.es.md) y la [arquitectura](docs/architecture.es.md).

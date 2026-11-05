# Arquitectura de Switch Power

El coordinador recibe cada solicitud en el chat principal. Al delegar, contrasta el catálogo actual de modelos con el esquema de la herramienta de lanzamiento. Elige el ejecutor y el nivel de razonamiento, delimita el trabajo, verifica el consentimiento e inicia el subagente con la herramienta nativa. Revisa el resultado y responde en el chat original.

| Componente | Función |
| --- | --- |
| [`skills/coordinate`](../plugins/switch-power/skills/coordinate/SKILL.md) | Selección de ejecutores, coordinación y revisión del resultado. |
| [`scripts/policy.py`](../plugins/switch-power/scripts/policy.py) | Comprobaciones de disponibilidad, consentimiento y alcance. |
| [`scripts/runtime.py`](../plugins/switch-power/scripts/runtime.py) | Catálogo nativo, estado local y CLI de verificación. |
| [`hooks/guard.py`](../plugins/switch-power/hooks/guard.py) | Eventos de Codex y control de lanzamientos mediante `PreToolUse`. |
| [`scripts/install.py`](../scripts/install.py) | Instalación global, desactivación y desinstalación. |
| [`scripts/configure.py`](../scripts/configure.py) | Configura o restaura el modelo del chat principal. |

## Ciclo de una tarea

1. El coordinador realiza directamente el trabajo local breve. Antes de delegar, sopesa el beneficio frente a la preparación, el trabajo del subagente y la revisión. Una solicitud explícita de un subagente sigue las comprobaciones habituales de consentimiento.
2. Para delegar, la CLI registra la tarea y el alcance. La llamada nativa especifica el modelo y el nivel de razonamiento cuando el esquema de Codex los admite.
3. Astra y los niveles superiores a `high` requieren consentimiento para el modelo, el nivel y el alcance exactos. El consentimiento se limita a la tarea actual. Una tarea independiente inicia un nuevo ciclo.
4. El coordinador recibe el resultado mediante el ciclo nativo, lo verifica y responde. El comando `finish` limpia el estado de la tarea.

La configuración de Codex determina el modelo principal. Los parámetros nativos del subagente seleccionan el ejecutor de un trabajo concreto. El chat principal recibe y reevalúa la siguiente solicitud.

En el esquema V2 verificado, al especificar modelo y nivel se usa `fork_turns: "none"`. El coordinador incluye el contexto necesario, las restricciones y los criterios de aceptación en el encargo.

## Catálogo y estado

El instalador obtiene el catálogo mediante `model/list`. Al preparar una delegación, la CLI actualiza los datos caducados y comprueba su antigüedad y compatibilidad con el esquema de lanzamiento.

El estado de la tarea se guarda en un directorio temporal privado del usuario. Contiene el alcance y la solicitud más reciente para vincular el consentimiento. El catálogo se guarda por separado en el perfil de Codex. [Referencia de comandos](../plugins/switch-power/skills/coordinate/references/runtime.md).

## Diagnóstico

Ejecuta `python3 scripts/verify_native.py` desde el clon o el archivo extraído. En Windows usa `py -3 scripts/verify_native.py`. El comando comprueba la detección de la habilidad y el estado de los hooks en dos directorios. Si un hook necesario figura como `untrusted`, revisa su definición con `/hooks` en Codex CLI. Si el lanzamiento nativo falla, el coordinador explica el motivo y elige una ruta disponible.

La cobertura de los hooks depende de la ruta de herramientas de Codex. El coordinador interpreta el alcance de la tarea y el consentimiento del usuario. [Informe de verificación](verification.es.md).

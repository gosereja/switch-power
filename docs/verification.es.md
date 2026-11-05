# Verificación de Switch Power

## Versiones 0.1.3 y 0.1.4

La versión 0.1.3 añadió el aviso de tokens. Un Codex App Server en funcionamiento confirmó los totales de respuestas directas y delegadas. La versión 0.1.4 resuelve las tareas breves directamente salvo que compense delegarlas. Superó 38 pruebas y una actualización desde el archivo en un perfil aislado. Las 12 ejecuciones comparativas devolvieron las respuestas esperadas con contadores completos. Una solicitud explícita independiente lanzó Luna/low correctamente. [Método y resultados](usage-benchmark.md).

## Versión 0.1.2

Se añadió la instalación desde PowerShell con `codex.exe` nativo, el bloqueo de estado en Windows, los canales multiplataforma de App Server y comandos de hooks compatibles con espacios y apóstrofos en rutas. En macOS pasaron 31 pruebas. También se verificaron la instalación en un perfil limpio con un solo comando desde el archivo, la configuración de Sol/high y la detección de la habilidad desde dos directorios. Los comandos de Windows pasaron las pruebas de generación. Queda pendiente la prueba integral con Codex nativo en Windows.

## Versión 0.1.1

Cada solicitud se evaluaba de nuevo. La versión prefería un subagente ligero para trabajos sencillos delegados, mientras Sol/high coordinaba y revisaba el resultado en el chat original. El entorno aislado bloqueó la escritura bajo `~/.codex` y el App Server hijo falló al inicializar SQLite. La corrección trasladó el estado a un directorio temporal privado y reutilizó un catálogo reciente. El perfil personal detectó la actualización y cuatro hooks de confianza en dos directorios.

Pasaron 29 pruebas. El catálogo contenía diez modelos. Se registró un alcance, se autorizó Luna/low y Codex aceptó el lanzamiento nativo. El subagente devolvió cinco archivos Python de `scripts/`, lo mismo que el recuento independiente. En esa etapa quedaban pendientes una prueba del segundo turno y la certificación del modelo en el backend.

## Verificación inicial de la versión 0.1.0

Las pruebas se realizaron el 5 de noviembre de 2026 (Europe/Podgorica) con Codex CLI 0.166.0-alpha.6, incluido en la aplicación de escritorio.

- Se integró el GitHub Spec Kit oficial 1.3.1.dev0 en el commit `ec9a6f3b94c0aa856f77e550785a1ddde1993de1`. Se crearon la constitución, los requisitos, el plan, la investigación, el modelo de datos, los contratos y las tareas. La comprobación de requisitos previos pasó.
- Se generaron los esquemas de App Server y se revisó la herramienta de lanzamiento real. `model/list` devolvió diez modelos sin abrir chats de usuario, entre ellos gpt-reserve, variantes anteriores de 5.6 y codex-auto-review. El esquema de lanzamiento admitía cinco modelos. Se usa la intersección.
- Un subagente nativo Sol/high aceptó una investigación de solo lectura y devolvió un resultado final. Se indicaron el modelo y el nivel. La certificación del backend no estaba disponible.
- La instalación del catálogo y del complemento funcionó en un `CODEX_HOME` aislado. Se detectó `switch-power:coordinate` como habilidad activa de usuario en dos directorios independientes.
- Esa versión de Codex no detectó los hooks empaquetados, incluso con el manifiesto de compatibilidad. El respaldo mediante `hooks.json` de usuario detectó cuatro hooks en ambos directorios sin errores. Estaban pendientes de aprobación. El instalador comprueba ese respaldo.
- Veintisiete pruebas cubrieron la política, JSON de CLI y hooks, estado, bloqueos, instalación, conservación de ajustes, consentimiento directo, alcance y modelo/nivel exactos, lanzamientos restringidos, catálogos caducados o modelos ausentes, reutilización de solicitudes anteriores, errores del subagente, estado inválido y eventos incompletos.
- En un perfil aislado se verificaron la instalación desde el archivo, desactivar → activar → eliminar y volver a detectar. Desactivar o eliminar retiró la habilidad, los hooks y el bloque AGENTS. Dos compilaciones del mismo código generaron ZIP idénticos y se verificó `SHA256SUMS`.
- Se verificó aplicar → inspeccionar → actualizar sin cambios → leer la configuración → restaurar el modelo principal. Codex confirmó gpt-6.1-sol/high. La prueba no cambió el perfil personal.
- Una revisión Sol/high encontró dos defectos en TOML multilínea y en la desactivación tras cambiar Python. Se reprodujeron con pruebas fallidas y se corrigieron. La segunda revisión cubrió 27 pruebas, casos TOML adicionales, aplicación/restauración e instalación/reinstalación/desactivación, sin nuevas observaciones.
- Un subagente nativo Luna/medium leyó la habilidad y acertó en diez casos de trabajo simple y visual, Astra sin consentimiento, Astra/xhigh explícito, tareas independientes, instrucciones en README, aprobación de propuestas, catálogo incompatible, autoinforme del backend y parámetros ausentes. Fue una comprobación de comportamiento.

[Detección activa](evidence/native-enabled.json) · [Detección desactivada](evidence/native-disabled.json) · [Configuración del coordinador](evidence/coordinator-config.json) · [Catálogo](evidence/catalogue.json). Se usaron conexiones de diagnóstico a App Server y no se crearon chats de usuario.

## Coherencia con Spec Kit

Se cotejaron requisitos, plan, tareas, constitución y rutas. Las tareas cubrieron los 14 requisitos, sin conflictos con la constitución ni marcadores pendientes. La cobertura de tareas y la verificación en vivo se registran por separado.

| Requisito | Tareas | Evidencia principal |
| --- | --- | --- |
| FR-001 | T005, T007, T009 | Activación global y detección en distintos directorios |
| FR-002 | T001, T004, T005 | Modelo, nivel, fork y ejecuciones reales con Sol y Luna |
| FR-003 | T001, T004, T008 | Catálogo nativo e intersección con el esquema de lanzamiento |
| FR-004 | T003, T004 | Familias y niveles preautorizados |
| FR-005 | T003, T004, T005 | Bloqueo y consentimiento. Interceptación real pendiente en esa etapa |
| FR-006 | T003, T004, T005 | Alcance, consentimiento directo y propuestas |
| FR-007 | T003, T004, T005 | Reinicio, reutilización y origen de la evidencia |
| FR-008 | T004, T005 | Tarea, alcance y reglas de `SubagentStart`. Ruta recursiva pendiente |
| FR-009 | T003, T004, T005 | Lanzamientos no disponibles o fallidos y recuperación limitada |
| FR-010 | T006, T007 | Lectura y restauración de configuración nativa |
| FR-011 | T004, T008 | Metadatos de actualización y prueba sin cambios |
| FR-012 | T007, T009 | Instalar, detectar, desactivar, activar y eliminar |
| FR-013 | T009, T010 | Pruebas, verificación del archivo y límites |
| FR-014 | T001, T002, T010 | Integración local oficial y revisión de coherencia |

## Límites de la verificación en vivo

- Durante el desarrollo no se ejecutó Astra ni se usaron niveles superiores a `high`. Se probaron esos casos con entradas controladas de la política y los hooks.
- En la etapa 0.1.0 quedaban pendientes la interceptación real tras la aprobación de hooks, la interceptación recursiva y los nombres de herramientas con espacio de nombres en eventos reales. Las pruebas posteriores se describen arriba y en el informe de consumo.
- Se verificaron la detección de la habilidad y el bloque AGENTS sin crear chats de usuario. La presentación en escritorio y el comportamiento en turnos sucesivos requieren verificación en el cliente de destino.
- Los resultados del lanzamiento y los autoinformes son insuficientes para certificar el modelo o nivel en el backend. El coordinador interpreta las tareas independientes y el consentimiento. Una cita con `source=live_user` vincula la evidencia a un turno.
- El catálogo probado no ofrecía `upgrade` ni `upgradeInfo` para Sol. La prueba nativa verificó el comportamiento seguro sin cambios.
- Windows nativo, la orquestación remota o en la nube, las políticas de espacios administrados y las rutas de herramientas especializadas quedan fuera del alcance verificado. La cobertura de los hooks depende del entorno.

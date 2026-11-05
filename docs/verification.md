# Проверка Switch Power

## Обновление 0.1.2

Добавлена установка из PowerShell с нативным `codex.exe`. Для состояния
используются блокировки Windows, а app-server обменивается сообщениями через
каналы, доступные на обеих платформах. Установщик формирует Windows-команды
обработчиков для путей с пробелами и апострофами.

На macOS прошёл 31 тест. Отдельно проверена установка из архива одной командой
в чистый профиль, настройка Sol/high и обнаружение навыка в двух каталогах.
Формирование Windows-команд проверено тестами. Сквозной запуск в Windows Codex
ещё предстоит проверить.

## Обновление 0.1.1

Обычный запрос оценивается заново. Для простых задач с отдельным исполнением
навык предпочитает лёгкого субагента. Sol/high принимает запрос, выбирает
маршрут и возвращает проверенный результат в исходный чат.

В песочнице воспроизведены запрет записи состояния в `~/.codex` и отказ
дочернего app-server при инициализации SQLite. Исправление использует приватный
временный каталог для состояния и свежий снимок нативного каталога моделей.
Штатное обновление обнаружило 0.1.1 в личном профиле. Все четыре обработчика
имеют статус trusted в двух проверенных каталогах.

Прошли 29 тестов. В текущей песочнице прочитан каталог из 10 моделей,
зарегистрирована область проверки и разрешён Luna/low. Штатный вызов с этими
параметрами принят. Субагент вернул список из пяти Python-файлов в `scripts/`,
который совпал с независимым подсчётом. Выбор на следующем пользовательском
ходе описан в навыке. Отдельная живая проверка второго хода и backend-аттестация
модели остаются открытыми.

## Исходная проверка 0.1.0

Дата: 2026-11-05, Europe/Podgorica. Проверенная версия: Codex CLI
0.166.0-alpha.6, поставляемая с установленным настольным приложением.

## Выполнено

- Локально подключён официальный GitHub Spec Kit 1.3.1.dev0, commit
  ec9a6f3b94c0aa856f77e550785a1ddde1993de1. Созданы constitution, spec, plan,
  research, data model, contracts и tasks. Штатный check-prerequisites проходит.
- Сгенерированы JSON schemas установленного app-server, просмотрена реальная
  схема spawn. Live model/list прочитан без создания новых чатов: десять моделей.
  Среди них gpt-reserve, старые 5.6 и codex-auto-review; текущий spawn допускает
  пять моделей. Совместимость определяется пересечением, а не API-списком.
- Реальный Sol/high субагент принял read-only задачу исследования и вернул обычный
  final через штатный lifecycle. Параметры запрошены явно, backend не аттестован.
- В изолированном CODEX_HOME штатные marketplace add и plugin add приняли пакет.
  Native skills/list обнаруживает `switch-power:coordinate`, scope user, enabled
  true в двух посторонних каталогах, без новых чатов.
- Bundled hooks не обнаружились в этой версии, в том числе с поддерживаемым
  compatibility manifest. Переход на штатный пользовательский hooks.json дал
  четыре обнаруженных обработчика без loader errors в обоих каталогах.
  Trust status — untrusted. Установщик проверяет этот fallback автоматически.
- **27 тестов проходят**. Тесты локального policy, CLI/hook JSON, состояния, блокировок, установки и
  сохранения чужих настроек выполняются через unittest. Проверяются direct consent,
  точный scope/tuple, запрет Astra/повышенного effort, отсутствие/устаревание модели,
  сброс и невозможность переноса старого prompt в новую задачу, ошибка агента,
  испорченный state и неполное событие prompt.
- Установка из распакованного release-архива, disable → enable → remove и повторное
  native обнаружение прошли в отдельном CODEX_HOME. После disable/remove skill,
  собственные hooks и AGENTS-блок отсутствуют. Две сборки одинакового состояния
  дают побайтно одинаковый ZIP; проверены внутренние SHA256SUMS.
- Отдельная настройка main model проверена нативно в изолированном профиле:
  apply → inspect → upgrade(no-op) → config/read → restore. Codex config/read
  подтвердил gpt-6.1-sol/high; пользовательский основной профиль не изменялся.
- Независимый Sol/high code review выявил два дефекта (многострочный TOML и
  отключение после смены Python). Оба воспроизведены failing tests и исправлены;
  повторный review проверил 27 тестов, дополнительные TOML-сценарии, apply/restore
  и install/reinstall/disable, новых замечаний не нашёл.
- Реальный Luna/medium агент прочитал skill и дал ожидаемые решения в десяти
  сценариях: простая работа, визуальная задача, срочная Astra без согласия,
  direct Astra/xhigh, новая задача, инструкция в README, согласие на предложение,
  несовместимый каталог, backend self-report и отсутствие параметров запуска.
  Это одна поведенческая проверка, не статистическое доказательство стабильности.

Машинные свидетельства: [native enabled](evidence/native-enabled.json),
[native disabled](evidence/native-disabled.json),
[coordinator config](evidence/coordinator-config.json),
[catalogue](evidence/catalogue.json). Все проверки создавали диагностические
app-server подключения, а не новые пользовательские чаты.

## Согласованность по Spec Kit

Проверены spec/plan/tasks/constitution и фактические пути. Покрытие задачами:
14/14 FR (100%); требований без задач — 0; конфликтов constitution — 0;
незавершённых placeholder — 0. Покрытие задачами не означает полную живую проверку.

| Требование | Задачи | Основное свидетельство |
|---|---|---|
| FR-001 | T005,T007,T009 | global bootstrap + native cross-directory discovery |
| FR-002 | T001,T004,T005 | explicit model/effort/fork checks, live Sol/Luna launches |
| FR-003 | T001,T004,T008 | native catalogue + spawn intersection tests |
| FR-004 | T003,T004 | automatic-family/effort tests |
| FR-005 | T003,T004,T005 | deny/consent tests; live interception still unverified |
| FR-006 | T003,T004,T005 | exact tuple/scope, direct and proposal consent tests |
| FR-007 | T003,T004,T005 | reset/replay/provenance tests; semantic duty documented |
| FR-008 | T004,T005 | root task/scope validation + SubagentStart rules; recursive live path unverified |
| FR-009 | T003,T004,T005 | unavailable/failed tuple tests and bounded recovery instructions |
| FR-010 | T006,T007 | separate native config/read + restore |
| FR-011 | T004,T008 | vendor-pointer unit tests + live no-op |
| FR-012 | T007,T009 | native install, discover, disable, enable, remove |
| FR-013 | T009,T010 | executable tests, archive checks and explicit limits below |
| FR-014 | T001,T002,T010 | official local integration and consistency review |

## Границы живой проверки

- Не запускались реальные Astra или усилия выше high: пользователь не разрешал
  тратить их на разработку. Их запреты и разрешения проверяются локальными
  исполнениями policy/hook с контролируемыми payload, без расходов модели.
- Hooks не подтверждались автоматически. Перехват **реального** spawn после
  пользовательского trust, recursive interception и namespaced tool_name в
  actual hook payload остаются непроверенными.
- Новые пользовательские чаты не создавались. Обнаружение skill и наличие
  глобального AGENTS-блока проверены; его фактическая инъекция и поведение полного
  автоматического workflow в новой UI-сессии требуют следующей сессии пользователя.
- Ответ spawn и self-report агента не доказывают реальную backend-модель/effort.
- Семантическое распознавание независимых задач и согласия — обязанность
  координатора; source=live_user и цитата не являются удостоверением смысла.
- Сейчас каталог не даёт upgrade/upgradeInfo для Sol; безопасный no-op проверяется,
  настоящий переход на ещё не вышедшую версию проверить невозможно.
- Windows, remote/cloud orchestration, managed workspace policy и все возможные
  specialized tool paths не проверялись. Hooks не являются полной security boundary.

Итог: устанавливаемый локальный пакет и его нативное обнаружение проверены;
полная сквозная сертификация поведения в новом живом чате не заявляется.

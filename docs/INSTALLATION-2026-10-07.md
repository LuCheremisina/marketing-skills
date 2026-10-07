# Release and installation evidence — 2026-10-07

The accepted library is published as [v2.0.1](https://github.com/LuCheremisina/marketing-skills/releases/tag/v2.0.1). v1.0.2 and v2.0.0 remain immutable. This documentation can advance on main without rebuilding an existing release under the same version.

| Requirement | Evidence | Limit |
|---|---|---|
| Public release | PRs 6 and 7 merged after successful CI; release artifacts published; anonymous manifest and archive downloads checked | Search indexing and business effects not measured |
| Historical immutability | Builds explicitly checked against accepted 1.0.2 and then 2.0.0 manifests | A changed payload cannot reuse its package version |
| Local migration | 34 authored packages installed in Codex, Claude Code and Cursor; hashes match 2.0.1. 14 vendor payloads per client already match and were retained | File installation does not prove every workflow executes |
| Backups | 81 old authored copies verified against 1.0.2, copied outside discovery and retired after replacement hash checks. No local modifications were found | Private backup paths and transaction journals remain private |
| Codex discovery | Native skills/list force reload: 34 unique authored names enabled, no parse errors, no legacy authored names in that CLI discovery | Desktop remote-plugin discovery is a separate surface |
| Codex invocation | Installed che-product-market-intake, che-unisender-email-pipeline and che-skill-optimizer explicitly invoked with synthetic inputs; resources read, missing inputs respected, no live email draft; optimizer ran from another cwd with 0 errors | Three scoped samples; full library, automatic selection and live integrations unverified |
| Claude Code | Files installed; native invocation attempted | OAuth 401 invalid token; 0 model tokens, no execution result |
| Cursor | Files installed and verified | GUI discovery and execution unverified; no agent CLI available |
| ChatGPT authored plugin | Existing identity updated to 2.0.1; UI lists all 34 CHE_ names. The 2.0.0 import exposed only 33; removing the undocumented policy.products adapter field restored Research Loop | Read-back registration, not full native execution; standalone personal skills remain separate |
| ChatGPT vendor plugin | Existing identity updated to 2.0.1; all 14 skills listed, original authors preserved | Registration read-back; full archived source download did not return through the available browser mechanism |
| Grok Bot / Claude Cowork | Portable packages and instructions retained | Separate import and execution not verified |

No account credentials, sharing permissions, client profiles or managed vendor caches were modified. Old cloud personal skills were not deleted automatically. The canonical public catalog has 48 packages; this does not claim every other account library has been destructively deduplicated.

## Русская версия

Опубликован **v2.0.1: 34 авторских CHE_ и 14 сторонних пакетов**. Публичные архивы доступны без входа. Прежние выпуски сохранены.

В Codex, Claude Code и Cursor установлены 34 новых авторских навыка; контрольные суммы совпали с выпуском. 14 сторонних пакетов в каждой системе уже соответствовали выпуску. 81 прежняя авторская копия сохранена вне каталогов обнаружения. Локальных изменений в этих копиях не было.

Codex CLI обнаружил все 34 новых имени без ошибок; для трёх навыков выполнены выборочные нативные проверки. Claude Code остановился на OAuth 401 — требуется повторный вход. Cursor: установка подтверждена, интерфейс и исполнение не проверены. Облачный авторский плагин ChatGPT обновлён: отображаются 34 навыка, включая Research Loop. Сторонний облачный плагин также обновлён до 2.0.1: отображаются 14 навыков. Обнаружение в облаке не доказывает полное исполнение.

Старые персональные облачные навыки не удалялись; канонический публичный каталог и прочие библиотеки аккаунта — разные уровни. Grok Bot и отдельный импорт Claude/Cowork пока не проверены. Токеномика и бизнес-эффект требуют отдельных измерений.

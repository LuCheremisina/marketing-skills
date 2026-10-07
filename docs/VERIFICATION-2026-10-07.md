# Verification — 2026-10-07 / Проверка кандидата

This report covers the **2.0.0 candidate**, not the immutable v1.0.2 release or a native installation.

## Scope and evidence

- 70 cloud package instances consolidated into **48 canonical packages: 34 authored CHE_ workflows and 14 licensed third-party packages**. Source archive checksums and 984 package-file checksums were verified; 14 additional archive files are global packaging resources.
- Every source instance has a private disposition. Client-specific source names, private identifiers and original archives are excluded from the public candidate.
- YAML, names, catalog hashes and resource validation: **48 packages pass**. The optimizer is a read-only static checker, not proof of semantic correctness, complete privacy or platform execution.
- Offline tooling: **53 repository tests + 16 optimizer tests pass**. Six new universal workflows have **21 synthetic CLI checks**, including execution from another directory and missing input cases.
- Existing authored workflows: **81 synthetic instruction cases** were reviewed in the current Codex agent (normal request, adjacent task, missing data/connection). Six new workflows: 18 scoped instruction-review cases; optimizer: 3 scoped cases. These are not executions in Claude, Cursor, ChatGPT or Grok.
- Optimizer: **0 errors, 752 advisory findings**. Of these, 751 concern preserved vendor packages: 620 navigation recommendations, 98 long-reference TOC recommendations, 32 synthetic public example addresses, and one MCP fallback review. One authored finder warning concerns a general portability mention of MCP, not a mandatory live connection. Vendor resources are preserved byte-for-byte; warnings are not silently erased by rewriting upstream work.
- Automated privacy scan is supplemented by human review of source profiles and synthetic examples. Author attribution and the approved portrait remain public intentionally. No scanner proves absence of all possible personal data.
- Same 27 pre-existing authored entrypoints: **192,202 → 170,880 Unicode characters (11.09% less)**. New packages and conditionally loaded references are excluded. This is a text-size proxy, **not paid-token savings**; workload token measurements remain unverified.
- Vendor source checks on 2026-10-07: Cloudflare Skills and the attribution-preserved autopilot source have no changes relative to their pinned revisions. Four external catalog sources were checked without copying, installing or rebranding managed plugins.

## Requirements and limits

The seven working review groups are documented in [CHE_skill-optimizer](../skills/che-skill-optimizer/references/requirements.md): compact progressive disclosure, metadata/triggering, resource navigation, portable script execution and dependencies, real MCP capabilities, proportionate workflow/feedback, and before/after behavior validation (privacy and provenance are additional checks). They are an operational grouping of current primary guidance, **not an official numbered seven-rule standard**. The earlier local Anthropic guide files could not be found, so exact correspondence with that attachment's seven items is unverified.

Current primary sources: [Agent Skills specification](https://agentskills.io/specification), [Anthropic best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [Yandex Wordstat operators](https://yandex.ru/support2/wordstat/ru/content/operators).

Native discovery, invocation, scripts, account connections and real task outcomes for the new CHE_ namespace are **not verified** in Codex, Claude, Cursor, ChatGPT and Grok Bot. Prior v1.0.2 installation evidence must not be transferred to the new namespace. Packaging compatibility and a static pass do not establish runtime compatibility.

Publication, merging, release and installation remain separate review gates. [Migration map](MIGRATION-2.0.md) preserves previous names as documentation, not duplicate installable packages. [Task routing](TASK-ROUTING.md) explains related workflows with different outputs. [MCP guidance](MCP-CONNECTIONS.md) offers an optional connection path when a required connection is missing.

## Русская версия

Подготовлено **48 пакетов: 34 авторских CHE_ и 14 сторонних**, вместо 70 экземпляров в облачном экспорте. Все исходники имеют решение в приватном реестре; клиентские имена и приватные идентификаторы в публичный каталог не включены.

Проверены структура, YAML, ресурсы, контрольные суммы, лицензии и авторство. Проходят **53 теста библиотеки и 16 тестов оптимизатора**; для шести новых универсальных навыков выполнена 21 синтетическая проверка CLI. Проверки поведения в текущем агенте и обзор инструкций не означают запуск на всех целевых платформах.

У оптимизатора **0 ошибок и 752 рекомендации**. 751 рекомендация относится к неизменённым сторонним пакетам, одна — к упоминанию MCP в инструкции поиска навыков. Рекомендации рассмотрены отдельно от обязательных ошибок; первоисточники сторонних навыков сохранены.

Основные файлы 27 существовавших авторских навыков сокращены на **11,09% по числу символов**. Реальная экономия токенов не измерялась. Личные настройки заменены входными параметрами; публичная атрибуция и согласованный портрет сохранены. Автоматический поиск признаков приватных данных дополнен просмотром исходных профилей, но не является абсолютной гарантией.

Точное совпадение с семью пунктами старого приложенного руководства не подтверждено: его локальные файлы недоступны. Применены актуальные официальные рекомендации по ссылкам выше, с явно описанной рабочей группировкой требований.

**Новые имена не установлены и не проверены в нативных клиентах. Публичный выпуск 2.0.0 не выполнен.** Предыдущая проверка v1.0.2 относится к прежним пакетам. Слияние, выпуск и установка выполняются после принятия кандидата.

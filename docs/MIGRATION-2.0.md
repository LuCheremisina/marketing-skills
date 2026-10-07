# CHE_ names and migration to 2.0.x

34 authored workflows use visible names `CHE_<task>` and portable IDs `che-<task>`. Uppercase letters and underscores belong in display metadata, not Agent Skills `name` or installed folder names. Third-party workflows retain original names, authors and licenses.

[Machine-readable migration map](../catalog/name-migration.json) maps the 27 published authored IDs. Aliases are documentation, not duplicate skill folders. Article and news image production use one `che-cover-production` package with project-specific settings; prompt-only requests use `che-editorial-cover-prompts`.

## Safe upgrade

1. Back up your existing installation outside skill-discovery directories. Keep any previous release archives you already downloaded, and record installed file checksums and local modifications.
2. Review the current release manifest, per-package hashes and platform requirements. New package presence does not prove native execution.
3. Test one new package in an isolated directory. Use the verified installer dry run before applying a reviewed batch. Never overwrite modified local copies without merging their changes.
4. Disable or move an old authored folder only after confirming its identity, backup and replacement. Preserve project profiles and state outside packages. Managed plugin copies must be upgraded through their vendor mechanism; do not edit plugin caches.
5. Test discovery, invocation and resource loading in each chosen client; check for active duplicate IDs. Restore the backed-up installation if acceptance fails.

Use [the current clean release](https://github.com/LuCheremisina/marketing-skills/releases/latest). Historical public releases v1.0.2, v2.0.0 and v2.0.1 have been withdrawn. Rollback uses your own pre-upgrade backup or previously downloaded archives; old release download links are unavailable.

## Русская версия

Маркировка авторских навыков: `CHE_` в отображаемом названии, `che-` в YAML и папке. Сторонние навыки не получают авторскую маркировку.

Карта миграции сохраняет связь со старым выпуском, но не создаёт дублирующие устанавливаемые папки. Обложки статьи и новости — режимы одного production-навыка; промпт без файла — отдельная задача.

Перед установкой сохранить резервную копию вне каталогов обнаружения, проверить локальные доработки, провести dry-run и тест отдельного пакета. Старые копии отключать только после проверки владельца, резервной копии и новой версии. Профили, токены и рабочую историю не переносить в распространяемый пакет. Управляемые плагины обновлять штатно.

Используйте [текущий очищенный выпуск](https://github.com/LuCheremisina/marketing-skills/releases/latest). Старые публичные выпуски v1.0.2, v2.0.0 и v2.0.1 отозваны. Для отката нужна ваша резервная копия до обновления или ранее скачанные архивы; старые ссылки загрузки недоступны.

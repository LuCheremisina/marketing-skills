# Release integrity

Published packages have immutable versions and SHA-256 checksums. Download a release from the [release page](https://github.com/LuCheremisina/marketing-skills/releases) and verify it against its `SHA256SUMS` and `manifest.json`. Each skill retains its own package version, source and license.

The standalone manifest is authoritative for the release archives. The complete bundle embeds a manifest without its own outer ZIP checksum to avoid self-reference. Check the complete ZIP against the standalone manifest.

For maintainers, run the repository checks and affected workflow tests, then build under a new library version with the accepted previous release manifest:

```bash
python scripts/build_release.py --output dist --version 2.0.2 --previous-manifest /path/to/accepted-previous/manifest.json
python scripts/audit_public.py --archives-dir dist
```

The baseline rejects changed skill contents under an unchanged package version. Changed documentation requires a new bundle version, even when individual skill packages remain unchanged. Never overwrite a published archive with different bytes under the same version.

The verification workflow builds a candidate and does not publish it. Review licenses, attribution, privacy, resource links and required connections before publication. Keep internal audit logs, account details and local installation evidence outside public files and archives.

Historical complete bundles containing internal maintenance reports have been withdrawn from release downloads. Individual skill packages are unchanged. Use the current clean complete bundle for installation.

## Русская версия

Проверяйте скачанный архив по `SHA256SUMS` и `manifest.json` соответствующего выпуска. Изменённый архив получает новую версию; опубликованные файлы не заменяются другим содержимым под прежним номером. Для полной библиотеки используйте текущий очищенный выпуск. Версии и содержимое отдельных навыков сохранены.

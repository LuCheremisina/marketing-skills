# Marketing Skill Cheremisina: установка полного плагина

[English instructions](INSTALL-PLUGIN.md)

Для установки из ZIP скачайте **[marketing-skills-plugin-2.0.7.zip](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.7/marketing-skills-plugin-2.0.7.zip)**. Не распаковывайте файл. Он содержит все **34 авторских маркетинговых навыка** вместе с ресурсами, скриптами и справочными материалами.

Дополнительный **[marketing-skills-vendor-2.0.7.zip](https://github.com/LuCheremisina/marketing-skills/releases/download/v2.0.7/marketing-skills-vendor-2.0.7.zip)** содержит 14 сторонних инженерных навыков с исходным авторством и лицензиями. Его устанавливают отдельно, при необходимости. Оба плагина вместе дают 48 навыков. Полный архив исходников репозитория не предназначен для нативной установки плагина.

## Выберите способ

| Система | Полный плагин | Отдельные навыки |
|---|---|---|
| Codex CLI / локальный Codex | GitHub marketplace, команды ниже | `npx skills`, все 34 или выбранные |
| Claude Code | GitHub marketplace, команды ниже | `npx skills`, все 34 или выбранные |
| Cursor | Используйте набор Agent Skills через CLI | `npx skills`, все 34 или выбранные |
| Claude / Cowork | GitHub marketplace или ZIP | Отдельный ZIP через Skills, если поддерживается |
| ChatGPT | Приватный плагин из ZIP через Plugin Creator | Отдельный ZIP через поддерживаемое создание навыка |
| Grok Bot | Универсальная команда импорта плагина не подтверждена | Сохранение навыка с ресурсами через библиотеку Bot |

Выберите один способ для одного набора: включённый плагин и параллельная CLI-установка дают дубли. [Все Skills или один через CLI](INSTALL.ru.md). ZIP — фиксированный выпуск; marketplace использует исходники репозитория. Изменения в `main` не меняют ранее скачанный ZIP.

## Claude Code

В чате Claude Code выполните по очереди:

```text
/plugin marketplace add LuCheremisina/marketing-skills
/plugin install marketing-skills@cheremisina-marketing
```

Или из терминала:

```sh
claude plugin marketplace add LuCheremisina/marketing-skills
claude plugin install marketing-skills@cheremisina-marketing --scope user
```

`user` — для пользователя во всех проектах на этом компьютере. Для общего проекта замените на `--scope project`. Проверьте установку через `claude plugin list`, откройте новый сеанс и выполните:

```text
/marketing-skills:che-deep-research Подготовь исследовательский бриф для вымышленного B2B-сервиса. Сначала уточни вводные.
```

Marketplace находится в [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json); имя `cheremisina-marketing`, плагин `marketing-skills`, источник — корень репозитория с 34 навыками. Пакет для каталога Claude в `platforms/claude/cheremisina-marketing-skills` имеет другое техническое имя; не устанавливайте его как второй экземпляр того же набора.

[Официальная инструкция Claude Code](https://code.claude.com/docs/en/discover-plugins).

## Codex

В терминале с установленным Codex CLI:

```sh
codex plugin marketplace add LuCheremisina/marketing-skills
codex plugin add marketing-skills@cheremisina-marketing
codex plugin list
```

В интерфейсе Codex откройте **Plugins → Add plugin marketplace**, введите `LuCheremisina/marketing-skills`, затем установите **Marketing Skill Cheremisina** из источника `cheremisina-marketing`. В CLI браузер плагинов открывается командой `/plugins` внутри сеанса Codex. Если ваша версия не поддерживает эти команды или интерфейс, используйте [CLI Skills](INSTALL.ru.md).

Каталог Codex — [`.agents/plugins/marketplace.json`](../.agents/plugins/marketplace.json), манифест плагина — [`.codex-plugin/plugin.json`](../.codex-plugin/plugin.json). После установки начните новый чат, выберите плагин и попросите: «Примени che-deep-research: подготовь исследовательский бриф для вымышленного B2B-сервиса».

Установка на компьютере не подтверждает наличие плагина в отдельной облачной задаче: там нужно отдельно настроить доступный способ установки и проверить обнаружение. [Официальные команды Codex](https://learn.chatgpt.com/docs/developer-commands), [формат marketplace](https://developers.openai.com/plugins/build/plugins).

## Claude / Cowork

### Из GitHub без скачивания ZIP

В **Customize → Plugins → Add → Add marketplace → Add from a repository** укажите:

```text
https://github.com/LuCheremisina/marketing-skills
```

Синхронизируйте каталог, выберите **Marketing Skill Cheremisina** и установите. Проверьте 34 навыка. Если добавление marketplace ограничено аккаунтом или организацией, используйте разрешённый импорт ZIP ниже.

### Из ZIP

1. Откройте **Персонализация → Плагины**; в английском интерфейсе — **Customize → Plugins**.
2. Выберите **Добавить → Загрузить плагин** и файл `marketing-skills-plugin-2.0.7.zip`.
3. Подтвердите импорт и включите **Marketing Skill Cheremisina**. На вкладке Skills должно быть **34 навыка**.
4. Начните новый чат или сессию Cowork. Пример: «Примени che-deep-research: подготовь исследовательский бриф для вымышленного B2B-сервиса. Сначала уточни недостающие вводные».

Для обновления установленного плагина загрузите новый ZIP тем же способом. Техническое имя `marketing-skills` сохраняется: поддерживаемый импорт распознаёт существующий плагин. Проверьте предложение заменить версию, чтобы избежать дубля. Установка плагина отличается от загрузки одного навыка через вкладку Skills.

[Официальная инструкция Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude). Доступность зависит от аккаунта и правил организации.

## ChatGPT

Один ZIP позволяет создать плагин со всеми 34 навыками, **если вашему аккаунту доступны Plugins и Plugin Creator**. Простое прикрепление архива к обычному чату не устанавливает навыки.

1. В разделе **Plugins / Плагины** откройте **Build plugins / Plugin Creator**, чтобы начать диалог создания плагина.
2. Прикрепите `marketing-skills-plugin-2.0.7.zip` и напишите: «Создай из этого архива приватный персональный плагин. Сохрани манифесты и все 34 навыка. Дай ссылку для установки. Не публикуй плагин в организации».
3. Откройте полученную страницу, установите или включите плагин, если появится такой запрос. Проверьте название **Marketing Skill Cheremisina** и **34 навыка**.
4. Начните новый чат и попросите применить `che-deep-research`, например к задаче из инструкции выше.

Для обновления передайте Plugin Creator ссылку на уже установленный плагин и попросите **обновить именно его из ZIP**, сохранив приватность и аудиторию. Не создавайте второй экземпляр. Названия кнопок могут различаться. Если Plugins или Plugin Creator отсутствует, этот нативный способ вашему аккаунту недоступен; использование ZIP как вложения обычного чата не заменяет установку.

[Официальная инструкция OpenAI](https://learn.chatgpt.com/docs/plugins), [формат пакета плагина](https://developers.openai.com/plugins/build/plugins).

## Cursor и отдельные Skills

Используйте [русскую CLI-инструкцию](INSTALL.ru.md): она содержит команды всех 34 навыков и одного навыка для Codex, Claude Code и Cursor, глобальную и проектную установку, проверку, обновление и удаление. Это установка папок Skills; она не регистрирует плагин в магазине Cursor. [Примеры использования](../README.ru.md#как-пользоваться).

## Что входит в установку

Плагин предоставляет инструкции и ресурсы навыков. Подключение внешних аккаунтов и доступ к API выполняются отдельно. Если задача требует MCP, используйте [инструкцию подключения](MCP-CONNECTIONS.md) и [MCP Panel](https://cheremisina.ru). До применения в рабочих решениях проверьте одну задачу и доступ к ресурсам.

Методолог: **Любовь Черемисина** — [cheremisina.ru](https://cheremisina.ru), [cheremisina.online](https://cheremisina.online).

## Обновить существующий плагин ChatGPT

Прикрепите ZIP авторского плагина из последнего выпуска и попросите: «Обнови существующий Marketing Skill Cheremisina из этого архива. Сохрани идентификатор, доступы и все 34 навыка. Не создавай дубликат и не откатывай более новую установку. Проверь версию и исправленные скрипты дайджестов. Не запускай доставку и платные API».

Публикация на GitHub сама не обновляет существующие установки. Доступность обновления зависит от текущего интерфейса; если оно недоступно, используйте поддерживаемый редактор/импорт с резервной копией.

## Обновление и удаление

Используйте тот же механизм, которым установили набор. Для Skills через `npx` команды приведены в [CLI-инструкции](INSTALL.ru.md#обновление-и-удаление).

**Claude Code**, в терминале:

```sh
claude plugin marketplace update cheremisina-marketing
claude plugin update marketing-skills@cheremisina-marketing
claude plugin uninstall marketing-skills@cheremisina-marketing
```

Первые две строки обновляют, третья удаляет плагин — выполняйте нужное действие. Если ставили в проект, передайте `--scope project` команде обновления или удаления. Перед обновлением сохраните свои правки; после — проверьте версию и задачу.

**Codex**: `codex plugin marketplace upgrade cheremisina-marketing` обновляет Git-источник каталога. Проверьте установленную версию через `codex plugin list` и примените доступное обновление в Plugins. Для удаления: `codex plugin remove marketing-skills@cheremisina-marketing`. Обновление источника само по себе не является доказательством замены установленной копии.

**Claude / Cowork**: управляйте marketplace и установленным плагином через Plugins; для ZIP используйте поддерживаемую замену существующего плагина. **ChatGPT**: обновите существующий плагин через Plugin Creator, как описано выше, либо удалите его через Installed. При смене способа установки сначала сохраните локальные изменения и отключите прежнюю копию.

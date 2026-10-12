# Marketing Skill Cheremisina — privacy and data handling

This notice covers the authored plugin distributed from this repository. It describes the included code; third-party services and tools connected by a user have their own policies.

## What the plugin can process

The workflows process the business context, documents, URLs and datasets supplied for a task. Depending on those inputs and the tools connected by the user, this can include personal or customer data. Installation itself starts no scripts, connectors, subscriptions or telemetry.

The optional Telegram subscription listener stores chat identifiers, usernames, first and last names, subscription status and timestamps in a local `subscribers.json` file. Unsubscribing marks the record inactive; it does not erase the record. Reports, SQLite caches, run history, delivery history and logs can also remain in the execution environment. The user or workspace operator controls these files and their deletion; the package implements no automatic retention deadline.

## External services

Public research retrieves the websites and feeds needed for the task. Optional digest delivery and subscription processing communicate with `api.telegram.org`; recipients and a Telegram bot token must be configured by the user. Delivery sends the prepared HTML digest to an explicit approved recipient list and stores local delivery receipts. Subscriber processing is a separately started owner-operated process, not part of digest preparation or delivery. Optional OpenAI commentary in `che-direct-analyst` sends the calculated campaign dataset to `api.openai.com` when that step is authorized and configured. Use `--no_llm` for a local deterministic report. AI-digest OpenAI processing sends RSS/news titles, URLs, summaries and previous digest context only after explicit `--allow-openai` authorization. Industry-digest OpenAI processing additionally includes the business name, niche and language; without `--allow-openai` it returns an unverified draft without OpenAI processing. Other skills may use APIs or MCP tools connected by the user. Confirm destinations, recipients and data before external writes or transmission.

No credentials are included. Some optional scripts use vendor credentials supplied through environment configuration or a configured local `.env` file. Never place secrets in prompts, public reports or the repository. Neither installation, preparation nor delivery starts a background subscription listener; it requires a separate owner-authorized launch.

## Publisher, host and retention

The plugin contains no publisher-operated data collection or storage endpoint. Lyubov Cheremisina does not receive task inputs through this package merely because it is installed or run. This does not mean data never leaves the host: Claude, other AI hosts, connected tools, Telegram and OpenAI can process data according to their own settings and policies. The publisher cannot delete files held in a user's environment or records held by those services.

For questions or issues, use the [repository issue tracker](https://github.com/LuCheremisina/marketing-skills/issues). Do not post personal data, credentials or private datasets there. Author: [cheremisina.ru](https://cheremisina.ru) and [cheremisina.online](https://cheremisina.online).

## Русский

Плагин обрабатывает вводные, документы, адреса страниц и наборы данных, которые пользователь предоставляет для задачи. Они могут содержать персональные или клиентские данные. Установка не запускает скрипты и не подключает сервисы автоматически.

Необязательный Telegram-подписчик сохраняет локально идентификатор чата, имя пользователя, имя, фамилию, статус подписки и временные отметки. Отписка делает запись неактивной, но не удаляет её. Отчёты, кеши, история и логи остаются в среде выполнения до удаления пользователем или оператором; автоматический срок хранения не предусмотрен.

Исследования запрашивают публичные страницы и ленты. Необязательная отправка дайджеста и обработка подписок обращаются к Telegram; комментарии OpenAI в `che-direct-analyst` передают рассчитанные данные рекламной кампании, если этот этап разрешён и настроен. Для локального отчёта используйте `--no_llm`. Другие навыки могут использовать подключённые пользователем API и MCP. До отправки подтвердите сервис, данные и получателей. Подготовка, установка и доставка не запускают Telegram-подписчика: это отдельный разрешённый процесс владельца. Доставка сохраняет локальный журнал получателей и подтверждений для защиты от повторной отправки. AI-дайджест передаёт OpenAI заголовки, URL, фрагменты RSS и контекст предыдущего выпуска только с разрешением и флагом --allow-openai. Отраслевой дайджест при таком разрешении дополнительно передаёт название бизнеса, нишу и язык; без флага выдаёт непроверенный черновик без обращения к OpenAI.

Ключей в пакете нет. Отдельные скрипты принимают ключи поставщиков из настроенного окружения или локального `.env`. Не вставляйте секреты в чат и публичные файлы. Плагин не содержит сервера сбора данных автора. Хранение и обработка у Claude, других AI-систем и внешних сервисов регулируются их собственными настройками и правилами. Файлами в рабочей среде управляет её пользователь.


## Audience and host restrictions / Аудитория и ограничения среды

The library's intended audience includes users under 18, as declared by the publisher. This is not a claim that minors may use Claude accounts: current Anthropic account rules require age 18+. No dedicated age-assurance or child-data compliance system is implemented by this skills-only package. Any permitted deployment for younger audiences needs separate confirmation and appropriate host controls.

Автор указала, что библиотека предназначена также для пользователей младше 18 лет. Это не разрешает им пользоваться аккаунтами Claude вопреки возрастному ограничению 18+. В пакете нет отдельной системы проверки возраста и специальных механизмов обработки детских данных. Допустимый способ использования этой аудиторией требует согласования и контроля со стороны соответствующей среды.

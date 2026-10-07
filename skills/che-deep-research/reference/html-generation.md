# Генерация HTML: компактный consulting-отчёт

## Содержание

- Принципы дизайна
- Шаги генерации
- Шаг 1: Загрузить consulting-шаблон
- Шаг 2: Извлечь ключевые метрики
- Шаг 3: Конвертировать MD в HTML
- Шаг 4: Добавить тултипы ссылок (опционально)
- Шаг 5: Заменить плейсхолдеры шаблона
- Шаг 6: Верифицировать HTML
- Шаг 7: Сообщить путь к файлу
- Генерация PDF


## Принципы дизайна

- Острые углы (БЕЗ border-radius)
- Приглушённые корпоративные цвета (navy #003d5c, серый #f8f9fa)
- Ультракомпактный макет
- Структура с приоритетом информации
- Базовый шрифт 14px, компактные отступы
- Без декоративных градиентов или цветов
- БЕЗ ЭМОДЗИ в финальном HTML

---

## Шаги генерации

### Шаг 1: Загрузить consulting-шаблон
Загрузить из: `./templates/consulting_report_template.html`

### Шаг 2: Извлечь ключевые метрики
Извлечь 3–4 ключевых количественных вывода для отображения на дашборде вверху.

### Шаг 3: Конвертировать MD в HTML

Использовать Python-скрипт. Запускать **из директории скилла** (путь зависит от установки):
```bash
# Запускать из распакованной директории скилла (путь задаёт установка)
cd [ДИРЕКТОРИЯ_СКИЛЛА]
python scripts/md_to_html.py [путь_к_markdown_отчёту]
```

**Скрипт выводит две части:**
- **Часть A ({{CONTENT}}):** Все разделы кроме Библиографии
- **Часть B ({{BIBLIOGRAPHY}}):** Только раздел Библиографии

**Скрипт обрабатывает всю конвертацию:**
- Заголовки: `##` → `<div class="section"><h2 class="section-title">`
- Заголовки: `###` → `<h3 class="subsection-title">`
- Списки: Markdown буллеты → `<ul><li>` с вложением
- Таблицы: Markdown таблицы → `<table>` с thead/tbody
- Абзацы: Текст обёрнут в `<p>`
- Жирный/курсив: `**текст**` → `<strong>`, `*текст*` → `<em>`
- Ссылки: [N] сохранены для конвертации в тултипы

### Шаг 4: Добавить тултипы ссылок (опционально)

Обернуть каждую ссылку [N]:
```html
<span class="citation">[N]
  <span class="citation-tooltip">
    <div class="tooltip-title">[Название источника]</div>
    <div class="tooltip-source">[Автор/Издатель]</div>
    <div class="tooltip-claim">
      <div class="tooltip-claim-label">Поддерживает утверждение:</div>
      [Извлечь предложение с этой ссылкой]
    </div>
  </span>
</span>
```
Примечание: Шаг опционален для скорости. Базовые ссылки [N] достаточны.

### Шаг 5: Заменить плейсхолдеры шаблона

| Плейсхолдер | Содержимое |
|-------------|-----------|
| {{TITLE}} | Название отчёта (из первого `##` заголовка) |
| {{DATE}} | Дата генерации (YYYY-MM-DD) |
| {{SOURCE_COUNT}} | Число уникальных источников |
| {{METRICS_DASHBOARD}} | HTML метрик из шага 2 |
| {{CONTENT}} | HTML из Части A |
| {{BIBLIOGRAPHY}} | HTML из Части B |

### Шаг 6: Верифицировать HTML

```bash
python scripts/verify_html.py --html [путь_к_html] --md [путь_к_md]
```
- Прошёл: перейти к шагу 7
- Не прошёл: Исправить ошибки и повторить

### Шаг 7: Сообщить путь к файлу

Success is FILE_GENERATED + PATH_RETURNED. Tell the user the exact HTML
path. Do not require a desktop/GUI opener for the skill to succeed.

Optional, host-specific open examples (never mandatory):

- macOS: `open report.html`
- Linux: `xdg-open report.html`
- Windows: `start report.html`

---

## Генерация PDF

**Вариант A: WeasyPrint напрямую (предпочтительно)**

1. Создать HTML для печати по `./reference/weasyprint_guidelines.md`
2. Критичные CSS:
   - `page-break-inside: avoid` для таблиц, блоков
   - `page-break-after: avoid` для заголовков
   - `orphans: 3; widows: 3` для абзацев
   - Использовать `display: table`, не Flexbox/Grid
   - Размеры шрифтов в pt (10pt основной, 8pt ссылки)
3. Генерировать: `weasyprint [путь_к_html] [путь_к_pdf]`
4. Сообщить пользователю точный путь к PDF. Opening the file in a viewer
   is optional and host-specific (see Step 7 examples).

**Вариант B: Скилл generating-pdf**

Использовать Task с агентом general-purpose, вызвать скилл generating-pdf.

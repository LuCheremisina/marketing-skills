# Контракт checkpoint и результата

## Checkpoint

Сохранять после каждой итерации до следующей; все поля обязательны:

```yaml
workflow: RESEARCH-LOOP-001
version: '1.0'
client_id: 'исследовательский ключ; CRM ID только при подтверждении'
iteration: 1
status: RUNNING
sources_checked: []
known_facts: []
gaps: []
conflicts: []
client_state: {status: UNKNOWN, confidence: 0, evidence: []}
reactivation_eligibility: {status: HUMAN_REVIEW, reason: 'Исследование продолжается', evidence: []}
next_step: {uncertainty: '', source: '', purpose: ''}
retry_count: {} # источник → число повторных попыток, не первичных вызовов
updated_at: 'реальное время записи ISO 8601'
```

Сохранять journal и raw evidence рядом с checkpoint или ссылками в нём. Использовать новый каталог собственного исследования; не изменять исходные данные. Указывать дату события отдельно от времени получения. Не придумывать отсутствующий timestamp события. При возобновлении проверить сохранённые evidence и следующий шаг. Терминальный результат не уничтожает checkpoint.

## RESEARCH_RESULT

JSON и YAML одинаково допустимы; скрипт guard принимает JSON. UNKNOWN — явное значение, а пустой список означает «нет установленных записей в проверенном охвате», не автоматически «не существует».

```yaml
research_result:
  workflow: {name: RESEARCH-LOOP-001, version: '1.0'}
  client:
    company: ''
    legal_entity: UNKNOWN
    contacts: [] # имя, роль, email, телефон, CRM IDs, evidence или UNKNOWN
    website: UNKNOWN
    crm_ids: {}
  relationship:
    first_known_contact: UNKNOWN
    projects: [] # стадии discussed/ordered/paid/performed/result с раздельными evidence
    purchases: [] # продукт, дата, сумма, валюта, стадии и evidence
    key_events: [] # подтверждённая хронология: дата, участники, факт, evidence
    last_meaningful_interaction:
      date: UNKNOWN
      participants: []
      topic: UNKNOWN
      outcome: UNKNOWN
      evidence: []
  stop_reason: {status: UNKNOWN, reason: UNKNOWN, evidence: []}
  current_context:
    active_projects: UNKNOWN
    recent_changes: UNKNOWN
    open_commitments: UNKNOWN
    current_deals: UNKNOWN
    servicing: UNKNOWN
    current_correspondence: UNKNOWN
    scheduled_meetings: UNKNOWN
    responsible_manager: UNKNOWN
    human_restrictions: [] # точные слова, срок/область, evidence, влияние
  client_state: {status: UNKNOWN, confidence: 0, evidence: []}
  reactivation_eligibility: {status: HUMAN_REVIEW, reason: '', evidence: []}
  facts: [] # claim, confidence, evidence
  evidence_registry: [] # id, source, reference, date, fact; retrieved_at и охват при необходимости
  conflicts: [] # question, source_a, source_b, status, affects_decision, resolution/evidence
  gaps: [] # fact, importance HIGH/MEDIUM/LOW, source_needed, affects_decision boolean
  sources_checked: [] # источник, запрос/охват, outcome, ссылки; недоступность/ошибки тоже
  source_selection_log: [] # iteration, uncertainty, source, purpose, changed_after_check
  research_quality:
    iterations: 0
    evidence_coverage: UNKNOWN # подтверждённые существенные claims / все существенные claims
    unresolved_high_priority_gaps: []
    loop_stop_reason: DATA_SUFFICIENT # либо NO_MATERIAL_GAIN / ITERATION_LIMIT / INFRASTRUCTURE_BLOCKED
  verify: {} # 15 пунктов ниже: PASS / UNKNOWN / FAIL с объяснением и evidence
  routing: {next_process: HUMAN_REVIEW, reason: ''}
  result: HUMAN_REVIEW
```

Evidence в claim можно ссылать ID из evidence_registry; обязательно разрешить каждую ссылку. Reference — реальный ID/URL/путь/диапазон записи, не придуманный линк. Для неизвестного факта пустой evidence допустим только вместе с явным UNKNOWN и gap; отсутствие доказательства классификации объяснить, не подделывать evidence.

## Финальный VERIFY

1. Компания идентифицирована.
2. Контакт идентифицирован либо явно не установлен.
3. История собрана с указанным охватом.
4. Последнее значимое взаимодействие установлено либо UNKNOWN.
5. Обсуждение/заказ/оплата/исполнение/результат разделены.
6. Причина паузы подтверждена либо UNKNOWN/NOT_APPLICABLE.
7. CLIENT_STATE определён.
8. REACTIVATION_ELIGIBILITY определён.
9. Маршрут согласован с ними и Human Safety Gate.
10. Существенные claims имеют evidence.
11. Конфликты перечислены, влияние оценено.
12. Gaps перечислены.
13. Нет скрытых предположений.
14. Терминальный result согласован с качеством.
15. Никаких сообщений клиенту и запрещённых изменений не выполнено.

Невыполненный обязательный факт не отмечать PASS; UNKNOWN допустим там, где спецификация разрешает неизвестность. Если техническая дисциплина checkpoint нарушена, явно отразить нарушение отдельно от бизнес-вывода. Структурная валидация не подтверждает выполнение процедур или истинность claims.

# Контракты данных

## Содержание

- 1. `project-registry.json`
- 2. `seed-manifest.json`
- 3. `candidate-ledger.json`
- 4. `cluster-registry.json`
- 5. Вход тренд-движка `input.json`
- 6. `trend-history.sqlite`
- 7. Экспорт Яндекс.Вебмастера `webmaster-export.json`


## 1. `project-registry.json`

Использовать `assets/project-registry.template.json`. Валидировать через `scripts/validate_registry.py`.

## 2. `seed-manifest.json`

```json
{
  "schema_version": "2.0",
  "project_id": "example",
  "registry_fingerprint": "sha256:...",
  "seeds": [
    {
      "seed_id": "seed:buy-product",
      "phrase": "купить продукт",
      "status": "active",
      "priority": "high",
      "source_refs": ["product:main"],
      "force_monitor": false
    }
  ]
}
```

Одинаковый реестр должен формировать одинаковые seed IDs, порядок и fingerprint.

## 3. `candidate-ledger.json`

```json
{
  "project_id": "example",
  "snapshot_date": "2026-07-01",
  "region_id": 225,
  "devices": ["all"],
  "candidates": [
    {
      "phrase": "...",
      "volume": 100,
      "source_seed_ids": ["seed:..."],
      "intent": "commercial_research",
      "core_entity": "...",
      "customer_job_ids": [],
      "product_ids": [],
      "relevance_level": "direct",
      "decision": "include",
      "reason_codes": ["DIRECT_PRODUCT_FIT"],
      "cluster_id": "..."
    }
  ]
}
```

Все кандидаты должны иметь `decision` и минимум один `reason_code`. Запрещено хранить только включённые фразы.

## 4. `cluster-registry.json`

```json
{
  "project_id": "example",
  "clusters": [
    {
      "cluster_id": "ai-analytics__commercial-research__analyze-marketing",
      "canonical_label": "ИИ для маркетинговой аналитики",
      "canonical_phrase": "ии для аналитики",
      "aliases": [],
      "intent": "commercial_research",
      "core_entity": "ai-analytics",
      "primary_job_id": "job:analyze-marketing",
      "product_ids": ["product:mcp-panel"],
      "audience_ids": ["audience:marketer"],
      "relevance_level": "direct",
      "decision": "include",
      "coverage": {
        "status": "partial",
        "urls": ["https://example.ru/"]
      },
      "representative_queries": ["ии для аналитики"],
      "merged_from": [],
      "change_log": []
    }
  ]
}
```

`coverage.status`: `covered_product`, `covered_content`, `partial`, `gap`, `irrelevant`.

## 5. Вход тренд-движка `input.json`

```json
{
  "project": {
    "id": "example",
    "name": "Пример",
    "domain": "example.ru",
    "region": "Россия",
    "region_id": 225,
    "devices": "all",
    "min_volume": 30,
    "registry_fingerprint": "sha256:..."
  },
  "clusters": [
    {
      "id": "ai-analytics__commercial-research__analyze-marketing",
      "label": "ИИ для маркетинговой аналитики",
      "intent": "commercial_research",
      "business_relevance": 1.0,
      "coverage": {
        "status": "partial",
        "urls": ["https://example.ru/"]
      },
      "series": [
        {"date": "2024-01", "value": 120, "complete": true},
        {"date": "2024-02", "value": 130}
      ]
    }
  ]
}
```

Требования к ряду:

- `date`: `YYYY-MM`, без дублей;
- `value`: неотрицательное число;
- минимум 6 точек для расчёта, 18 ненулевых месяцев для уверенного тренда, 24 ненулевых месяца для сезонности;
- не смешивать регионы, устройства и операторы Wordstat;
- `complete: false` помечает неполный месяц и снижает доверие; текущий месяц лучше исключать;
- у кластера разрешены `canonical_phrase` или `representative_phrase`: они нужны для безопасного ключа истории.

## 6. `trend-history.sqlite`

SQLite создаётся через `scripts/analyze_trends.py --history-db`. Таблица `observations` имеет ключ:

`project_id, phrase, cluster_id, region_id, device, operator, month`.

Таблицы `runs` и `classifications` сохраняют снимок каждой классификации. Это позволяет определить изменение между двумя последовательными запусками, не переписывая прошлый вывод.

## 7. Экспорт Яндекс.Вебмастера `webmaster-export.json`

```json
{
  "rows": [
    {
      "query": "ии для маркетинговой аналитики",
      "cluster_id": "ai-analytics__commercial-research__analyze-marketing",
      "url": "https://example.ru/ai-analytics/",
      "impressions": 120,
      "clicks": 5,
      "position": 7.8
    }
  ]
}
```

`cluster_id` должен поступать из явной карты фраз, а не из эвристического сопоставления в момент отчёта. Отчёт видимости формируется только `scripts/merge_webmaster_visibility.py` и не меняет сигнал Wordstat.

Не хранить секреты доступа к MCP, аналитике или CRM в реестрах.

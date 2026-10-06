# Контракт данных

## Содержание

1. Роли и обязательность источников
2. Пакет числового прогноза
3. Факт, корректировки и fingerprint
4. Ретропроверка и неопределённость
5. Управленческие сценарии
6. Поисковая воронка и бизнес-ценность
7. Сегменты и самообучение
8. Правила объединения и статусы качества

## 1. Роли и обязательность источников

| Источник | Что измеряет | Не использовать как |
|---|---|---|
| Яндекс.Метрика | фактические визиты, поведение, страницы входа, цели | рыночный спрос |
| Яндекс.Вебмастер | показы, клики, CTR, позиции, индексные и технические сигналы | общий спрос ниши |
| Wordstat | частотность и сезонность поисковых формулировок | позиции и клики сайта |
| CRM | лиды, качество, стадии, сделки и продажи | полный трафик |
| Финансы | выручка, валовая прибыль, маржа, возвраты, LTV | маркетинговую атрибуцию без связки |
| Контекст проекта | продукт, аудитория, интент, URL, CTA, KPI и ограничения | числовое доказательство спроса |

Определять источник истины по целевой метрике:

| Целевая метрика | Обязательный источник истины | Сильное обогащение |
|---|---|---|
| Все визиты | Метрика | рекламные кабинеты, календарь кампаний |
| Органические визиты | Метрика | Вебмастер, Wordstat |
| Клики из поиска | Вебмастер | Wordstat, Метрика |
| Лиды | CRM или сверенное событие Метрики | Вебмастер, CRM |
| Выручка/прибыль | CRM/заказы + финансовое определение | Метрика, расходы |

В `sources[]` для каждого источника хранить:

`name`, `role`, `status`, `required_for_target`, `freshness_date`, `coverage_from`, `coverage_to`, `grain`, `units`, `notes`.

Если `required_for_target=true`, источник не может быть `blocked`. Для `high` confidence он должен иметь статус `ok`.

## 2. Пакет числового прогноза

Создавать `dashboard-input.json` в UTF-8. Для числового прогноза обязательны все верхнеуровневые поля:

```json
{
  "meta": {},
  "forecast_run": {},
  "metric_definition": {},
  "sources": [],
  "actual_series": [],
  "adjustments_log": [],
  "events_calendar": [],
  "regime": {},
  "data_fingerprint": {},
  "horizons": [7, 30],
  "scenario_totals": [],
  "uncertainty_totals": [],
  "daily_forecast": [],
  "model": {},
  "scenario_confidence": {},
  "drivers": [],
  "demand_signals": [],
  "blockers": [],
  "actions": [],
  "business_registry": [],
  "search_funnel": {},
  "hierarchical_forecasts": [],
  "learning_loop": {}
}
```

Пакет прежнего формата без `schema_version=2.0`, фактического ряда и backtest-окон не валидировать и не мигрировать арифметически. Пересобрать его из источников: недостающие доказательства нельзя восстановить из готовых итогов.

`meta`:

- `schema_version`: `2.0`;
- `project`, `domain`, `as_of`, `target_metric`, `target_unit`, `timezone`;
- `status`: `complete` или `partial`.

`forecast_run`:

- `run_id`: стабильный уникальный идентификатор снимка;
- `generated_at`: ISO datetime с часовым поясом;
- `previous_run_id`: `null` для первого запуска, иначе идентификатор предыдущего снимка.

`metric_definition`:

- `name`, `formula`, `grain`, `source_of_truth`;
- `inclusions`, `exclusions`: массивы явных правил;
- `aggregation`: `sum`, `count`, `mean` или другое однозначное правило.

`horizons` содержит ровно `7` и `30`.

`scenario_totals` содержит все комбинации:

```json
{"horizon": 7, "scenario": "base", "value": 3479}
```

Сценарии: `pessimistic`, `base`, `optimistic`.

## 3. Факт, корректировки и fingerprint

`actual_series` хранит не менее 90 последовательных завершённых дней до `meta.as_of` включительно:

```json
{
  "date": "2026-07-22",
  "actual": 472,
  "adjusted": 455,
  "adjustment_ids": ["adj-2026-07-22-bots"]
}
```

Правила:

- `actual` — неизменённый факт из источника;
- `adjusted` — значение, используемое для обучения;
- при равных значениях `adjustment_ids` пуст;
- при различии значений требуется хотя бы один существующий `adjustment_id`;
- не заполнять пропущенные даты молча; нулевой факт хранить строкой с нулём.

`adjustments_log` хранит каждую правку:

```json
{
  "id": "adj-2026-07-22-bots",
  "date": "2026-07-22",
  "original_value": 472,
  "adjusted_value": 455,
  "reason": "Подтверждённый ботовый всплеск",
  "method": "Исключены визиты по подтверждённому фильтру",
  "evidence": "Ссылка или идентификатор запроса"
}
```

`events_calendar[]` хранит подтверждённые прошлые и будущие события:

`id`, `date_from`, `date_to`, `type`, `status`, `scope`, `expected_direction`, `evidence`.

Допустимые `status`: `observed`, `confirmed`, `planned`. Плановое событие без подтверждения не включать в базу.

`regime`:

- `training_from`, `training_to`;
- `detection_method`;
- `change_points[]`: дата, тип, evidence;
- `excluded_periods[]`: даты и причина;
- `rationale`: почему выбранный период сопоставим.

Обучающее окно должно входить в `actual_series`, заканчиваться на `as_of` и содержать минимум 90 дней.

`data_fingerprint`:

```json
{"algorithm": "sha256", "value": "...", "series_rows": 365}
```

Fingerprint рассчитывать по canonical JSON из `actual_series`, `adjustments_log`, `events_calendar`, `regime`, `metric_definition` и `sources`. Использовать валидатор с `--write-fingerprint`; не вводить hash вручную.

## 4. Ретропроверка и неопределённость

`model`:

- `selected_model_id`, `baseline_model_id`;
- `training_from`, `training_to`;
- `minimum_lift_pct`: минимальный выигрыш сложной модели над baseline;
- `selection_reason`;
- `candidate_models[]`;
- `backtest_folds[]`;
- `backtest_summary[]`;
- `uncertainty_method`;
- `confidence`: `high`, `medium`, `low`;
- `notes`.

Каждый `candidate_models[]`:

```json
{
  "id": "seasonal-naive-7",
  "method": "seasonal_naive",
  "complexity": "baseline",
  "parameters": {"lag": 7},
  "eligible": true,
  "metrics": [
    {"horizon": 7, "wape": 8.2, "mae": 31.4, "mase": 1.0, "bias": -4.1},
    {"horizon": 30, "wape": 11.6, "mae": 39.8, "mase": 1.0, "bias": -7.2}
  ]
}
```

Хранить минимум baseline и выбранную модель. Если выбрана не baseline-модель, её `lift_vs_baseline_pct` должен быть не ниже `minimum_lift_pct` на обоих горизонтах.

Каждый `backtest_folds[]`:

```json
{
  "fold_id": "fold-01-selected-7",
  "model_id": "selected",
  "cutoff": "2026-05-31",
  "horizon": 7,
  "observations": [
    {
      "date": "2026-06-01",
      "actual": 451,
      "forecast": 438,
      "p10": 401,
      "p90": 476
    }
  ]
}
```

Для baseline и выбранной модели хранить минимум три последовательных окна на каждый горизонт. В каждом окне:

- даты следуют сразу после `cutoff`;
- число наблюдений равно горизонту;
- сохраняются факты и прогнозы, а не только готовая ошибка;
- для выбранной модели сохраняются P10/P90 каждого наблюдения, чтобы воспроизвести фактическое покрытие интервала;
- преобразования совпадают с production-прогнозом;
- нет утечки данных из будущего.

Каждый `backtest_summary[]` содержит:

`horizon`, `wape`, `mae`, `mase`, `bias`, `wape_std`, `baseline_wape`, `lift_vs_baseline_pct`, `interval_coverage_pct`, `folds`.

Метрики обязательны отдельно для 7 и 30 дней. `interval_coverage_pct` показывает фактическую долю backtest-наблюдений внутри P10/P90; для высокой уверенности она должна быть не ниже 75%.

`daily_forecast` содержит 30 последовательных дат после `as_of`:

```json
{
  "date": "2026-07-23",
  "p10": 420,
  "p50": 490,
  "p90": 568,
  "pessimistic": 455,
  "base": 490,
  "optimistic": 531
}
```

Статистический слой:

- `p10 <= p50 <= p90`;
- `p50` совпадает с `base` с учётом округления;
- P10/P90 получать из эмпирических backtest-ошибок или conformal-подхода, не из произвольного процента.

`uncertainty_totals` содержит P10/P50/P90 отдельно на 7 и 30 дней. Агрегатные интервалы рассчитывать для суммы горизонта; не получать их механическим сложением дневных квантилей.

## 5. Управленческие сценарии

`scenario_confidence` хранит `base`, `pessimistic`, `optimistic`.

Каждое действие в `actions[]` содержит:

- `id`, `priority`, `lever`, `metric`, `baseline`, `target`;
- `start_date`, `lag_days`, `ramp_curve`;
- `completion_probability`, `outcome_probability`;
- `impact_cap`, `impact_unit`;
- `expected_impact_by_horizon`: объект с ключами `7` и `30`;
- `impact_range_by_horizon`: low/high для 7 и 30;
- `daily_impact[]`: дата и уже скорректированный ожидаемый эффект;
- `evidence_level`, `evidence_reference`;
- `interaction_group`, `overlap_discount`;
- `cost`: amount/currency;
- `resource`, `dependency`, `done_when`.

Допустимые `evidence_level` по убыванию силы:

1. `project_experiment`;
2. `project_historical_analogue`;
3. `comparable_pages`;
4. `external_benchmark`;
5. `expert_assumption`.

`daily_impact` хранит итог после вероятностей и `overlap_discount`. Его сумма должна совпадать с `expected_impact_by_horizon`, не превышать probability-adjusted `impact_cap` и не начинаться раньше `start_date + lag_days`.

Если несколько действий имеют один `interaction_group`, хотя бы одно должно иметь `overlap_discount < 1`.

Каждый риск в `blockers[]` содержит:

- `id`, `severity`, `metric`, `evidence`, `resolution`;
- `probability`;
- `expected_loss_by_horizon`;
- `daily_loss[]`: дата и probability-adjusted потеря.

Дневная траектория обязана сходиться:

```text
optimistic(date) = base(date) + sum(actions.daily_impact(date))
pessimistic(date) = max(0, base(date) - sum(blockers.daily_loss(date)))
```

Если более половины оптимистичного эффекта основано на `expert_assumption`, `scenario_confidence.optimistic` должен быть `low`.

## 6. Поисковая воронка и бизнес-ценность

`business_registry[]`:

`product`, `audience`, `customer_job`, `intent_type`, `cluster_id`, `url`, `cta`, `conversion_event`, `lead_quality_rule`, `business_goal`, `deal_lag_days`, `visit_value_level`.

`visit_value_level`: `high`, `medium`, `low`, `unknown`. Не присваивать денежную ценность без сверенной CRM/финансовой модели.

`search_funnel`:

- `status`: `ready`, `partial`, `blocked`;
- `notes`;
- `stages[]`: `id`, `label`, `source`, `metric`, `unit`, `status`;
- `links[]`: `from`, `to`, `formula`, `validated`;
- `forecasts[]`: `horizon`, `stage_id`, `value`, `status`.

Статус отсутствующего нижнего слоя — `readiness_gap`, а не нулевое значение. Для лидов, сделок и прибыли использовать только сверенные события.

## 7. Сегменты и самообучение

`hierarchical_forecasts[]` хранит согласованные разрезы:

```json
{
  "dimension": "intent_type",
  "status": "complete",
  "coverage_share": 1.0,
  "rows": [
    {"segment": "commercial", "horizon": 7, "scenario": "base", "value": 740}
  ],
  "notes": ""
}
```

Для `status=complete` суммы сегментов должны совпадать с общим сценарием по каждому горизонту. Для `partial` указать `coverage_share` и не выдавать разрез за полный.

`learning_loop`:

- `status`: `first_run`, `pending` или `active`;
- `evaluations[]`: прошлые `run_id`, горизонт, прогноз, факт, WAPE, bias;
- `action_outcomes[]`: `action_id`, период, статус исполнения, `actual_effect`, `identification_method`, `evidence`, `updated_effect_factor`.

Допустимые статусы идентификации эффекта: `identified`, `directional`, `not_identified`. Для первого запуска массивы пусты. `pending` использовать, если предыдущий запуск есть, но горизонт ещё не завершён. Для `active` нужна хотя бы одна завершённая оценка предыдущего прогноза.

## 8. Правила объединения и статусы качества

- Согласовывать даты в часовом поясе проекта.
- Хранить оригинальные единицы и рассчитывать производные поля явно.
- Не объединять Wordstat с Вебмастером только по похожей строке; использовать стабильный `cluster_id`, интент и URL.
- Для query-level анализа строить связь `query → cluster_id → URL`.
- Не считать клики Вебмастера и органические визиты Метрики идентичными.
- Не суммировать вложенные Wordstat-фразы как независимый спрос.
- Не смешивать общий и органический трафик без раздельных рядов.
- Не смешивать цели с разным бизнес-смыслом в одну конверсию.
- Не суммировать сегменты разных измерений между собой.

Статусы источников:

- `ok` — источник доступен, свеж, покрытие и поля достаточны;
- `partial` — отсутствует детализация или есть ограничение, но целевая метрика остаётся доказуемой;
- `blocked` — нет доступа, обязательных полей или безопасной интерпретации.

Для временного `5xx` повторить запрос один раз. Ошибку параметров исправить и повторить. Пустые query-level indicators при работающих агрегатах считать `partial`, а не `blocked`.

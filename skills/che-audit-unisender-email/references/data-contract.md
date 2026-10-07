# Контракт данных и коннекторов

## Содержание

- Источники истины
- Минимальные возможности коннекторов
- Нормализованный вход
- UTM-контракт
- Ключи хранения


## Источники истины

| Уровень | Основной источник | Назначение |
|---|---|---|
| Отправка и реакция в письме | UniSender | доставлено, открытия, уникальные кликающие, отписки, жалобы, ссылки |
| Поведение на сайте | Метрика или Matomo | визиты, вовлечённость, цели и страницы |
| Сверка web-аналитики | вторая аналитическая система | диагностика расхождений, не суммирование |
| Заявки и продажи | CRM | лиды, статусы, сделки, выручка |

## Минимальные возможности коннекторов

Платформенный адаптер должен предоставить следующие read-only возможности;
перед вызовом сверить реальные названия инструментов и схему аргументов:

- UniSender: `email.campaigns.read`, `email.campaign_status.read`,
  `email.campaign_stats.read`,
  `email.delivery_stats.read`;
- Яндекс.Метрика: `web_analytics.report.read`, `web_analytics.sources.read`,
  `web_analytics.goals.read`;
- amoCRM: `crm.leads.read`, `crm.pipelines.read`,
  `crm.pipeline_statuses.read`.

Наличие UniSender link-level statistics требуется проверить. Методы CRM
возвращают сделки, воронки и статусы, но не являются готовым контрактом
email-атрибуции. Метод Matomo для этого workflow также не подтверждён. Поэтому
полный link-map и attribution/revenue-аудит возможен только из предоставленного
нормализованного входа или другого отдельно подтверждённого источника. Без него
live-аудит обязан вернуть `partial`.

## Нормализованный вход

```json
{
  "as_of": "2026-08-25T00:00:00+07:00",
  "maturity_days": 7,
  "required_sources": ["unisender", "link_stats", "utm", "web_analytics", "web_analytics_comparison", "crm", "resend_dedup"],
  "campaigns": [
    {
      "campaign_id": "123",
      "name": "Название письма",
      "subject": "Тема письма",
      "campaign_type": "primary",
      "sent_at": "2026-08-17T10:00:00+07:00",
      "observation_window": "D+7",
      "comparable": true,
      "source_status": {
        "unisender": "complete",
        "link_stats": "complete",
        "utm": "complete",
        "web_analytics": "complete",
        "web_analytics_comparison": "complete",
        "crm": "complete",
        "resend_dedup": "not_applicable"
      },
      "utm_campaign": "2026-08-17-campaign",
      "web_analytics_source": "metrika",
      "web_analytics_comparison_source": "matomo",
      "web_analytics_comparison_metrics": {
        "sessions": 18,
        "engaged_sessions": 11
      },
      "link_unique_clickers_status": "unavailable",
      "crm_source": "amoCRM",
      "sent": 852,
      "delivered": 850,
      "unique_opens": 200,
      "unique_clickers": 22,
      "unsubscribes": 2,
      "complaints": 0,
      "sessions": 19,
      "engaged_sessions": 12,
      "leads": 2,
      "qualified_leads": 1,
      "sales": 0,
      "revenue": 0,
      "expected_link_count": 1,
      "link_map_total_clicks": 25,
      "links": [
        {
          "utm_content": "hero_button",
          "url": "https://example.com/page?utm_source=unisender&utm_medium=email&utm_campaign=2026-08-17-campaign&utm_content=hero_button",
          "element": "button",
          "position": "hero",
          "all_clicks": 25,
          "unique_clickers": null,
          "sessions": 19,
          "engaged_sessions": 12,
          "leads": 2,
          "qualified_leads": 1,
          "sales": 0,
          "revenue": 0
        }
      ]
    }
  ]
}
```

Допустимые `campaign_type`: `primary`, `resend`, `excluded`. Для `resend` обязательно передавать `original_campaign_id`. Поле `comparable` определяет участие primary-кампании в основном baseline. Неизвестные метрики задавать `null` или не передавать; не использовать `0` вместо отсутствия данных.

`source_status` хранит отдельный статус `complete`, `partial`, `missing` или `not_applicable` для каждого источника. `not_applicable` допустим только для `resend_dedup` у primary. Статус `link_stats=complete` требует непустого `links`, `expected_link_count` и сверки `link_map_total_clicks`; `utm=complete` требует фактических UTM в URL и уникального `utm_content`; `web_analytics=complete` требует основной источник и метрики; `web_analytics_comparison=complete` — отдельный источник и набор сравнения; `crm=complete` требует `crm_source` и бизнес-метрики. Для полного resend требуется валидный `resend_pair_metrics`. Итоговый статус определяется только по источникам из `required_sources`.

`link_unique_clickers_status` принимает `available`, `unavailable` или `partial`. Значение `unavailable` является прозрачным ограничением источника, а не поводом подменять all clicks уникальными людьми.

Для resend `sent_at` должен быть позже исходного письма. Инкрементальные метрики не могут превышать соответствующие показатели resend, а дедуплицированные открытия и кликающие должны равняться показателю original плюс доказанный инкремент.

## UTM-контракт

Каждая ссылка должна иметь:

- `utm_source=unisender`;
- `utm_medium=email`;
- `utm_campaign=<стабильный id или slug кампании>`;
- `utm_content=<уникальный id размещения>`.

Рекомендуемый словарь `utm_content`:

- `hero_image`;
- `hero_button`;
- `intro_text_link`;
- `body_link_01`;
- `case_link`;
- `final_button`;
- `footer_link`.

Один и тот же URL в двух местах должен получать разные `utm_content`. Не включать персональные данные. Для точного пользовательского связывания использовать непрозрачный `click_id`, хранимый отдельно от URL-параметров аналитической классификации.

## Ключи хранения

- Кампания: `campaign_id`.
- Размещение: `campaign_id + utm_content`.
- Снапшот: `campaign_id + observation_window + as_of`.
- Resend-связка: `original_campaign_id + resend_campaign_id`.

Хранить исходные значения и рассчитанные метрики раздельно, чтобы формулы можно было пересчитать.

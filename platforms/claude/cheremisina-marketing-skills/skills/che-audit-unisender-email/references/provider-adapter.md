# Сопоставление возможностей провайдеров

Это справочник адаптации, а не гарантия доступности инструмента.
Проверить реальную схему платформы до вызова; отсутствие означает `partial`.

| Capability | Пример исторического имени |
|---|---|
| `email.campaigns.read` | `unisender.get_campaigns` |
| `email.campaign_status.read` | `unisender.get_campaign_status` |
| `email.campaign_stats.read` | `unisender.get_campaign_common_stats` |
| `email.delivery_stats.read` | `unisender.get_campaign_delivery_stats` |
| `web_analytics.report.read` | `metrika.getReportData` |
| `web_analytics.sources.read` | `metrika.getSources` |
| `web_analytics.goals.read` | `metrika.getGoals` |
| `crm.leads.read` | `amocrm.listLeads` |
| `crm.pipelines.read` | `amocrm.listPipelines` |
| `crm.pipeline_statuses.read` | `amocrm.listPipelineStatuses` |

# Сопоставление возможностей провайдеров

Это справочник адаптации, а не гарантия доступности инструмента.
Проверить реальную схему платформы до вызова; отсутствие означает `partial`.

| Capability | Пример исторического имени |
|---|---|
| `web_analytics.report.read` | `metrika.getReportData` |
| `web_analytics.sources.read` | `metrika.getSources` |
| `web_analytics.goals.read` | `metrika.getGoals` |
| `crm.leads.read` | `amocrm.listLeads` |
| `crm.pipelines.read` | `amocrm.listPipelines` |
| `crm.pipeline_statuses.read` | `amocrm.listPipelineStatuses` |
| `wordstat.regions.read` | `wordstat.get_regions_tree` |
| `wordstat.top_requests.read` | `wordstat.get_top_requests` |
| `wordstat.dynamics.read` | `wordstat.get_dynamics` |
| `webmaster.queries.read` | `webmaster.get_popular_search_queries` |
| `webmaster.query_history.read` | `webmaster.get_all_search_queries_history` |
| `webmaster.query_history.read` | `webmaster.get_query_history` |

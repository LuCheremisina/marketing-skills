# Сопоставление возможностей провайдеров

Это справочник адаптации, а не гарантия доступности инструмента.
Проверить реальную схему платформы до вызова; отсутствие означает `partial`.

| Capability | Пример исторического имени |
|---|---|
| `wordstat.top_requests.read` | `wordstat_get_top_requests` |
| `wordstat.regions.read` | `wordstat_get_regions_tree` |
| `webmaster.hosts.read` | `webmaster_list_hosts` |
| `webmaster.queries.read` | `webmaster_get_popular_search_queries` |
| `web_analytics.report.read` | `metrika_getReportData` |

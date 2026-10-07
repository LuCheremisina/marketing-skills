## 3. Расширить спрос через Wordstat

Для каждого активного seed получить до установленного в реестре лимита:

```text
methodCode: wordstat.top_requests.read
params: {"phrase":"...","regions":[geo_id],"limit":200}
```

GeoID получать через:

```text
methodCode: wordstat.regions.read
params: {"search":"название региона"}
```

Каждый результат записывать в `candidate-ledger.json`, включая отклонённые запросы. Никогда не удалять фразу без причины.

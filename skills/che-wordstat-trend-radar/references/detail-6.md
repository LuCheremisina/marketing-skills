## 7. Рассчитать тренды

Подготовить `input.json` по `references/data-contract.md` и выполнить:

```bash
python3 scripts/analyze_trends.py input.json --history-db trend-history.sqlite --json trend-report.json --markdown trend-report.md
```

Классы: `breakout`, `emerging`, `rapid_growth`, `growing`, `seasonal_rise`, `seasonal_fall`, `structural_decline`, `declining`, `stable`, `watch`, `insufficient_data`.

Не выдавать сигнал только по проценту. Учитывать объём, историю ненулевого спроса, согласованность метрик, волатильность, близость к продукту и покрытие сайта. Отмечать пропуски, дубли, отрицательные значения, неполный месяц и выбранный метод сезонной декомпозиции. Прогнозировать только направлением: `вверх`, `вниз` или `неопределённо`.

#!/usr/bin/env python3
import json, os, shutil
from datetime import datetime

CONFIG_FILE = 'config.json'
CORRELATION_FILE = 'final_correlation.json'
HTML_FILE = 'dashboard.html'
MD_FILE = 'report.md'
OUTPUTS_DIR = os.environ.get('OUTPUT_DIR', os.environ.get('SEO_DEMAND_OUTPUTS', os.path.join(os.getcwd(), 'OUTPUTS')))

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Ошибка: {CONFIG_FILE} не найден."); exit(1)
    with open(CONFIG_FILE) as f: return json.load(f)

def sc(status):
    return {'ТОП-3':'top3','ТОП-10':'top10','ТОП-50':'top50',
            'Слабая видимость':'weak','Не видим':'invisible'}.get(status,'')

def main():
    print("=== Генерация отчётов ===")
    if not os.path.exists(CORRELATION_FILE):
        print(f"Ошибка: {CORRELATION_FILE} не найден. Выполните этап 5."); exit(1)
    with open(CORRELATION_FILE) as f: corr = json.load(f)
    cfg = load_config()
    domain = cfg['domain']
    region = cfg.get('region_name', cfg.get('region', ''))
    niche = cfg['niche']
    date_str = datetime.now().strftime('%d.%m.%Y')
    statuses = ['ТОП-3','ТОП-10','ТОП-50','Слабая видимость','Не видим']
    cnt = {s: sum(1 for c in corr if c['status']==s) for s in statuses}
    total = len(corr)
    growth = sorted([c for c in corr if c['status']=='Не видим'],
                    key=lambda x: x['demand_count'], reverse=True)
    wins = sorted([c for c in corr if c['status'] in ('ТОП-10','ТОП-50')],
                  key=lambda x: x['demand_count'], reverse=True)

    rows = ''
    for c in corr:
        cls = sc(c['status'])
        pos = c['best_position'] if c['best_position'] > 0 else '—'
        rows += (f'<tr class="{cls}" data-status="{c["status"]}">'
                 f'<td>{c["phrase"]}</td><td>{c["demand_count"]}</td>'
                 f'<td>{c["wm_related_count"]}</td><td>{pos}</td>'
                 f'<td>{int(c["total_shows"])}</td><td>{int(c["total_clicks"])}</td>'
                 f'<td><span class="badge {cls}">{c["status"]}</span></td></tr>\n')

    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>SEO: {niche} · {region}</title><style>
body{{font-family:Arial,sans-serif;margin:24px;color:#222}}
h1{{font-size:1.35em;margin-bottom:6px}}.meta{{color:#777;font-size:.88em;margin-bottom:20px}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px}}
.card{{border-radius:8px;padding:12px 18px;min-width:100px;text-align:center}}
.card .num{{font-size:2em;font-weight:bold}}.card .lbl{{font-size:.77em;color:#555;margin-top:2px}}
.g{{background:#d4edda}}.y{{background:#fff3cd}}.o{{background:#ffe0b2}}.r{{background:#f8d7da}}.gr{{background:#e9ecef}}
.filter-bar{{display:flex;gap:8px;align-items:center;margin-bottom:12px}}
select,input{{padding:6px 10px;border:1px solid #ccc;border-radius:4px;font-size:.9em}}
table{{border-collapse:collapse;width:100%;font-size:.88em}}
th{{background:#343a40;color:#fff;padding:8px 10px;text-align:left;cursor:pointer;user-select:none}}
th:hover{{background:#495057}}
td{{border-bottom:1px solid #dee2e6;padding:6px 10px}}
tr:hover td{{background:#f8f9fa}}
.top3 td{{background:#d4edda}}.top10 td{{background:#fff3cd}}
.top50 td{{background:#ffe0b2}}.weak td{{background:#fdebd0}}.invisible td{{background:#f8d7da}}
.badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.78em;font-weight:bold}}
.badge.top3{{background:#28a745;color:#fff}}.badge.top10{{background:#ffc107;color:#333}}
.badge.top50{{background:#fd7e14;color:#fff}}.badge.weak{{background:#e67e22;color:#fff}}
.badge.invisible{{background:#dc3545;color:#fff}}
</style></head><body>
<h1>SEO-аналитика: {niche} в {region}</h1>
<div class="meta">Домен: {domain} &nbsp;&middot;&nbsp; Дата: {date_str}</div>
<div class="cards">
  <div class="card g"><div class="num">{cnt['ТОП-3']}</div><div class="lbl">ТОП-3</div></div>
  <div class="card y"><div class="num">{cnt['ТОП-10']}</div><div class="lbl">ТОП-10</div></div>
  <div class="card o"><div class="num">{cnt['ТОП-50']}</div><div class="lbl">ТОП-50</div></div>
  <div class="card o"><div class="num">{cnt['Слабая видимость']}</div><div class="lbl">Слабая видимость</div></div>
  <div class="card r"><div class="num">{cnt['Не видим']}</div><div class="lbl">Не видим</div></div>
  <div class="card gr"><div class="num">{total}</div><div class="lbl">Всего</div></div>
</div>
<div class="filter-bar">
  <select id="sf" onchange="flt()"><option value="">Все статусы</option>
  <option>ТОП-3</option><option>ТОП-10</option><option>ТОП-50</option>
  <option>Слабая видимость</option><option>Не видим</option></select>
  <input id="q" type="text" placeholder="Поиск по запросу…" oninput="flt()" style="width:220px">
</div>
<table><thead><tr>
<th onclick="srt(0)">Запрос ↕</th><th onclick="srt(1)">Частота ↕</th>
<th onclick="srt(2)">Связ. (WM) ↕</th><th onclick="srt(3)">Позиция ↕</th>
<th onclick="srt(4)">Показы ↕</th><th onclick="srt(5)">Клики ↕</th><th>Статус</th>
</tr></thead><tbody id="tb">{rows}</tbody></table>
<script>
let sd={{}};
function srt(c){{
  const tb=document.getElementById('tb'),rows=[...tb.rows];
  sd[c]=!sd[c];
  rows.sort((a,b)=>{{const av=a.cells[c].textContent.trim(),bv=b.cells[c].textContent.trim();
    const an=parseFloat(av.replace('—','0')),bn=parseFloat(bv.replace('—','0'));
    return (sd[c]?1:-1)*(isNaN(an)||isNaN(bn)?av.localeCompare(bv,'ru'):an-bn);}});
  rows.forEach(r=>tb.appendChild(r));
}}
function flt(){{
  const s=document.getElementById('sf').value,q=document.getElementById('q').value.toLowerCase();
  [...document.querySelectorAll('#tb tr')].forEach(r=>
    r.style.display=(!s||r.dataset.status===s)&&(!q||r.cells[0].textContent.toLowerCase().includes(q))?'':'none');
}}
</script></body></html>"""

    with open(HTML_FILE, 'w', encoding='utf-8') as f: f.write(html)

    gr_rows = '\n'.join(f'| {c["phrase"]} | {c["demand_count"]} |' for c in growth[:15])
    wn_rows = '\n'.join(
        f'| {c["phrase"]} | {c["demand_count"]} | {c["best_position"]} | {int(c["total_shows"])} | {int(c["total_clicks"])} |'
        for c in wins[:10])

    md = f"""# SEO-аналитика: {niche} в {region} ({domain})
**Дата:** {date_str}

## Общая статистика

| Статус | Кол-во | % |
|--------|--------|---|
| ТОП-3 | {cnt['ТОП-3']} | {cnt['ТОП-3']/total*100:.1f}% |
| ТОП-10 | {cnt['ТОП-10']} | {cnt['ТОП-10']/total*100:.1f}% |
| ТОП-50 | {cnt['ТОП-50']} | {cnt['ТОП-50']/total*100:.1f}% |
| Слабая видимость | {cnt['Слабая видимость']} | {cnt['Слабая видимость']/total*100:.1f}% |
| Не видим | {cnt['Не видим']} | {cnt['Не видим']/total*100:.1f}% |
| **Итого** | **{total}** | 100% |

## Точки роста — высокий спрос, нет видимости (топ-15)

| Запрос | Частота Wordstat |
|--------|-----------------|
{gr_rows}

## Быстрые победы — есть позиции, высокий спрос (топ-10)

| Запрос | Частота | Позиция | Показы | Клики |
|--------|---------|---------|--------|-------|
{wn_rows}

## Инсайты и гипотезы роста

> ⚡ Раздел заполняется на Этапе 7: агент анализирует final_correlation.json
> и генерирует 5–7 инсайтов + приоритизированные гипотезы роста.

---
*Отчёт сгенерирован скиллом che-seo-demand-analytics*
"""
    with open(MD_FILE, 'w', encoding='utf-8') as f: f.write(md)
    print(f"✅ Отчёты сгенерированы: {HTML_FILE}, {MD_FILE}")

    if os.path.exists(OUTPUTS_DIR):
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        out = os.path.join(OUTPUTS_DIR, f'seo-analytics_{domain}_{ts}')
        os.makedirs(out, exist_ok=True)
        for fn in [HTML_FILE, MD_FILE, 'final_correlation.json', 'config.json']:
            if os.path.exists(fn): shutil.copy(fn, out)
        print(f"Файлы сохранены в OUTPUTS/: {out}")

if __name__ == "__main__":
    main()

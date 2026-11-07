"""Render paired real model runs into the README without changing their answers."""
import json
from pathlib import Path
from scripts.smoke_research import CASES

labels = {'automakers': 'Automakers', 'consumer-staples': 'Consumer staples', 'cloud': 'Cloud platforms'}
records = {}
for slug, tickers, question in CASES:
    record = json.loads((Path('evaluations') / f'{slug}.json').read_text())
    assert record['question'] == question, slug
    assert record['agent']['investigation']['scope']['tickers'] == tickers, slug
    assert record['agent']['investigation']['status'] == 'complete', slug
    assert record['baseline_no_tools_no_system'], slug
    records[slug] = record

block = ['### Recorded answers from the validation runs', '',
         'These are actual Gemini runs, not illustrative transcripts. Each pair uses the same question, dates and model (`gemini-3.5-flash-lite`). Baselines have no tools or system prompt. Complete answers and agent/tool traces are retained in the linked JSON files. Coca-Cola replaces the previously featured NVIDIA case; older semiconductor records remain archived.', '',
         '| Case | Research status | Research latency | Trace |', '|---|---|---:|---|']
for slug, record in records.items():
    block.append(f'| {labels[slug]} | complete | {record["elapsed_seconds"]} s | [Full trace and baseline](evaluations/{slug}.json) |')
for slug, record in records.items():
    block += ['', f'#### {labels[slug]}: same-model comparison', '']
    if record.get('comparison_note'):
        block += [record['comparison_note'], '']
    block += ['<details>', '<summary>No tools, no system prompt — complete recorded answer</summary>', '',
              '\n'.join(line.rstrip() for line in record['baseline_no_tools_no_system'].splitlines()), '', '</details>', '', '<details>',
              '<summary>The Receipts — complete evidence-based answer</summary>', '',
              record['agent']['response'], '', '</details>', '']

readme = Path('README.md')
text = readme.read_text()
start = text.index('### Recorded answers from the ')
end = text.index('To reproduce all three real model/tool runs and baselines', start)
readme.write_text(text[:start] + '\n'.join(block) + '\n\n' + text[end:])
print('README includes three matched question/model comparisons.')

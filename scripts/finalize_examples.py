"""Apply the current deterministic summary policy to recorded real model runs."""
import json
from datetime import datetime, timezone
from pathlib import Path
from receipts.research import calculated_summary, format_report, validate_report

for slug in ('automakers', 'chips', 'cloud'):
    path = Path('evaluations') / f'{slug}.json'
    record = json.loads(path.read_text())
    result = record['agent']
    investigation = result['investigation']
    assert investigation['status'] == 'complete', slug
    ledger = {r['id']: r for r in investigation['evidence']}
    report = investigation['report']
    report['summary'] = calculated_summary(ledger, investigation['scope']['tickers'][0]) or report['summary']
    _, errors = validate_report(report, ledger, investigation['scope'])
    assert not errors, (slug, errors)
    result['response'] = format_report(report, ledger)
    record['deterministic_summary_finalized_at'] = datetime.now(timezone.utc).isoformat()
    record['finalization_note'] = 'Real recorded model and source calls retained unchanged. Opening summary recomputed from this exact evidence under the final application policy.'
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(slug, 'verified', record['elapsed_seconds'])

readme = Path('README.md')
text = readme.read_text()
block = ['### Recorded answers from the final validation runs',
         '', 'These are actual Gemini runs, not illustrative transcripts. Full model/tool traces are retained in the linked JSON files. The opening agent summary uses the final deterministic arithmetic policy applied to the recorded evidence.',
         '', '| Case | Research status | Research latency | Trace |', '|---|---|---:|---|']
for slug in ('automakers', 'chips', 'cloud'):
    record = json.loads((Path('evaluations') / f'{slug}.json').read_text())
    block.append(f'| {slug} | {record["agent"]["investigation"]["status"]} | {record["elapsed_seconds"]} s | [Full trace](evaluations/{slug}.json) |')
for slug in ('automakers', 'chips', 'cloud'):
    record = json.loads((Path('evaluations') / f'{slug}.json').read_text())
    block += ['', f'#### {slug.title()}: same-model comparison', '', '<details>', '<summary>No tools, no system prompt — complete recorded answer</summary>', '',
              record['baseline_no_tools_no_system'], '', '</details>', '', '<details>', '<summary>The Receipts — complete evidence-based answer</summary>', '',
              record['agent']['response'], '', '</details>', '']
text = text.replace('<!-- VERIFIED_MODEL_COMPARISONS -->', '\n'.join(block))
readme.write_text(text)

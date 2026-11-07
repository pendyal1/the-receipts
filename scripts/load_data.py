"""Archive real public sources for the featured cases and archived starter industries."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from receipts.config import ROOT, INDUSTRIES
from receipts.sources import Sources

sources = Sources(archive=True)

def load(ticker, primary=False):
    counts = {'ticker': ticker}
    for label, fn in [('financials', lambda: sources.financials(ticker, '2020-01-01', '2025-03-01', '2025-03-01')),
                      ('prices', lambda: sources.prices(ticker, '2020-01-01', '2025-03-01'))]:
        try:
            result = fn()
            counts[label] = len(result) if isinstance(result, list) else len(result['observations'])
        except Exception as exc:
            counts[label] = str(exc)
    if primary:
        try:
            records = sources.passages(ticker, '2020-01-01', '2023-03-01')
            counts['claims'] = sum(r['kind'] == 'claim' for r in records)
        except Exception as exc:
            counts['claims'] = str(exc)
    sources.archive_loaded()
    return counts

if __name__ == '__main__':
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(load, t, True) for group in [*INDUSTRIES.values(), ['KO', 'PEP']] for t in group]
        for future in as_completed(jobs):
            result = future.result()
            results.append(result)
            print(json.dumps(result), flush=True)
    sources.macro('2020-01-01', '2025-03-01')
    sources.archive_loaded()
    manifest = {'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'scope': {'start': '2020-01-01', 'as_of': '2023-03-01', 'through': '2025-03-01'},
                'companies': results, 'archive_files': len(list(sources.directory.glob('*.json.gz'))),
                'notes': 'Unmodified UTF-8 source bodies with SHA-256, original URL and retrieval timestamp. Public historical data; archived at build time, not known at historical dates.'}
    (ROOT / 'data' / 'manifest.json').write_text(json.dumps(manifest, indent=2))

"""Public-data adapters. Archived bytes retain retrieval time and SHA-256 provenance."""
import csv
import gzip
import hashlib
import io
import json
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup
from .config import COMPANIES, METRICS, ROOT, USER_AGENT


class SourceError(Exception):
    pass


@lru_cache(maxsize=1)
def bundled_company_directory():
    """The dated SEC lookup snapshot also avoids a separate directory request per ticker."""
    path = ROOT / 'static' / 'companies.json'
    return {row['ticker']: row for row in json.loads(path.read_text())['companies']}


class Sources:
    def __init__(self, snapshot_dir=None, offline=False, archive=False):
        self.directory = Path(snapshot_dir or ROOT / 'data' / 'snapshots')
        self.offline = offline
        self.archive = archive
        self._cache = {}
        self._lock = threading.RLock()
        self._sec_lock = threading.Lock()
        self._last_sec = 0.0

    def fetch(self, url):
        key = hashlib.sha256(url.encode()).hexdigest()
        with self._lock:
            if key in self._cache:
                return self._cache[key]
            path = self.directory / f'{key}.json.gz'
            legacy = self.directory / f'{key}.json'
            if path.exists() or legacy.exists():
                record = json.loads(gzip.decompress(path.read_bytes()).decode() if path.exists() else legacy.read_text())
                if hashlib.sha256(record['body'].encode()).hexdigest() != record['sha256']:
                    raise SourceError('Archived source failed its integrity check.')
                self._remember(key, record)
                return record
        if self.offline:
            raise SourceError('This source is outside the bundled snapshot. Live retrieval is disabled.')
        # A single process-wide adapter is shared by Researchers; <5 SEC requests/s.
        if 'sec.gov/' in url:
            with self._sec_lock:
                time.sleep(max(0, .26 - (time.monotonic() - self._last_sec)))
                self._last_sec = time.monotonic()
        try:
            with httpx.Client(timeout=18, follow_redirects=False, headers={'User-Agent': USER_AGENT}) as client:
                response = client.get(url)
                response.raise_for_status()
            body = response.text
            if len(body) > 25_000_000:
                raise SourceError('Source exceeds the bounded download size.')
            record = {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                      'sha256': hashlib.sha256(body.encode()).hexdigest(), 'body': body}
            with self._lock:
                self._remember(key, record)
            return record
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceError(f'Source unavailable ({type(exc).__name__}). No data was substituted.') from exc

    def _remember(self, key, record):
        if self.archive:
            self.directory.mkdir(parents=True, exist_ok=True)
            (self.directory / f'{key}.json.gz').write_bytes(gzip.compress(json.dumps(record, ensure_ascii=False).encode(), mtime=0))
        # Bound memory by source text size as well as number of URLs.
        self._cache[key] = record
        while len(self._cache) > 160 or sum(len(r['body']) for r in self._cache.values()) > 64_000_000:
            self._cache.pop(next(iter(self._cache)))

    def json(self, url):
        record = self.fetch(url)
        try:
            return json.loads(record['body']), self.provenance(record)
        except ValueError as exc:
            raise SourceError('Source returned an invalid JSON document.') from exc

    @staticmethod
    def provenance(record):
        return {k: record[k] for k in ('url', 'retrieved_at', 'sha256')}

    def resolve(self, ticker):
        ticker = ticker.upper().strip()
        if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,9}', ticker):
            raise SourceError('Use a U.S. exchange ticker, such as TSLA.')
        if ticker in COMPANIES:
            name, cik = COMPANIES[ticker]
            return {'ticker': ticker, 'name': name, 'cik': cik}
        company = bundled_company_directory().get(ticker)
        if company:
            return {'ticker': ticker, 'name': company['name'], 'cik': company['cik']}
        directory, _ = self.json('https://www.sec.gov/files/company_tickers.json')
        for company in directory.values():
            if company['ticker'].upper() == ticker:
                return {'ticker': ticker, 'name': company['title'], 'cik': company['cik_str']}
        raise SourceError(f'{ticker} was not found in the SEC ticker directory. Foreign/private companies are not covered.')

    def financials(self, ticker, start, end, available_by):
        company = self.resolve(ticker)
        data, provenance = self.json(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{company["cik"]:010d}.json')
        gaap = data.get('facts', {}).get('us-gaap', {})
        records = []
        # Only annual duration facts (330–380 days); never mix YTD/quarter/instant facts.
        for metric, tags in METRICS.items():
            candidates = []
            for rank, tag in enumerate(tags):
                for fact in gaap.get(tag, {}).get('units', {}).get('USD', []):
                    if not fact.get('start') or not fact.get('filed'):
                        continue
                    days = (date.fromisoformat(fact['end']) - date.fromisoformat(fact['start'])).days
                    if (330 <= days <= 380 and start <= fact['end'] <= end
                            and fact['filed'] <= available_by and fact.get('form') in ('10-K', '10-K/A')):
                        candidates.append({**fact, 'tag': tag, 'rank': rank})
            # Earliest filed value per exact fiscal period: no later restatement leaks.
            by_period = {}
            for item in sorted(candidates, key=lambda x: (x['filed'], x['rank'])):
                by_period.setdefault((item['start'], item['end']), item)
            # Protect against differing tag start dates for one fiscal year.
            by_end = {}
            for item in sorted(by_period.values(), key=lambda x: (x['filed'], x['rank'])):
                by_end.setdefault(item['end'], item)
            for item in sorted(by_end.values(), key=lambda x: x['end']):
                accession = item['accn']
                filing_url = f'https://www.sec.gov/Archives/edgar/data/{company["cik"]}/{accession.replace("-", "")}/{accession}-index.html'
                records.append({'kind': 'financial', 'ticker': ticker, 'metric': metric,
                    'value': item['val'], 'unit': 'USD', 'period_start': item['start'],
                    'period_end': item['end'], 'filed': item['filed'], 'accession': accession,
                    'tag': item['tag'], 'url': filing_url, 'provenance': provenance,
                    'selection': 'Earliest filed annual USD fact for this fiscal period; original reported basis.'})
        return records

    def filings(self, ticker, start, end, limit=3, forms=('10-K', '10-Q', '8-K')):
        company = self.resolve(ticker)
        data, _ = self.json(f'https://data.sec.gov/submissions/CIK{company["cik"]:010d}.json')
        blocks = [data['filings']['recent']]
        # Older filings are separate SEC submissions files. Read only overlapping blocks.
        for file in data.get('filings', {}).get('files', []):
            if file['filingFrom'] <= end and file['filingTo'] >= start:
                name = file['name']
                if re.fullmatch(r'CIK\d+-submissions-\d+\.json', name):
                    block, _ = self.json(f'https://data.sec.gov/submissions/{name}')
                    blocks.append(block)
        records = []
        seen = set()
        for block in blocks:
            for i, form in enumerate(block.get('form', [])):
                filed = block['filingDate'][i]
                if form not in forms or not start <= filed <= end:
                    continue
                acc = block['accessionNumber'][i]
                doc = block['primaryDocument'][i]
                if acc in seen or not re.fullmatch(r'[\w.\-/]+', doc) or '..' in doc:
                    continue
                seen.add(acc)
                records.append({'kind': 'filing', 'ticker': ticker, 'form': form, 'filed': filed,
                    'period_end': block.get('reportDate', [''] * len(block['form']))[i],
                    'accession': acc, 'url': f'https://www.sec.gov/Archives/edgar/data/{company["cik"]}/{acc.replace("-", "")}/{doc}'})
        # Most recent annual/quarterly filings; do not bury the current outlook under old annual reports.
        return sorted(records, key=lambda r: r['filed'], reverse=True)[:limit]

    def passages(self, ticker, start, cutoff, query='', limit=10):
        filings = self.filings(ticker, start, cutoff, limit=3, forms=('10-K', '10-Q'))
        tokens = set(re.findall(r'[a-z]{4,}', query.lower())) - {'company', 'compare', 'management', 'about', 'between'}
        records = []
        for filing in filings:
            try:
                source = self.fetch(filing['url'])
                soup = BeautifulSoup(source['body'], 'html.parser')
                for element in soup(['script', 'style', 'header', 'footer', 'ix:header']):
                    element.decompose()
                # Filing DOM commonly contains div paragraphs. Whole-text sentence chunks
                # avoid duplicating nested tags and preserve exact normalized source excerpts.
                text = ' '.join(soup.get_text(' ', strip=True).split())
                sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
                scored = []
                for position, sentence in enumerate(sentences):
                    if not 55 <= len(sentence) <= 950:
                        continue
                    outlook = re.search(r'\b(?:we|our company|tesla|nvidia|microsoft)\s+(?:(?:currently|also|therefore|generally)\s+)?(?:expect|anticipate|intend|plan|target|aim)\b', sentence, re.I)
                    if not outlook:
                        continue
                    # Exclude accounting policies, exhibit indexes and auditor opinions.
                    if re.search(r'forward.looking statements|actual results.*differ|undue reliance|equity incentive|omnibus|audit|tax position|form s-|revenue (?:is|are) recognized|consideration we expect|costs of (?:obtaining|fulfilling)', sentence, re.I):
                        continue
                    score = 5 + sum(word in sentence.lower() for word in tokens)
                    score += 4 * bool(re.search(r'\b(?:revenue|growth|capital expenditures|cash flow|operating income|profit|margin|production|deliveries|demand|investment|investments)\b', sentence, re.I))
                    score += 3 * bool(re.search(r'\b(?:increase|grow|expand|billion|million|percent)\b|\d+%', sentence, re.I))
                    score += 2 * bool(re.search(r'we (?:currently )?(?:expect|anticipate)', sentence, re.I))
                    # Prefer substantive forward expectations to generic legal risk statements.
                    score -= 3 * bool(re.search(r'litigation|regulatory|regulations|comply|competition|competitors', sentence, re.I))
                    scored.append((score, position, sentence))
                for score, position, sentence in sorted(scored, reverse=True)[:4]:
                    if score < 3:
                        continue
                    records.append({**filing, 'kind': 'claim', 'excerpt': sentence,
                        'locator': f'Normalized sentence {position + 1}; search the filing for this excerpt.',
                        'provenance': self.provenance(source),
                        'scope': 'Filing management outlook passage, not necessarily numeric guidance or a testable promise.'})
            except SourceError as exc:
                records.append({**filing, 'kind': 'source_gap', 'error': str(exc)})
        return records[:limit]

    def macro(self, start, end):
        records = []
        for series, label, unit in [('FEDFUNDS', 'Effective federal funds rate', 'percent'),
                                     ('CPIAUCSL', 'CPI, all urban consumers, seasonally adjusted', 'index 1982–84=100')]:
            url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?' + urlencode({'id': series, 'cosd': start, 'coed': end})
            try:
                source = self.fetch(url)
                rows = csv.DictReader(io.StringIO(source['body']))
                observations = []
                for row in rows:
                    when = row.get('observation_date') or row.get('DATE')
                    value = row.get(series)
                    if when and start <= when <= end and value not in (None, '.', ''):
                        observations.append({'date': when, 'value': float(value)})
                if not observations:
                    raise SourceError('No FRED observations in the requested window.')
                records.append({'kind': 'macro', 'series': series, 'label': label, 'unit': unit,
                    'observations': observations, 'url': f'https://fred.stlouisfed.org/series/{series}',
                    'provenance': self.provenance(source),
                    'scope': 'Current revised historical series, NOT an as-of vintage. Excluded from the historical knowledge room.'})
            except SourceError as exc:
                records.append({'kind': 'source_gap', 'series': series, 'url': url, 'error': str(exc)})
        return records

    def prices(self, ticker, start, end):
        self.resolve(ticker)
        t1 = int(datetime.combine(date.fromisoformat(start), datetime.min.time(), tzinfo=timezone.utc).timestamp())
        t2 = int(datetime.combine(date.fromisoformat(end) + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?' + urlencode({'period1': t1, 'period2': t2, 'interval': '1d'})
        data, provenance = self.json(url)
        result = (data.get('chart', {}).get('result') or [None])[0]
        if not result:
            raise SourceError('The historical price provider returned no observations.')
        indicators = result.get('indicators', {})
        adjusted = (indicators.get('adjclose') or [{}])[0].get('adjclose')
        if not adjusted:
            raise SourceError('Adjusted-close prices are missing; raw close was not substituted.')
        values = []
        for stamp, value in zip(result.get('timestamp', []), adjusted):
            when = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
            if value is not None and value > 0 and start <= when <= end:
                values.append({'date': when, 'value': round(value, 6)})
        if not values:
            raise SourceError('No trading days in this interval.')
        return {'kind': 'price', 'ticker': ticker, 'currency': result.get('meta', {}).get('currency'),
            'observations': values, 'url': f'https://finance.yahoo.com/quote/{ticker}/history/',
            'provenance': provenance,
            'scope': 'Yahoo Finance unofficial chart endpoint; vendor-adjusted close, retrospective adjustments. Not an executable historical quote, causal event study, or guaranteed total return.'}

    def archive_loaded(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with self._lock:
            for key, record in self._cache.items():
                (self.directory / f'{key}.json.gz').write_bytes(gzip.compress(json.dumps(record, ensure_ascii=False).encode(), mtime=0))

import hashlib
import json
from pathlib import Path

import pytest
from receipts.sources import Sources, SourceError


class Facts(Sources):
    def __init__(self, tags):
        super().__init__(offline=True)
        self.tags = tags
    def json(self, url):
        return {'facts': {'us-gaap': self.tags}}, {'url': url, 'retrieved_at': 'test', 'sha256': 'test'}


def fact(value, filed='2023-02-01', start='2022-01-01', end='2022-12-31', **extra):
    return dict(val=value, start=start, end=end, filed=filed, form='10-K', accn='0000000000-23-000001', **extra)


def tag(*facts):
    return {'units': {'USD': list(facts)}}


def test_cutoff_prevents_later_restated_value_and_ytd_mixing():
    source = Facts({'Revenues': tag(fact(100), fact(999, filed='2024-02-01'),
                                     fact(20, start='2022-10-01'), fact(80, end='2022-09-30'))})
    rows = source.financials('TSLA', '2022-01-01', '2023-01-01', '2023-03-01')
    assert len(rows) == 1
    assert rows[0]['value'] == 100 and rows[0]['filed'] == '2023-02-01'
    assert not source.financials('TSLA', '2022-01-01', '2023-01-01', '2023-01-01')


def test_total_revenue_precedes_contract_revenue_for_financing_companies():
    source = Facts({'Revenues': tag(fact(187)), 'RevenueFromContractWithCustomerExcludingAssessedTax': tag(fact(171))})
    row = source.financials('GM', '2022-01-01', '2023-01-01', '2023-03-01')[0]
    assert row['value'] == 187 and row['tag'] == 'Revenues'


def test_historical_fact_selection_does_not_restate_after_cutoff():
    source = Facts({'Revenues': tag(fact(101, filed='2023-02-01'), fact(102, filed='2024-01-01'))})
    assert source.financials('TSLA', '2022-01-01', '2024-01-01', '2025-01-01')[0]['value'] == 101


@pytest.mark.parametrize('ticker', ['../../etc/passwd', 'http://localhost', 'A&x=y', ''])
def test_invalid_ticker_cannot_change_network_destination(ticker):
    with pytest.raises(SourceError):
        Sources(offline=True).resolve(ticker)


def test_snapshot_integrity_check(tmp_path):
    source = Sources(tmp_path, offline=True)
    url = 'https://data.sec.gov/example'
    path = tmp_path / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    path.write_text(json.dumps({'body': 'tampered', 'sha256': 'bad', 'url': url}))
    with pytest.raises(SourceError, match='integrity'):
        source.fetch(url)


def test_offline_missing_source_explicit_failure(tmp_path):
    with pytest.raises(SourceError, match='outside the bundled snapshot'):
        Sources(tmp_path, offline=True).fetch('https://data.sec.gov/not-bundled')


def test_lookup_and_research_share_the_bundled_sec_company_identity():
    company = Sources(offline=True).resolve('KO')
    assert company == {'ticker': 'KO', 'name': 'Coca-Cola', 'cik': 21344}


def test_real_bundled_figures_and_date_integrity():
    source = Sources(offline=True)
    rows = source.financials('TSLA', '2020-01-01', '2025-03-01', '2025-03-01')
    revenue = {r['period_end']: r['value'] for r in rows if r['metric'] == 'revenue'}
    assert revenue['2022-12-31'] == 81_462_000_000
    assert revenue['2024-12-31'] == 97_690_000_000
    assert all(r['filed'] <= '2025-03-01' for r in rows)
    gm = source.financials('GM', '2020-01-01', '2025-03-01', '2025-03-01')
    assert next(r['value'] for r in gm if r['metric'] == 'revenue' and r['period_end'] == '2024-12-31') == 187_442_000_000


def test_passages_exclude_exhibit_and_auditor_text_and_respect_date():
    records = Sources(offline=True).passages('TSLA', '2020-01-01', '2023-03-01', 'growth revenue capital expenditures')
    claims = [r for r in records if r['kind'] == 'claim']
    assert claims
    assert all(r['filed'] <= '2023-03-01' for r in claims)
    assert all('Equity Incentive Plan' not in r['excerpt'] for r in claims)
    assert any('capital expenditure' in r['excerpt'].lower() or 'grow' in r['excerpt'].lower() for r in claims)


def test_price_series_has_trading_days_and_explicit_adjustment_limit():
    record = Sources(offline=True).prices('TSLA', '2020-01-01', '2025-03-01')
    assert len(record['observations']) > 1200
    assert record['observations'][0]['date'] == '2020-01-02'
    assert record['observations'][-1]['date'] == '2025-02-28'
    assert 'retrospective' in record['scope'].lower()

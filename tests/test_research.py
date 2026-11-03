import json
import threading
import time

import pytest
from receipts.research import Investigator, Scope, validate_report
from receipts.model import ModelError
from receipts.sources import SourceError

SCOPE = {'tickers': ['TSLA', 'GM'], 'start': '2020-01-01', 'as_of': '2023-03-01', 'through': '2025-03-01'}


class FakeSources:
    def financials(self, ticker, start, end, available_by):
        return [{'kind': 'financial', 'ticker': ticker, 'value': 100, 'metric': 'revenue',
                 'period_end': '2022-12-31', 'filed': '2023-02-01', 'url': 'https://www.sec.gov/example'}]
    def passages(self, ticker, start, cutoff, query=''):
        return [{'kind': 'claim', 'ticker': ticker, 'excerpt': 'We expect capital expenditures to grow.', 'filed': '2023-02-01', 'url': 'https://www.sec.gov/claim'}]
    def macro(self, start, end):
        return [{'kind': 'macro', 'series': 'FEDFUNDS', 'observations': [{'date': start, 'value': 1}], 'url': 'https://fred.stlouisfed.org/series/FEDFUNDS'}]
    def prices(self, ticker, start, end):
        return {'kind': 'price', 'ticker': ticker, 'observations': [{'date': start, 'value': 10}], 'url': 'https://finance.yahoo.com/'}


class FakeModel:
    def __init__(self, gap=False):
        self.contexts=[]
        self.active=0
        self.max_active=0
        self.lock=threading.Lock()
        self.gap=gap
    def generate(self, system, payload, **kwargs):
        if 'You are Lead.' in system:
            if not payload['explicit_scope'] and not payload['previous_scope']:
                return {'clarification': 'Which company and dates?'}
            return {'scope': payload['explicit_scope'] or payload['previous_scope'], 'tasks': {}}
        if 'You are an independent Researcher' in system:
            with self.lock:
                self.active+=1
                self.max_active=max(self.max_active,self.active)
                self.contexts.append(json.loads(json.dumps(payload)))
            time.sleep(.02)
            with self.lock:
                self.active-=1
            if not payload['turns']:
                return {'calls':[{'tool': payload['tool_menu'][0], 'ticker': payload['scope']['tickers'][0]}]}
            return {'findings':[{'text':'Found a record.', 'evidence_ids':[payload['turns'][0]['results'][0]['id']]}], 'gaps':[]}
        if 'You are Lead reviewing' in system:
            return {'gap_tasks':[{'agent':'Financials','tool':'financials_later','ticker':'GM','focus':'Missing peer'}] if self.gap else [], 'remaining_limits':[]}
        if 'You are Writer.' in system:
            record=next(r for r in payload['evidence'] if r['kind']=='financial')
            return {'title':'A case','verdict':'insufficient evidence','summary':f'Annual revenue is 100 [{record["id"]}].',
                    'sections':[{'title':'Evidence','text':f'Reported revenue is 100 [{record["id"]}].'}], 'receipts':[], 'limits':['Scope cannot prove intent.']}
        raise AssertionError('Unexpected role')


def test_parallel_fresh_contexts_and_project_one_trace_contract():
    model=FakeModel()
    result=Investigator(FakeSources(),model).run('Compare outcomes',SCOPE)
    assert result['investigation']['status']=='complete'
    assert model.max_active>=2
    initial=[c for c in model.contexts if not c['turns']]
    assert {c['role'] for c in initial}=={'Claims','Financials','Peers','Context'}
    assert all('evidence' not in c and 'findings' not in c for c in initial)
    assert all({'agent','name','args','result'}<=c.keys() and isinstance(c['result'],str) for c in result['tool_calls'])
    assert any(t['agent']=='Writer' for t in result['tool_calls'])


def test_gap_filling_is_bounded_and_collects_missing_peer():
    result=Investigator(FakeSources(),FakeModel(gap=True)).run('Compare',SCOPE)
    assert result['investigation']['rounds']==2
    assert any(t['name']=='financials_later' and t['args']['ticker']=='GM' for t in result['tool_calls'])
    signatures=[(t['name'],t['args'].get('ticker')) for t in result['tool_calls'] if t['name'] in ['claims','financials_then','financials_later','macro','prices']]
    assert len(signatures)==len(set(signatures))


def test_vague_input_asks_before_source_calls():
    result=Investigator(FakeSources(),FakeModel()).run('Is it good?')
    assert result['investigation']['status']=='clarification'
    assert [t['name'] for t in result['tool_calls']]==['plan']


def test_model_failure_never_masquerades_as_research():
    class Broken:
        def generate(self,*args,**kwargs):raise ModelError('No access')
    result=Investigator(FakeSources(),Broken()).run('Compare',SCOPE)
    assert result['investigation']['status']=='unavailable'
    assert result['investigation']['report'] is None


def test_fabricated_citation_rejected_and_grouped_real_citations_normalized():
    evidence={'Eabc':{'kind':'financial'}}
    raw={'verdict':'mixed','summary':'Claim [Enope]','sections':[{'title':'Evidence','text':'Value [Eabc]'}]}
    assert 'Unknown or unavailable evidence citation.' in validate_report(raw,evidence)[1]
    raw['summary']='Claim [Eabc, Eabc]'
    report,errors=validate_report(raw,evidence)
    assert not errors and report['summary']=='Claim [Eabc] [Eabc]'


def test_financial_fact_cannot_be_management_promise():
    evidence={'Eabc':{'kind':'financial'}}
    raw={'verdict':'mixed','summary':'Claim [Eabc]','sections':[{'title':'Evidence','text':'Value [Eabc]'}],
         'receipts':[{'claim_id':'Eabc','outcome_ids':['Eabc'],'assessment':'supported','explanation':'same value'}]}
    assert any('management passage' in e for e in validate_report(raw,evidence)[1])


def test_receipt_requires_same_company_outcome():
    evidence={'Eclaim':{'kind':'claim','phase':'known_then','ticker':'TSLA'},'Egm':{'kind':'financial','ticker':'GM'}}
    raw={'verdict':'mixed','summary':'Claim [Eclaim]','sections':[{'title':'Evidence','text':'Value [Egm]'}],
         'receipts':[{'claim_id':'Eclaim','outcome_ids':['Egm'],'assessment':'supported','explanation':'mismatch'}]}
    assert any('same entity' in e for e in validate_report(raw,evidence)[1])


@pytest.mark.parametrize('bad', [dict(SCOPE,through='2030-01-01'),dict(SCOPE,as_of='2019-01-01'),dict(SCOPE,tickers=['A','B','C','D'])])
def test_invalid_scope_rejected(bad):
    with pytest.raises(ValueError):Scope.model_validate(bad)


def test_unsupported_success_is_conservatively_demoted():
    evidence={'Eclaim':{'kind':'claim','phase':'known_then','ticker':'TSLA'}}
    raw={'verdict':'supported','summary':'Expectation [Eclaim]','sections':[{'title':'Evidence','text':'Outlook [Eclaim]'}],
         'receipts':[{'claim_id':'Eclaim','outcome_ids':[],'assessment':'supported','explanation':'testable estimate'}]}
    report,errors=validate_report(raw,evidence)
    assert not errors
    assert report['verdict']=='insufficient evidence'
    assert report['receipts'][0]['assessment']=='not testable'


def test_forecast_cannot_be_tested_with_prior_period_or_wrong_metric():
    from receipts.research import claim_test_candidates
    e={'Eclaim':{'kind':'claim','phase':'known_then','ticker':'TSLA','filed':'2023-01-31','excerpt':'We expect capital expenditures of $6 to $8 billion in 2023.'},
       'Eold':{'kind':'financial','ticker':'TSLA','metric':'capex','period_end':'2022-12-31'},
       'Ewrong':{'kind':'financial','ticker':'TSLA','metric':'revenue','period_end':'2023-12-31'},
       'Eright':{'kind':'financial','ticker':'TSLA','metric':'capex','period_end':'2023-12-31'}}
    assert claim_test_candidates(e)['Eclaim']['allowed_outcome_ids']==['Eright']
    raw={'verdict':'supported','summary':'Outlook [Eclaim]','sections':[{'title':'Evidence','text':'Outcome [Eold]'}],
         'receipts':[{'claim_id':'Eclaim','outcome_ids':['Eold'],'assessment':'supported','explanation':'invalid temporal claim'}]}
    assert any('before the management' in s for s in validate_report(raw,e)[1])


def test_known_then_section_cannot_cite_future_filing_or_revised_macro():
    evidence={'Efuture':{'kind':'financial','filed':'2024-02-01'},'Emacro':{'kind':'macro'}}
    raw={'verdict':'insufficient evidence','summary':'Records [Efuture]',
         'sections':[{'title':'What was knowable then','text':'Historical context [Efuture] [Emacro]'}]}
    assert any('hindsight context' in e for e in validate_report(raw,evidence,SCOPE)[1])


def test_quoted_capex_ranges_are_checked_with_arithmetic():
    from receipts.research import quantitative_range_checks
    evidence={'Eclaim':{'kind':'claim','phase':'known_then','ticker':'TSLA','filed':'2023-01-31',
        'excerpt':'We currently expect our capital expenditures to be between $6.00 to $8.00 billion in 2023 and between $7.00 to $9.00 billion in each of the following two fiscal years.'},
        'E2023':{'kind':'financial','ticker':'TSLA','metric':'capex','period_end':'2023-12-31','value':8_898_000_000},
        'E2024':{'kind':'financial','ticker':'TSLA','metric':'capex','period_end':'2024-12-31','value':11_339_000_000}}
    checks=quantitative_range_checks(evidence)
    assert len(checks)==2
    assert all(c['relation']=='above quoted range' for c in checks)
    assert checks[1]['upper']==9_000_000_000


def test_gap_references_can_explain_missing_evidence_but_not_facts():
    evidence={'Egap':{'kind':'source_gap','error':'No annual capex under supported tags'}}
    raw={'verdict':'insufficient evidence','summary':'Capex is not available [Egap].',
         'sections':[{'title':'Cross-examination','text':'The forecast is not testable because capex is missing [Egap].'}]}
    assert not validate_report(raw,evidence)[1]
    raw['summary']='Capex was $100 billion [Egap].'
    assert any('coverage-gap' in e for e in validate_report(raw,evidence)[1])


def test_calculated_summary_keeps_revenue_and_profit_directions_separate():
    from receipts.research import calculated_summary
    records={}
    for eid,metric,end,value in [('Er1','revenue','2023-12-31',96_773_000_000),('Er2','revenue','2024-12-31',97_690_000_000),('En1','net_income','2023-12-31',14_997_000_000),('En2','net_income','2024-12-31',7_091_000_000)]:
        records[eid]={'kind':'financial','ticker':'TSLA','metric':metric,'period_end':end,'filed':'2025-01-01','value':value}
    summary=calculated_summary(records,'TSLA')
    assert 'up from $96.773 billion' in summary
    assert 'down from $14.997 billion' in summary
    assert 'peaked' not in summary


def test_repair_retains_question_scope_and_identifies_bad_receipt():
    class RepairModel(FakeModel):
        writer_turn = 0
        repair_payload = None
        def generate(self, system, payload, **kwargs):
            result = super().generate(system, payload, **kwargs)
            if 'You are Writer.' in system:
                self.writer_turn += 1
                if self.writer_turn <= 2:
                    claim = next(r for r in payload['evidence'] if r['kind'] == 'claim')
                    fact = next(r for r in payload['evidence'] if r['kind'] == 'financial')
                    result['receipts'] = [{'claim_id': claim['id'], 'outcome_ids': [fact['id']],
                        'assessment': 'supported', 'explanation': 'Revenue verifies spending.'}]
                else:
                    self.repair_payload = payload
            return result
    model = RepairModel()
    result = Investigator(FakeSources(), model).run('Compare cash capital spending with GM', SCOPE)
    assert result['investigation']['status'] == 'complete'
    assert model.repair_payload['scope'] == SCOPE
    assert model.repair_payload['question'] == 'Compare cash capital spending with GM'
    assert any('Allowed outcome IDs: []' in e for e in model.repair_payload['validation_errors'])

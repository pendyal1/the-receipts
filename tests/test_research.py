import json
import threading
import time

import pytest
from receipts.research import Investigator, Scope, validate_report
from receipts.model import ModelError
from receipts.sources import SourceError

SCOPE = {'tickers': ['TSLA', 'GM'], 'start': '2020-01-01', 'as_of': '2023-03-01', 'through': '2025-03-01'}


class FakeSources:
    def resolve(self, ticker):
        return {'ticker': ticker, 'name': ticker, 'cik': 1}
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


@pytest.mark.parametrize('excerpt', [
    'We expect to recognize approximately 45 % of this revenue over the next 12 months and the remainder thereafter.',
    'We expect the macroeconomic uncertainty and the challenging market environment will extend into 2023. 2022 vs. 2021 2022 revenue was $63.1 billion, down $16.0 billion, or 20%, from 2021.',
    'We expect cash flows from operations to be sufficient to fund capital expenditures.',
])
def test_accounting_recognition_risk_and_liquidity_are_not_revenue_forecasts(excerpt):
    from receipts.research import claim_test_candidates
    evidence={'Eclaim': {'kind':'claim', 'phase':'known_then', 'ticker':'MSFT', 'filed':'2023-02-01', 'excerpt':excerpt}}
    for metric in ('revenue','capex','operating_cash_flow'):
        evidence['E'+metric]={'kind':'financial','ticker':'MSFT','metric':metric,'period_end':'2023-12-31'}
    candidate=claim_test_candidates(evidence)['Eclaim']
    assert candidate['metric'] is None
    assert candidate['allowed_outcome_ids']==[]


def test_unknown_ticker_gap_can_support_a_not_found_explanation():
    evidence={'Egap':{'kind':'source_gap','error':'ZZZZX was not found in the SEC ticker directory.'},
              'Emacro':{'kind':'macro'}}
    raw={'verdict':'insufficient evidence','summary':'ZZZZX was not found in the SEC ticker directory [Egap].',
         'sections':[{'title':'What was knowable then','text':'No company records were found; ZZZZX is not covered [Egap].'}]}
    assert not validate_report(raw,evidence,SCOPE)[1]


def test_incidental_word_project_does_not_hide_a_later_explicit_capex_forecast():
    from receipts.research import claim_test_candidates
    evidence={'Eclaim':{'kind':'claim','ticker':'TSLA','filed':'2022-10-24','excerpt':
        'The magnitude of purchase orders is difficult to accurately project. We currently expect capital expenditures between $6.00 to $8.00 billion in 2022.'},
        'Ecapex':{'kind':'financial','ticker':'TSLA','metric':'capex','period_end':'2022-12-31'}}
    assert claim_test_candidates(evidence)['Eclaim']['allowed_outcome_ids']==['Ecapex']


def test_capex_range_repeated_for_next_two_years_checks_every_attached_outcome():
    from receipts.research import quantitative_range_checks
    evidence={'Eclaim':{'kind':'claim','phase':'known_then','ticker':'TSLA','filed':'2022-10-24',
        'excerpt':'We expect capital expenditures between $6.00 to $8.00 billion in 2022 and each of the next two fiscal years.'}}
    for year,value in [(2022,7_158_000_000),(2023,8_898_000_000),(2024,11_339_000_000)]:
        evidence['E'+str(year)]={'kind':'financial','ticker':'TSLA','metric':'capex','period_end':f'{year}-12-31','value':value}
    checks=quantitative_range_checks(evidence)
    assert [c['relation'] for c in checks]==['within quoted range','above quoted range','above quoted range']
    raw={'verdict':'supported','summary':'Outlook [Eclaim]','sections':[{'title':'Evidence','text':'Outcomes [E2022] [E2023] [E2024]'}],
         'receipts':[{'claim_id':'Eclaim','outcome_ids':['E2022','E2023','E2024'],'assessment':'supported','explanation':'Only 2022 was within the range.'}]}
    assert any('outside its quoted forecast range' in e for e in validate_report(raw,evidence)[1])


def test_unknown_company_is_verified_without_asking_the_model_to_guess():
    class MissingSources(FakeSources):
        def resolve(self, ticker):
            raise SourceError(f'{ticker} was not found in the SEC ticker directory.')
    result=Investigator(MissingSources(),FakeModel()).run('Investigate ZZZZX',dict(SCOPE,tickers=['ZZZZX']))
    assert result['investigation']['status']=='clarification'
    assert 'SEC ticker directory' in result['response']
    assert [t['name'] for t in result['tool_calls']]==['company_lookup']
    assert result['investigation']['evidence'][0]['kind']=='source_gap'


def test_single_company_peer_note_is_derived_from_scope_without_a_fake_citation():
    evidence={'Evalue':{'kind':'financial'}}
    raw={'verdict':'insufficient evidence','summary':'A value [Evalue].',
         'sections':[{'title':'The peer test','text':'There are no peers.'}]}
    report,errors=validate_report(raw,evidence,dict(SCOPE,tickers=['AAPL']))
    assert not errors
    assert report['sections'][0]['text']=='Only AAPL was selected. Add a peer company to compare results.'


def test_source_gap_can_explain_absent_annual_observations():
    raw={'verdict':'insufficient evidence','summary':'No annual USD revenue observation was available [Egap].',
         'sections':[{'title':'Cross-examination','text':'A source gap prevents verification [Egap].'}]}
    assert not validate_report(raw,{'Egap':{'kind':'source_gap'}})[1]


def test_no_specific_outlook_was_retrieved_is_a_valid_gap_explanation():
    raw={'verdict':'insufficient evidence','summary':'No specific management outlook passages were retrieved [Egap].',
         'sections':[{'title':'Evidence','text':'An unprovided management statement cannot be tested [Egap].'}]}
    assert not validate_report(raw,{'Egap':{'kind':'source_gap'}})[1]
    raw['summary']='Ford capex metrics remain unpopulated under supported tags, creating a disclosure gap [Egap].'
    assert not validate_report(raw,{'Egap':{'kind':'source_gap'}})[1]
    raw['summary']='Neither company provided supported annual capex metrics for comparison [Egap].'
    assert not validate_report(raw,{'Egap':{'kind':'source_gap'}})[1]


def test_not_testable_gap_is_an_explanation_not_a_financial_outcome():
    evidence={'Ec':{'kind':'claim','phase':'known_then','ticker':'AMZN'},'Egap':{'kind':'source_gap'}}
    raw={'verdict':'insufficient evidence','summary':'No matching outcome is available [Egap].',
         'sections':[{'title':'Evidence','text':'Outlook [Ec] cannot be tested [Egap].'}],
         'receipts':[{'claim_id':'Ec','assessment':'not testable','outcome_ids':['Egap'],'explanation':'Spending is missing.'}]}
    report,errors=validate_report(raw,evidence)
    assert not errors
    assert report['receipts'][0]['outcome_ids']==[]
    assert '[Egap]' in report['receipts'][0]['explanation']
    raw['receipts'][0]['assessment']='supported'
    assert any('financial observations' in e for e in validate_report(raw,evidence)[1])


@pytest.mark.parametrize('field', ['explanation','limits'])
def test_visible_explanations_and_limits_cannot_invent_references(field):
    evidence={'Ec':{'kind':'claim','phase':'known_then','ticker':'TSLA'}}
    raw={'verdict':'insufficient evidence','summary':'Claim [Ec].',
         'sections':[{'title':'Evidence','text':'Outlook [Ec].'}],
         'receipts':[{'claim_id':'Ec','outcome_ids':[],'assessment':'not testable','explanation':'No data.'}]}
    if field=='limits':raw['limits']=['Unsupported [Efabricated].']
    else:raw['receipts'][0]['explanation']='Unsupported [Efabricated].'
    assert 'Unknown or unavailable evidence citation.' in validate_report(raw,evidence)[1]


def test_explicit_forecast_year_does_not_accept_a_different_year_outcome():
    from receipts.research import claim_test_candidates
    evidence={'Ec':{'kind':'claim','ticker':'TSLA','filed':'2023-01-31',
                    'excerpt':'We expect capital expenditures between $6 and $8 billion in 2023.'}}
    for year in (2023,2024):
        evidence['E'+str(year)]={'kind':'financial','ticker':'TSLA','metric':'capex','period_end':f'{year}-12-31'}
    assert claim_test_candidates(evidence)['Ec']['allowed_outcome_ids']==['E2023']


@pytest.mark.parametrize('excerpt,metric',[
    ('We expect data center revenue to grow in 2024.','revenue'),
    ('We expect international sales to grow in 2024.','revenue'),
    ('We expect operating income margins to expand in 2024.','operating_income'),
    ('We anticipate the changes will positively impact 2023 operating income by approximately $1 billion.','operating_income'),
])
def test_component_forecasts_cannot_be_tested_by_entity_wide_totals(excerpt,metric):
    from receipts.research import claim_test_candidates
    evidence={'Ec':{'kind':'claim','ticker':'TSLA','filed':'2023-01-31','excerpt':excerpt},
              'Ef':{'kind':'financial','ticker':'TSLA','metric':metric,'period_end':'2024-12-31'}}
    assert claim_test_candidates(evidence)['Ec']['allowed_outcome_ids']==[]


def test_writer_schema_stays_small_for_large_financial_ledgers():
    from receipts.research import writer_schema
    schema=writer_schema(['Ec'],['Ef'+str(i) for i in range(500)])
    outcome=schema['properties']['receipts']['items']['properties']['outcome_ids']
    assert 'enum' not in outcome['items']
    assert 'financial evidence ID only' in outcome['items']['description']
    assert len(json.dumps(schema))<2500


@pytest.mark.parametrize('failure',[SourceError('Provider unavailable'),ValueError('bad date'),KeyError('facts'),TypeError('bad body')])
def test_source_outage_or_malformed_provider_data_becomes_traceable_gap(failure):
    from receipts.research import Ledger
    class Broken(FakeSources):
        def financials(self,*args):raise failure
    ledger=Ledger()
    result=Investigator(Broken(),FakeModel()).tool(ledger,'Financials','financials_then','TSLA',Scope.model_validate(SCOPE))
    assert len(result)==1 and result[0]['kind']=='source_gap'
    assert result[0]['phase']=='coverage_gap'
    assert ledger.traces[0]['agent']=='Financials'
    assert all(r['kind']!='financial' for r in ledger.evidence.values())


def test_failed_writer_keeps_collected_evidence_without_publishing_a_report():
    class BrokenWriter(FakeModel):
        def generate(self,system,payload,**kwargs):
            if 'You are Writer.' in system:raise ModelError('Model request timed out.')
            return super().generate(system,payload,**kwargs)
    result=Investigator(FakeSources(),BrokenWriter()).run('Compare',SCOPE)
    assert result['investigation']['status']=='unavailable'
    assert result['investigation']['report'] is None
    assert any(r['kind']=='financial' for r in result['investigation']['evidence'])
    assert 'timed out' in result['response']


def test_unrepairable_fabrication_is_withheld_after_one_repair():
    class Fabricating(FakeModel):
        writer_calls=0
        def generate(self,system,payload,**kwargs):
            result=super().generate(system,payload,**kwargs)
            if 'You are Writer.' in system:
                self.writer_calls+=1
                result['summary']='Invented result [Efabricated].'
            return result
    model=Fabricating();result=Investigator(FakeSources(),model).run('Compare',SCOPE)
    assert result['investigation']['status']=='unavailable'
    assert result['investigation']['report'] is None
    assert model.writer_calls==3  # draft, evidence edit, one repair
    assert sum(t['name']=='repair_citations' for t in result['tool_calls'])==1
    assert 'Efabricated' not in result['response']


def test_expired_budget_stops_before_another_model_call():
    from receipts.research import Ledger
    class MustNotRun:
        def generate(self,*args,**kwargs):raise AssertionError('Called after deadline')
    with pytest.raises(ModelError,match='research budget'):
        Investigator(FakeSources(),MustNotRun()).model_call(Ledger(),'Lead','plan','',{},time.monotonic()-1)


def test_unscoped_question_cannot_use_dates_invented_by_planner():
    class GuessingPlanner(FakeModel):
        def generate(self,system,payload,**kwargs):
            if 'You are Lead.' in system:return {'clarification':'','scope':SCOPE,'tasks':{}}
            return super().generate(system,payload,**kwargs)
    result=Investigator(FakeSources(),GuessingPlanner()).run('Compare Tesla and GM revenue from 2020 through 2024.')
    assert result['investigation']['status']=='clarification'
    assert result['investigation']['evidence']==[]
    assert [t['name'] for t in result['tool_calls']]==['plan']


@pytest.mark.parametrize('question',[
    'Start January 1, 2020; use a historical knowledge date of March 1, 2023 and outcomes through March 1, 2025.',
    'History begins 2020-01-01, knowledge cutoff 2023-03-01, outcomes filed through 2025-03-01.',
    'From 2020, as of 2023, through 2025.',
])
def test_explicit_date_roles_accept_supported_api_phrasings(question):
    from receipts.research import explicit_date_roles
    assert explicit_date_roles(question)


def test_mixed_peer_profit_directions_cannot_be_called_uniform_expansion():
    from receipts.research import validate_peer_directions
    evidence={}
    for ticker,values in [('TSLA',(14_997,7_091)),('GM',(10_127,6_008)),('F',(4_347,5_879))]:
        for year,value in zip((2023,2024),values):
            evidence[ticker+str(year)]={'kind':'financial','ticker':ticker,'metric':'net_income',
                'period_end':f'{year}-12-31','filed':f'{year+1}-02-01','value':value}
    scope=dict(SCOPE,tickers=['TSLA','GM','F'])
    bad='Revenue growth and net income expansion across peers demonstrate parallel top-line scaling.'
    assert validate_peer_directions(bad,evidence,scope)
    assert validate_peer_directions('Entity-wide revenue and net income growth at GM and Ford do not verify capex.',evidence,scope)
    assert not validate_peer_directions('Profit directions diverged: Tesla and GM declined while Ford increased.',evidence,scope)
    assert not validate_peer_directions('Net income growth across peers between 2020 and 2024 requires a separate historical comparison.',evidence,scope)


def test_empty_company_coverage_has_a_sourced_explicit_fallback():
    from receipts.research import coverage_summary
    evidence={'Eg1':{'kind':'source_gap','phase':'known_then','ticker':'TSM'},
              'Eg2':{'kind':'source_gap','phase':'later_results','ticker':'TSM'},
              'Em':{'kind':'macro','phase':'hindsight_context'}}
    scope=dict(SCOPE,tickers=['TSM'])
    report,errors=validate_report(coverage_summary(evidence,scope),evidence,scope)
    assert not errors
    assert report['verdict']=='insufficient evidence'
    assert report['receipts']==[]
    assert 'deterministic' in report['limits'][0]
    assert '[Em]' not in json.dumps(report)


def test_empty_company_evidence_does_not_publish_a_fabricated_ai_draft():
    class NoCompanyData(FakeSources):
        def financials(self,*args):return []
        def passages(self,*args,**kwargs):return []
    class BadWriter(FakeModel):
        def generate(self,system,payload,**kwargs):
            if 'You are Writer.' in system:
                return {'title':'Bad draft','verdict':'supported','summary':'Invented [Efabricated]',
                        'sections':[{'title':'Evidence','text':'Invented [Efabricated]'}],'receipts':[],'limits':[]}
            return super().generate(system,payload,**kwargs)
    result=Investigator(NoCompanyData(),BadWriter()).run('Compare',dict(SCOPE,tickers=['TSM']))
    inv=result['investigation']
    assert inv['status']=='complete' and inv['report_kind']=='coverage_summary'
    assert inv['report']['verdict']=='insufficient evidence'
    assert 'Efabricated' not in result['response']
    assert any(t['name']=='finalize_coverage_summary' for t in result['tool_calls'])


@pytest.mark.parametrize('note',[
    'Intent cannot be proven, but the annual revenue comparison will be researched.',
    'Unsupported operational metrics cannot be established, but the annual revenue comparison is investigated.',
])
def test_planner_limitation_announcement_does_not_stop_supported_research(note):
    class ProgressNote(FakeModel):
        def generate(self,system,payload,**kwargs):
            result=super().generate(system,payload,**kwargs)
            if 'You are Lead.' in system:
                result.update(clarification=note,
                              tasks={a:'Compare the supported annual financials' for a in ('Claims','Financials','Peers','Context')})
            return result
    result=Investigator(FakeSources(),ProgressNote()).run('Compare annual revenue and explain whether intent is provable.',SCOPE)
    assert result['investigation']['status']=='complete'
    assert any(t['name']=='continue_supported_research' for t in result['tool_calls'])

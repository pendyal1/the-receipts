import json
import time

import pytest

from receipts.model import Gemini, ModelError, StructuredOutputError
from receipts.research import Investigator, Ledger


def test_malformed_json_has_retryable_error_without_exposing_output(monkeypatch):
    class Response:
        status_code = 200
        def json(self):
            return {'candidates': [{'content': {'parts': [{'text': '{"private":'}]}}]}
    monkeypatch.setattr('receipts.model.requests.post', lambda *a, **k: Response())
    monkeypatch.setattr(Gemini, 'token', lambda self: 'test-token')
    with pytest.raises(StructuredOutputError, match='incomplete structured output'):
        Gemini().generate('system', {'question': 'test'})


@pytest.mark.parametrize('failures, expected_calls', [(1, 2), (2, 2)])
def test_structured_output_retry_is_bounded_and_traced(failures, expected_calls):
    class Flaky:
        calls = 0
        def generate(self, *args, **kwargs):
            self.calls += 1
            if self.calls <= failures:
                raise StructuredOutputError('Malformed answer')
            return {'clarification': 'Which company and dates?'}
    model = Flaky()
    investigator = Investigator(None, model)
    ledger = Ledger()
    if failures == 1:
        assert investigator.model_call(ledger, 'Lead', 'plan', '', {}, time.monotonic()+10)['clarification']
    else:
        with pytest.raises(StructuredOutputError):
            investigator.model_call(ledger, 'Lead', 'plan', '', {}, time.monotonic()+10)
    assert model.calls == expected_calls
    assert len(ledger.traces) == 2
    assert json.loads(ledger.traces[0]['result']) == {'error': 'Malformed answer'}


def test_access_errors_are_not_retried():
    class Denied:
        calls = 0
        def generate(self, *args, **kwargs):
            self.calls += 1
            raise ModelError('No access')
    model = Denied()
    with pytest.raises(ModelError, match='No access'):
        Investigator(None, model).model_call(Ledger(), 'Lead', 'plan', '', {}, time.monotonic()+10)
    assert model.calls == 1

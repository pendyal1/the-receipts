import json
import sys
import time
from pathlib import Path
from receipts.model import Gemini
from receipts.sources import Sources
from receipts.research import Investigator

CASES = [
    ('automakers', ['TSLA', 'GM', 'F'], "Did Tesla's growth expectations hold up after 2022? Cross-examine the evidence and compare annual revenue and profitability with GM and Ford."),
    ('chips', ['NVDA', 'AMD', 'INTC'], 'As of March 1, 2023, what did NVIDIA expect, and how did annual revenue and operating income subsequently compare with AMD and Intel through March 1, 2025?'),
    ('cloud', ['MSFT', 'AMZN', 'GOOGL'], 'Compare management growth and investment expectations with later annual revenue and capital expenditures for Microsoft, Amazon and Alphabet. Which claims can the data actually test?'),
]

if __name__ == '__main__':
    selected = CASES if len(sys.argv) < 2 else [CASES[int(sys.argv[1])]]
    for slug, tickers, question in selected:
        scope = {'tickers': tickers, 'start': '2020-01-01', 'as_of': '2023-03-01', 'through': '2025-03-01'}
        prompt = f'{question}\nResearch scope: {json.dumps(scope)}'
        model = Gemini()
        start = time.monotonic()
        result = Investigator(Sources(), model).run(question, scope)
        output = {'question': question, 'scope': scope, 'model': 'gemini-3.5-flash-lite',
                  'elapsed_seconds': round(time.monotonic() - start, 2), 'agent': result}
        try:
            output['baseline_no_tools_no_system'] = model.generate(None, prompt, json_mode=False)
        except Exception as exc:
            output['baseline_error'] = str(exc)
        path = Path('evaluations') / f'{slug}.json'
        path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        print(json.dumps({'case': slug, 'status': result['investigation']['status'],
                          'seconds': output['elapsed_seconds'], 'calls': len(result['tool_calls']),
                          'evidence': len(result['investigation']['evidence']),
                          'limits': result['investigation']['limits'], 'answer': result['response'][:1000]}), flush=True)

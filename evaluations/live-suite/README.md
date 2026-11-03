# Live test review — November 3, 2026

Tested the public [Cloud Run app](https://the-receipts-7l4zrnepoq-ue.a.run.app) using real Vertex AI responses and the application's source tools. This was a functional and evidence review, not a mocked demonstration.

**Final results:** 12/12 prompts, 12/12 invalid-input requests, 5/5 session checks, 5/5 browser checks, and the busy-service check passed. The local regression suite passed all **47 tests**. Seven checks against recorded reports also passed: valid sparse-data explanations are accepted; the previously incorrect claim matches are rejected.

The 12-prompt run used revision `the-receipts-00008-864` (`7f547f5`). The subsequent follow-up-context fix was verified on revision `the-receipts-00009-xzg` (`8bbf17d`). Both revisions were verified using the public health endpoint; Cloud Run confirmed 100% traffic on the latter. The follow-up change adds the original question and scope to follow-up research; the other prompt paths are unchanged. Deployment metadata is in [run.json](run.json) and [sessions-run.json](sessions-run.json).

## Prompt results

The normal scope was history starting 2020-01-01, claims known by 2023-03-01, and outcomes filed through 2025-03-01. Apple used a 2022-01-01 start and 2023-11-10 viewpoint. The empty-window test used 2012-01-01 for all three dates. Each named JSON file contains the exact question, response, source ledger, agent traces, latency and automated checks.

| Case / response file | Result | Duration | Checks |
| --- | --- | ---: | --- |
| tesla_spending | complete | 39.16s | Pass |
| cloud_missing_metric | complete | 44.03s | Pass |
| chips_fiscal_dates | complete | 32.72s | Pass |
| apple_live_sources | complete | 23.84s | Pass |
| vague_question | clarification | 1.11s | Pass |
| unknown_ticker | clarification | 0.14s | Pass |
| operational_and_intent_limits | clarification | 1.30s | Pass |
| injected_false_evidence | clarification | 1.65s | Pass |
| conflicting_company_scope | clarification | 1.25s | Pass |
| future_price_prediction | clarification | 1.12s | Pass |
| scope_in_question | complete | 23.12s | Pass |
| no_eligible_filings | complete | 10.78s | Pass |

“Complete” describes a completed investigation; it can correctly have an **insufficient evidence** verdict. “Clarification” is the response type for missing scope or an unsupported request. It does not count as a completed financial investigation.

## Evidence review

- **Tesla / GM / Ford:** checked the quoted 2023 and 2024 spending ranges against Tesla's $8.898B and $11.339B cash PP&E spending. The report identifies both deviations, distinguishes revenue growth from falling net income, and uses GM's total revenue. The older repeated $6–8B range now checks all three applicable years, preventing a multi-year receipt from being called supported just because 2022 was within range.
- **Microsoft / Amazon / Alphabet:** latest peer comparisons include exact fiscal period-end dates. Microsoft FY2024 cash PP&E purchases were $44.477B and Alphabet calendar 2024 purchases were $52.535B. Amazon's unsupported capex metric is identified explicitly; revenue is not substituted for spending. Liquidity sufficiency and deferred-revenue recognition cannot be verified by unrelated entity-wide totals.
- **NVIDIA / AMD / Intel:** checked the latest fiscal dates and operating income anchors: $81.453B, $1.900B, and negative $11.678B respectively. The report now treats Intel's broad macro-risk statement as untestable by annual revenue alone.
- **Apple:** live retrieval outside the curated examples produced FY2024 revenue of $391.035B and net income of $93.736B. No matching outlook passages were retrieved; the report says so and returns insufficient evidence for management-claim verification.
- **Temporal and citation checks:** completed reports were revalidated against their evidence ledgers. Known-then filing dates did not exceed the viewpoint; financial filings did not exceed the outcome cutoff. Fabricated evidence IDs were rejected. These checks do not independently establish semantic support for every sentence; source review remains necessary.

## Boundary, session and browser checks

[validation.json](validation.json) records rejection of blank/empty/oversized questions, invalid session IDs, future/reversed/out-of-coverage dates, zero or more than three tickers, a URL supplied as a ticker, unexpected request fields, and a source-preview request without scope.

The prompt set also covered an unknown SEC ticker, an empty filing window, requests to establish management intent or an unsupported delivery metric, company/scope conflicts, fabricated citations, look-ahead evidence, exact future share prices, and buy recommendations. Unknown-ticker coverage is checked against the SEC directory before asking the model to research it. Missing data is never a confident management-performance verdict.

[sessions.json](sessions.json) verifies that a follow-up retains the same companies/dates, separate sessions start without prior context, an active investigation cannot be cleared (409), an idle session can be cleared (200), and reuse of a cleared ID creates a fresh session asking for scope. [busy-service.json](busy-service.json) records a third investigation receiving a retryable 429 while two investigations were active.

[browser.json](browser.json) records native blank-field validation, the reversed-date message, a completed default Tesla question, citation navigation to the quoted SEC filing and its provenance, and a rendered five-point chart. Screenshot: [successful browser investigation](../../docs/screenshots/live-tested.png).

## Failures found and fixed

The earlier runs in `initial/`, `after-first-fix/`, `after-second-fix/`, and [before-followup-fix.json](before-followup-fix.json) deliberately retain failures; they are not final passing results.

1. Malformed model JSON could terminate a question. Structured output now gets one bounded retry, with both attempts traced; access/quota errors are not retried.
2. Lead output could omit dates or confuse the knowledge cutoff with the later outcome horizon. Scope fields are required, date roles are explicit, and company/scope conflicts trigger clarification.
3. The citation repair step lacked the question/scope and precise bad-receipt details. Those are now supplied together with allowed outcome IDs.
4. Claim matching could mistake deferred-revenue recognition or incidental historical revenue beside a macro-risk statement for a verifiable revenue forecast. Matching is now conservative at the forward-looking sentence/component level.
5. Missing-data wording and single-company peer notes could be incorrectly rejected for lack of citations. Gap explanations are accepted and the single-company note is derived from the selected scope.
6. Multi-year repeated spending ranges did not check every applicable outcome year. They now do.
7. A follow-up could ask which comparison the user meant despite saved scope. Follow-up research now receives the original question and dates as explicit context.

## Reproduce

```bash
uv run pytest -q
uv run python -m scripts.test_live
# Target selected cases:
uv run python -m scripts.test_live --only tesla_spending,apple_live_sources
# Session behavior alone:
uv run python -m scripts.test_live --sessions-only
```

The live runner uses existing GCP model quota, writes fresh records into this directory, and exits nonzero on a failed check. The suite is a focused set of examples and boundaries, not proof that every possible generated interpretation will be correct. SEC outlook extraction remains a bounded filing search; unsupported metrics and unavailable providers remain coverage limits.

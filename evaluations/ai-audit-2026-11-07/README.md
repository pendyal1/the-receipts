# AI functional and stress audit — November 7, 2026

The actual Vertex AI pipeline works end to end. The final named suite passed **24/24 prompts**, **26/26 invalid-input requests**, and **5/5 session checks**. Local regression checks passed **94/94** (86 Python, 8 JavaScript). This is representative regression coverage, not proof that every future generated interpretation will be correct.

The 24-prompt matrix ran against revision `the-receipts-00024-kdg`, commit `adc0e05507a9fe0b8bf79a8439a336ca0e4b0850`. The subsequent load fix changed filing extraction and HTTP concurrency, not the research prompts or answer logic. Its records are in [load-final/run.json](load-final/run.json); final deployment verification is in [deployed-version.json](deployed-version.json). Browser exports and screenshots were captured after that deployment.

## Real prompts and results

All entries below used the public service and real Vertex responses. A `complete` investigation may correctly return insufficient evidence. A `clarification` response can explain missing scope or a wholly unsupported request; it is not a completed financial investigation. Completed named cases took 9.34–86.24 seconds (median 31.62s).

| Case | Outcome | Time | Check | Exact response, evidence and traces |
| --- | --- | ---: | --- | --- |
| apple_live_sources | complete | 16.66s | Pass | [record](final/apple_live_sources.json) |
| bank_metrics | complete | 86.24s | Pass | [record](extended-final/bank_metrics.json) |
| chips_fiscal_dates | complete | 26.15s | Pass | [record](final/chips_fiscal_dates.json) |
| cloud_missing_metric | complete | 47.33s | Pass | [record](final/cloud_missing_metric.json) |
| conflicting_company_scope | clarification | 1.00s | Pass | [record](final/conflicting_company_scope.json) |
| consumer_peers | complete | 30.71s | Pass | [record](extended-final/consumer_peers.json) |
| correct_false_premise | complete | 38.78s | Pass | [record](extended-final/correct_false_premise.json) |
| date_scope_conflict | clarification | 1.33s | Pass | [record](extended-final/date_scope_conflict.json) |
| foreign_filer | complete | 19.27s | Pass | [record](extended-final/foreign_filer.json) |
| future_price_prediction | clarification | 1.23s | Pass | [record](final/future_price_prediction.json) |
| industry_scope | complete | 35.56s | Pass | [record](extended-final/industry_scope.json) |
| injected_false_evidence | clarification | 1.70s | Pass | [record](final/injected_false_evidence.json) |
| latest_fiscal_year | complete | 42.17s | Pass | [record](extended-final/latest_fiscal_year.json) |
| missing_viewpoint | clarification | 1.30s | Pass | [record](extended-final/missing_viewpoint.json) |
| mixed_supported_unsupported | complete | 49.25s | Pass | [record](extended-final/mixed_supported_unsupported.json) |
| no_eligible_filings | complete | 9.34s | Pass | [record](final/no_eligible_filings.json) |
| off_topic | clarification | 1.32s | Pass | [record](extended-final/off_topic.json) |
| operational_and_intent_limits | clarification | 1.47s | Pass | [record](final/operational_and_intent_limits.json) |
| punctuated_share_class | complete | 24.90s | Pass | [record](extended-final/punctuated_share_class.json) |
| quarterly_only | complete | 31.62s | Pass | [record](extended-final/quarterly_only.json) |
| scope_in_question | complete | 22.71s | Pass | [record](final/scope_in_question.json) |
| tesla_spending | complete | 32.95s | Pass | [record](final/tesla_spending.json) |
| unknown_ticker | clarification | 1.00s | Pass | [record](final/unknown_ticker.json) |
| vague_question | clarification | 1.23s | Pass | [record](final/vague_question.json) |

The questions cover the three featured industries, Apple, Coca-Cola/PepsiCo, JPMorgan/Bank of America, a foreign SEC filer, newer fiscal years through November 2026, a punctuated share class, false premises, unsupported quarterly/EPS questions, operational metrics, management intent, future prices, investment recommendations, hostile citation instructions, scope conflicts, missing dates and an empty filing window.

## Evidence and orchestration checks

- **15 numerical anchors** matched SEC/XBRL source records: [source checks](source-anchor-audit.json).
- **10 quoted outlook excerpts** were found in normalized archived filing text and their source hashes matched: [quote checks](quote-audit.json).
- **33 archived filings** produced exactly identical normalized text after replacing DOM construction with streaming extraction. Local extraction time fell from 8.988s to 2.927s for that corpus: [parser regressions](filing-parser-regressions.json). This measures parsing, not total investigation speed.
- Reports were revalidated for real citation IDs, correct entity/metric links, explicit forecast years, historical filing cutoffs, source-gap treatment, and selected broad peer-direction assertions. These are bounded checks; they do not independently prove semantic entailment of every sentence.
- Local tests exercise parallel fresh-context Researchers, bounded gap filling, duplicate-tool guards, malformed model output, a single citation repair, expired budgets, provider/auth errors, source outages, malformed source records, safe sparse-data summaries and Project 1 response fields including `tool_calls` and `agent`.
- [Session checks](final/sessions.json) passed follow-up context, separate-session isolation, active-clear rejection, idle clearing and fresh context after clearing.

## Browser and load verification

The real browser passed blank/company-only input, four-company rejection, impossible-date validation, a busy-service response that preserved the question, a complete peer investigation, exports, citation navigation, and time travel. Hiding later results reduced the revenue chart from 15 to 9 points; every retained filing was known by March 1, 2023.

A complete browser investigation produced **129 source records and 30 research-log entries**: [export](browser-tesla.json), [screenshot](browser-final.png). Its citation opened the exact January 31, 2023 Tesla 10-K outlook with its filing URL, retrieval timestamp and SHA-256: [source screenshot](browser-source.png). A separate quarterly question displayed the capability limit in the main answer, instead of an unrelated spending headline: [export](browser-quarterly.json), [screenshot](browser-quarterly.png). Both exported reports passed reference validation.

During two simultaneous investigations, the homepage, health endpoint, application script and company directory returned HTTP 200 in **0.18–0.42 seconds**: [page checks](load-final/page-load.json). The native browser also loaded successfully with custom fonts ready: [screenshot](load-final/browser-during-research.png). HTTP concurrency is now 32, while AI investigations remain capped at two and Cloud Run remains capped at one instance.

A separate five-request burst accepted two short requests and returned three retryable 429 responses; the health endpoint remained responsive: [admission check](concurrency-final.json). That check preceded the HTTP concurrency increase; application AI admission limits did not change.

## Failures found and fixed

1. Valid missing-data wording could fail the citation checker. Coverage language is recognized more accurately, and citation repair receives the precise offending text.
2. A not-testable receipt could incorrectly attach a source-gap ID as a financial outcome. Gap references are kept as explanations, and all actual outcomes must be financial records.
3. Forecast matching could accept a different explicit year, entity-wide totals for segment targets, or totals for margins/incremental changes. Matching is now more conservative.
4. Citation IDs in claim explanations and limits were not checked. They are now checked alongside the displayed answer and report sections.
5. Unscoped questions could receive invented dates. The server now requires explicit date roles or an existing dated investigation.
6. A planner limitation/progress note could halt a supported mixed request despite a complete plan. Complete supported plans continue when no user decision is requested.
7. A broad peer-profit growth statement could contradict the annual figures. A narrow arithmetic gate now checks uniform latest-period assertions, with precise repair feedback.
8. Large outcome-ID enumerations exceeded the model provider's schema complexity budget. The schema stays compact; server-side ID checks remain authoritative. This behavior is consistent with [Google's structured-output limitations](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/control-generated-output).
9. With no company evidence, a malformed AI draft could turn an honest coverage limit into an unavailable response. A clearly labeled deterministic coverage summary can report the actual gaps without making a financial assessment.
10. The result screen could substitute a spending headline for another question. It now displays the validated question answer, while calculated annual numbers remain supporting evidence.
11. Opening the page during large investigations could display `Rate exceeded`, and page/health requests were observed taking about 16s. Filing extraction now avoids a full DOM, and the hosting HTTP allowance leaves room for page requests. [Original observation](page-load-issue-initial.json), [follow-up load results](load-final/run.json).

## Remaining limits and actual provider-rate event

One additional bank investigation during load testing hit a **real Vertex HTTP 429**. The app returned `unavailable`, retained the source ledger and published no unverified report: [failed provider call](load-final/bank_metrics.json). A later isolated retry completed successfully in **66.75s**: [recovery](provider-recovery/bank_metrics.json). This external quota/capacity limit remains; the service does not promise unlimited simultaneous AI research. One earlier health request also timed out during overlapping deployment/testing, then recovered: [observation](rollout-health-note.json).

Financial coverage remains selected annual US GAAP USD tags and a bounded filing search, not all metrics for every SEC filer. Quarterly EPS, IFRS/foreign forms, segments, operational targets, intent and causation may be unsupported. FRED revisions and adjusted historical prices remain hindsight context. Source outages and exhausted model budgets must return explicit limitations rather than invented findings. Inspect the cited primary record before relying on a generated interpretation.

Earlier folders intentionally retain failures. The final matrix is `final/` plus `extended-final/`; later hosting/browser/provider checks are identified separately above. [Machine-readable summary](summary.json).

## Reproduce

```sh
uv run pytest -q
node --test tests/company-directory.test.cjs
uv run python -m scripts.test_live --out evaluations/new-core-run
uv run python -m scripts.audit_ai --out evaluations/new-extended-run
```

Run the two live suites sequentially: each already uses two request workers, matching AI admission capacity. Live runs consume the existing GCP model quota.

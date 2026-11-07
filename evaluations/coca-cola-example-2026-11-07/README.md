# Coca-Cola featured example verification

Replaced the NVIDIA landing-page example with Coca-Cola and PepsiCo. The editable question asks whether Coca-Cola delivered on its 2023 capital-spending outlook, then compares annual revenue and net income for 2023–2024 with PepsiCo.

The exact new prompt completed against the deployed AI endpoint in 17.97 seconds, returning 88 evidence records. It compared the approximately $1.9 billion forecast with $1.852 billion in actual cash PP&E spending, included both companies’ annual revenue and net income, and acknowledged PepsiCo capital-spending coverage limits. All report citation IDs resolve to the returned evidence ledger. See `live-result.json` for the complete request and response.

Regression checks: 86 Python tests and 8 JavaScript tests passed.

Browser testing caught the acronym PP&E being interpreted as ticker E. The final example uses “capital spending”; the JavaScript regression suite now checks the exact featured prompt resolves to only KO and PEP.

Deployment verified at commit `ced3b970d10fb84471d2700fffe6944b3b6dd070`, Cloud Run revision `the-receipts-00027-588`; Cloud Build completed successfully. The live button loads the correct company logo and editable question. Submitting through the browser selects only KO and PEP and completes with 88 sources, a spending forecast versus outcome answer, and 25 research log entries. No browser console errors were recorded. `live-example.png` and `live-answer.png` show the live interface.

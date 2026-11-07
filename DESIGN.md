# The Receipts — Sage-inspired interface

Reference: [Sage on Site of Sites](https://www.siteofsites.co/websites/sage%C2%AE), linking to the [original Sage site by Fantik Studio](https://sage.fantik.studio/). Inspected November 7, 2026, at a 1280 × 720 desktop viewport. See [reference screenshot](docs/design/sage-reference.png).

## Observed reference

The live page uses a near-black full-screen canvas, a large white futuristic wordmark, an animated gray wireframe surface, a centered rounded “Enter App” control, compact peripheral controls, and monochrome details. The wireframe crosses behind the central content. Small outlined/dashed capsules introduce the wordmark. These layout descriptions come from inspected pixels; spacing and geometry are visual estimates, not extracted exact coordinates.

The original stylesheet (`https://sage.fantik.studio/assets/index-CDTW-d7f.css`) declares `NecroCosmic` for display type and `TTFirsNeueRegular` for body type. Its declared palette includes `#000`, `#fff`, and translucent white (`#fff6`, `#fffc`, `#ffffff40`, `#ffffff4d`, `#ffffff80`). A fresh Firecrawl branding capture confirmed the display/body pairing. Font metadata identifies the display face as Necosmic Personal Use (the CSS calls it NecroCosmic). TT Firs Neue requires appropriate web-use rights; the user selected free alternatives. The reference screenshot was captured and inspected through the browser. No Sage production font or artwork is shipped in this application.

## Adaptation for The Receipts

Keep the spatial composition and dark material; replace the entry button with a working company/question search. Create an original receipt icon, segmented wordmark treatment, and procedural wireframe. Use bright green for the search outline, action arrow, focus rings, evidence citations, selected controls and restrained highlights. The financial investigation remains the application's primary task.

| Role | Implementation |
| --- | --- |
| Background | `#080a09` |
| Panel | `#0c100d`, nearly opaque |
| Foreground | `#f0f2ec` |
| Secondary text | `#949b93` / lighter olive-gray on dark panels |
| Divider | `#30362f` |
| Accent / focus | `#bcfa77` |
| Display | Orbitron variable, locally hosted, SIL Open Font License |
| Body | Sora variable, locally hosted, SIL Open Font License |
| Technical labels | Sora, with tabular figures; no system font stack |

After the user chose free self-hosted alternatives to Sage's licensed fonts, Orbitron became the display/navigation face and Sora the only reading/control/chart face. No generic or system-font fallbacks are declared. Text stays hidden behind an SVG loader until the Font Loading API confirms both faces. Files and OFL licenses are in `static/fonts/`; sources are the official [Orbitron](https://github.com/google/fonts/tree/main/ofl/orbitron) and [Sora](https://github.com/google/fonts/tree/main/ofl/sora) directories.

## Components and behavior

- **Landing:** full viewport, large white wordmark, short introduction, centered search, three preset cases. The wireframe is original canvas geometry, not financial data. No stock photo or raster background is necessary.
- **Search:** a company name or ticker opens branded suggestions from the dated SEC directory, with keyboard selection, aliases, typo suggestions and share-class identity. Company logos also appear in the preset cases; unavailable logos use ticker initials. The main bar submits a full question directly. Company-only input offers question suggestions; a missing company is requested inline. Optional company, peer and date controls are beneath the bar, with the historical window visible before submission. Enter submits and Shift+Enter adds a line. Featured cases fill editable questions.
- **Navigation:** About, How to use, and Sources open one native dialog with switchable panels. Close button, Escape, backdrop dismissal and native focus containment are supported. External source links are explicit.
- **Research:** the setup panel closes when valid research starts. Progress appears on the landing screen. Duplicate submissions are disabled. Invalid fields and dates keep the panel open with an explanation.
- **Results:** collapse the landing into a dark research desk. Preserve real findings, financial cards, numbered citations, evidence ledger, research log, chart replay, exports, source-only previews and session reset. The chart palette and labels are adapted for the dark background.
- **Motion:** restrained mesh movement and pointer parallax. Respect reduced-motion preferences, allow manual pause, and stop animation while the page is hidden.
- **Responsive:** desktop composition adapts to a narrow single-column view; long dialogs scroll, financial cards stack, dates stack, and primary interactive targets remain at least 44px. Mobile behavior is an adaptation, not an assertion about Sage's uninspected mobile design.

## Research lens refinement

The optional context panel uses a continuous chronology, small green nodes, flat underline fields, issuer-logo peer chips and thin rules. Dates use a custom Sora calendar and validated ISO text entries; they do not open a browser calendar. The search textarea has no inherited bottom margin, and its box is centered on the submit button. Navigation explicitly uses Orbitron. New controls retain the question-first workflow.

Logo lookup now covers any ticker in the SEC snapshot through the local `/company-logo/{ticker}` route. Public image hosts are used on demand and cached by SEC CIK; a missing image is represented as unavailable. This is broad retrieval capability, not a guarantee that every SEC filer has a published brand image. Logos identify current issuers and are not historical financial evidence.

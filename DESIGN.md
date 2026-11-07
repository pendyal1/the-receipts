# The Receipts — Sage-inspired interface

Reference: [Sage on Site of Sites](https://www.siteofsites.co/websites/sage%C2%AE), linking to the [original Sage site by Fantik Studio](https://sage.fantik.studio/). Inspected November 7, 2026, at a 1280 × 720 desktop viewport. See [reference screenshot](docs/design/sage-reference.png).

## Observed reference

The live page uses a near-black full-screen canvas, a large white futuristic wordmark, an animated gray wireframe surface, a centered rounded “Enter App” control, compact peripheral controls, and monochrome details. The wireframe crosses behind the central content. Small outlined/dashed capsules introduce the wordmark. These layout descriptions come from inspected pixels; spacing and geometry are visual estimates, not extracted exact coordinates.

The original stylesheet (`https://sage.fantik.studio/assets/index-CDTW-d7f.css`) declares `NecroCosmic` for display type and `TTFirsNeueRegular` for body type. Its declared palette includes `#000`, `#fff`, and translucent white (`#fff6`, `#fffc`, `#ffffff40`, `#ffffff4d`, `#ffffff80`). Firecrawl supplied page text and metadata; branding fields and screenshots were not returned by the available connector. The screenshot was captured and inspected through the browser instead. No Sage production font or artwork is shipped in this application.

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
| Display | Michroma, locally hosted, SIL Open Font License |
| Body | Manrope variable, locally hosted, SIL Open Font License |
| Technical labels | system monospace |

Michroma and Manrope are implementation choices approximating the reference's futuristic/clean pairing. Files and licenses are in `static/fonts/`; sources are the official [Google Fonts Michroma directory](https://github.com/google/fonts/tree/main/ofl/michroma) and [Manrope directory](https://github.com/google/fonts/tree/main/ofl/manrope).

## Components and behavior

- **Landing:** full viewport, large white wordmark, short introduction, centered search, three preset cases. The wireframe is original canvas geometry, not financial data. No stock photo or raster background is necessary.
- **Search:** a company name, ticker or company-specific question opens a focused investigation dialog. Recognized companies and peers are prefilled; unfamiliar questions ask for a ticker. Questions remain editable. Research dates are visible before starting and adjustable in a disclosure.
- **Navigation:** About, How to use, and Sources open one native dialog with switchable panels. Close button, Escape, backdrop dismissal and native focus containment are supported. External source links are explicit.
- **Research:** the setup panel closes when valid research starts. Progress appears on the landing screen. Duplicate submissions are disabled. Invalid fields and dates keep the panel open with an explanation.
- **Results:** collapse the landing into a dark research desk. Preserve real findings, financial cards, numbered citations, evidence ledger, research log, chart replay, exports, source-only previews and session reset. The chart palette and labels are adapted for the dark background.
- **Motion:** restrained mesh movement and pointer parallax. Respect reduced-motion preferences, allow manual pause, and stop animation while the page is hidden.
- **Responsive:** desktop composition adapts to a narrow single-column view; long dialogs scroll, financial cards stack, dates stack, and primary interactive targets remain at least 44px. Mobile behavior is an adaptation, not an assertion about Sage's uninspected mobile design.

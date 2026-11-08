---
name: html-report-slides
description: Generate self-contained HTML reports, presentation slides, or full-text reading decks from Markdown, notes, or data. Use for HTML reports/slides, personal report reading, beginner-friendly finance explanations, charts, and final-action summaries without needing a .pptx file.
---

# HTML Report & Slides

Produce ONE self-contained `.html` file that opens in any browser with no build step.

## 1. Choose the purpose before shortening content

| Mode | Use when | Template |
| --- | --- | --- |
| **Reading deck** | The user wants to read, understand, study, or personally review a complete report | `templates/reading-slides.html` |
| **Presentation slides** | The user explicitly wants to present to other people or requests a short briefing | `templates/slides.html` |
| **Report page** | The user wants a single scrolling HTML report, page, or one-pager | `templates/report.html` |

When converting an existing multi-section report to slides, default to a **reading
deck** unless the user asks for a presentation. "Slides" does not automatically
mean "short bullets." Ask only if the purpose remains genuinely unclear.

Start from the matching template and adapt its CSS variables and navigation.
The templates contain placeholders, not real source data; replace them before
delivering a generated report.

## 2. Shared content rules

- Read the entire source, including final decisions, caveats, tables and debate
  rounds. Do not work only from the beginning or a truncated file preview.
- Use source facts only. Never invent prices, dates, holdings, forecasts, targets,
  numbers, quotations or outcomes. Use `[TBD: ...]` for genuinely missing facts.
- Preserve whether a value is reported, estimated, disputed or unverified. Do not
  silently reconcile inconsistent figures or present an assumption as a fact.
- Lead with the final conclusion or action. Keep intermediate recommendations
  distinguishable from the final approved decision.
- Educational explanations may define terms, but must be visibly separate from
  source content and must not add unsupported market claims or recommendations.
- Preserve source attribution, analysis date, generation date and relevant limits.
  Do not copy private report or portfolio data into the reusable skill/templates.

## 3. Reading decks: preserve the report, explain the meaning

**There is no 30-word limit in reading mode.** Do not replace full report sections
with presentation bullets. The user is reading, not presenting.

### Content and structure

- Begin with a short reading overview: final action, prerequisites, reduction or
  reassessment triggers, and where the complete decision can be found.
- Follow the source's team/chapter structure in the navigation.
- Reproduce full analyst reports, research/debate rounds and decision sections,
  including their tables, caveats, rationale and conditions.
- Split long debates by round or meaningful source subsection. Preserve every
  paragraph across the split pages; do not truncate or silently drop rebuttals.
- Condense only sections the user explicitly permits you to shorten. Label them
  **Condensed source summary**; preserve the stance, reasons, objections and
  relationship to the final decision.
- Keep the source text in a main reading column. Add a separately labeled
  **Plain-English guide** with the main point, vocabulary, uncertainties and
  implications for reading the final action.
- Explain for a beginner by default in finance reports, especially if the reader
  is technical but not a finance professional. Avoid unexplained jargon.
- Keep a visible final-action reminder while reading. A proposed Buy must not be
  confused with a later final Hold, or a condition with an already executed order.

### TradingAgents report layout

For a report with these sections, preserve this chapter structure:

1. **Analyst Team Reports**: every available analyst, with full content.
2. **Research Team Decision**: all available researchers and the Research Manager;
   preserve all debate rounds and the complete manager decision.
3. **Trading Team Plan**: the **full Trader content**, including reasoning,
   entry/add levels, stop, sizing, funding and constraints.
4. **Risk Management Team Decision**: every risk analyst. If the user requests
   shorter risk coverage, give each analyst one condensed reading page.
5. **Portfolio Manager Decision**: the **full final content**, including executive
   summary, thesis, funding/protection steps, upgrade/reduce conditions, data
   limits, price target or its absence, and time horizon.

Do not require all these roles in a different report; use the source's actual
structure. For TradingAgents, distinguish research ratings, Trader proposals and
the final Portfolio Manager action rather than assuming they agree.

Useful plain-English explanations include EPS/P/E and forecast dependence;
operating margin and leverage; FCF versus capex; SMA/EMA, RSI/MACD and ATR;
concentration; funding versus margin; starter/tranche sizing; stop/gap risk; and
conditional protection costs. Explain only relevant terms. For example, a
one-third tranche is not automatically one-third of the whole portfolio.

### Reading UX

- One active reading page, with chapter/role navigation, previous/next buttons,
  a page counter and linkable URL fragments.
- Left/right arrows change pages. Preserve normal vertical scrolling, Page
  Up/Down, text selection, copying and interaction with links or controls.
- Do not advance when the user clicks ordinary report text; this is not a stage
  presentation. Do not intercept editing keys or navigation while selecting text.
- Allow full text to scroll; never clip a long section to fit a 16:9 canvas.
- Use readable body text (about 16px or larger), generous line height, reasonable
  line lengths, wrapping and horizontally scrollable tables/charts.
- Keep the **Plain-English guide always visible side-by-side with the source
  text**, including iPad Mini and smaller screens. Do not collapse the entire
  guide or move it above/below the source at tablet/mobile breakpoints. Use
  responsive column widths, smaller spacing and wrapping on narrow screens.
  Keep the guide sticky with independent scrolling for long explanations; each
  individual explanation card may still be toggled. Preserve readable source
  text and expose both source and guide content for print.
- Keep a hamburger sitemap toggle visible in the reader toolbar on desktop and
  mobile. Desktop collapse must remove the navigation column and expand the
  reading area; the same button reopens it. Preserve the desktop choice between
  reading pages. At **1024px and below** (including iPad Mini landscape), start
  with the sitemap collapsed. Opening it must show a fixed overlay drawer over
  a dimmed backdrop, without shrinking the reading area. Provide a close button,
  close on backdrop click or Escape, and close after a chapter jump. Make the
  background reader inert while the drawer is open, trap keyboard focus inside
  the drawer and restore focus when it closes. Wider screens retain the
  collapsible in-layout sitemap.
- Synchronize `aria-expanded`, descriptive expand/collapse labels and the hidden
  panel's `inert` state. Move focus out of a panel before leaving it hidden; Escape
  closes it. Reset appropriately when switching between desktop and mobile.
- Keep keyboard focus visible; when jumping from navigation, focus the new
  heading. Closing the small-screen chapter panel must not strand hidden focus.
- Print all reading pages without truncation. A long reading page may span
  multiple printed pages; preserving content takes priority over one-page slides.

## 4. Charts and diagrams for understanding

Add useful visuals when the source supplies enough data. A reading chart
**supplements** full source content; it never replaces it.

- Prefer **inline SVG** for offline, self-contained charts and flowcharts.
- Use actual source values with units, labeled axes, readable labels and a
  caption beginning with **How to read**.
- Good choices: selected price observations, reported versus forecast EPS,
  proposed entry/add/stop reference levels, and a final-action prerequisite flow.
- Label forecasts distinctly from reported observations. Preserve source data
  warnings next to the visual, not only elsewhere in the report.
- Space dates by elapsed time. With sparse data, label the chart **Selected
  observations, not a complete daily series**; do not invent missing daily prices
  or treat connecting lines as observed intermediate data.
- Use a zero baseline for magnitude bars. If a line or reference-level chart
  uses a restricted axis, disclose it. Do not use misleading scales.
- A price-reference plot is not a time series. A prior high is not a price target.
  A stop reference is not a guaranteed fill or protection against overnight gaps.
- Do not invent allocation pies without complete holdings/weights, probability
  forecasts, targets, performance histories or guaranteed outcomes.
- A final-action flow must retain all applicable gates and alternatives. Make
  "not confirmed / wait" explicit when a prerequisite is missing.
- Every SVG needs an accessible name and description (`role="img"`,
  `aria-labelledby`, `<title>` and `<desc>`), including the important values.
- Use existing tools only. Do not download data, install a chart package or add
  a service merely to generate a visual. Ask before adding dependencies or
  external resources.

## 5. Presentation and report-page modes

- **Presentation only**: one idea per slide, a takeaway headline, roughly
  30 words of body and at most 5 bullets unless the user asks for more detail.
  Use a 16:9 viewport with keyboard/button navigation; no text clipping.
- **Report page**: executive summary first (3-5 bullets), followed by source
  sections ordered by importance, with charts/tables where useful.
- Numbers that matter can go in KPI cards, but cards must preserve units,
  forecast labels and source caveats.

## 6. Technical and visual requirements

- Deliver one HTML file with inline CSS and JavaScript, no build step.
- Default to no network dependencies, external fonts or local image assets.
  Use inline SVG. The older presentation/report templates include CDN examples:
  remove unused imports and do not retain them without user approval.
- If external code is explicitly approved, Chart.js or Mermaid can be used;
  disclose that the resulting file needs the network. Never silently add CDN
  fallbacks, automatic downloads or a bundled service.
- No frameworks, servers, background workers or new tooling are required.
- Font: `"Segoe UI", system-ui, sans-serif`. Keep palette variables `--bg`,
  `--fg`, `--muted`, `--accent`, `--card`. Use at most two accent colors.
- Default dark theme for reading/presentation decks, light for report pages.
  Use accessible contrast (at least 4.5:1 for normal text), semantic headings,
  labeled buttons, reduced-motion support and print styles.
- Treat Markdown/HTML source as untrusted content. Escape raw HTML or sanitize it
  using already available tools; do not execute scripts from the input report.
  Generated trusted navigation scripts are separate from source content.
- External HTTP(S) source links may open with `noopener noreferrer`; reject
  unsafe link schemes. Do not fetch linked pages without a request.

## 7. Quality checks and handoff

1. Verify every required role/chapter exists. For full-source sections, compare
   the rendered content against the input, including all research rounds,
   Trader and final-decision text. Only approved summaries may be shortened.
2. Trace every chart value to the source. Check units, date spacing, forecast
   styling, limits and that diagrams preserve the final-action conditions.
3. Check navigation, chapter jumps, URL fragments, focus, text selection and
   normal scrolling. All content must remain reachable at 1280x720, laptop and
   small-screen sizes.
4. Check script syntax, SVG validity and accessible labels. When an existing
   browser is available, inspect rendering and console errors. Do not install or
   start a browser service without approval; state an unverified visual check
   plainly rather than claiming it passed.
5. Remove all unused sample code and template placeholders from the generated
   output. Verify there are no unapproved external resources.
6. Tell the user the filename and how to read it: open in a browser, left/right
   arrows or buttons to change pages, scroll normally for full content.

## 8. Iteration and portability

Apply feedback as targeted edits. Adding charts or changing layout must not
silently remove full text or weaken qualifiers. Do not regenerate the source
analysis or change its final action during a visual conversion.

To use this skill with another agent, copy the **entire `html-report-slides`
folder**, including `SKILL.md` and `templates/`, into that agent's supported skill
directory. Keep the relative template paths intact. No example report, credentials,
portfolio snapshot, package installation or service is required.

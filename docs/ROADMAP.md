# A11yLens roadmap

This page is the maintained implementation plan based on the supplied six-week project roadmap. “Done” means the feature exists in the local project; it does not imply independent evaluation or Chrome Web Store approval.

## Week 1 — Extension foundation: done

- [x] Set up the Manifest V3 extension, popup, and background service worker.
- [x] Add on-demand active-tab messaging and session storage for recent scan results.
- [x] Show a helpful preview message when `popup.html` is opened as a local file.

## Week 2 — Accessibility scanning: done

- [x] Bundle axe-core locally and run WCAG A/AA checks after the user starts a scan.
- [x] Present violations separately from checks that need manual review.
- [x] Highlight affected elements and show a small sample of their HTML.

## Week 3 — Explanation API: done locally

- [x] Add a FastAPI endpoint with input limits and strict request fields.
- [x] Provide local WCAG guidance without a model key.
- [x] Add optional Groq explanations and code suggestions, with API keys kept in the backend environment.
- [x] Add provider error/retry guidance and document a safe local-key setup walkthrough. Groq behavior is documented from code but has not been tested with a provider key.

## Week 4 — WCAG retrieval: implemented; semantic mode optional

- [x] Build a linked summary corpus of WCAG 2.2 A/AA criteria from W3C WAI Understanding documents.
- [x] Map common axe rules directly to relevant criteria.
- [x] Add TF-IDF retrieval as the lightweight default fallback.
- [x] Add an optional local Sentence Transformers + FAISS retrieval path.
- [x] Keep the large embedding dependencies optional and document their separate installation path.

## Week 5 — Evaluation and interface polish: in progress

- [x] Add a local JSON export for scan summaries. The schema excludes page HTML and removes URL credentials, query parameters, and fragments.
- [x] Link findings to the related axe rule guidance when the source is a trusted Deque University HTTPS page.
- [x] Use neutral labels for manual-review impact, clarify summary count units, explain when one axe rule has both result types, and offer clearly labeled review guidance on manual-review cards.
- [x] Smoke-check local guidance for six axe rules and confirm one popup guidance request after starting the API. Record API results against axe 4.14.0's criterion tags. This is not a formal accuracy evaluation; Groq mode was not tested.
- [x] Add GitHub maintenance docs, a changelog, and issue templates.
- [x] Create a small, clearly labeled set of accessible and intentionally flawed local demo pages with a repeatable scan procedure and results template.
- [x] Document a repeatable keyboard and screen-reader review procedure in `evaluation/ASSISTIVE_TECH_TEMPLATE.md`; the manual checks themselves remain pending.
- [ ] Record scan coverage, retrieval agreement, and repair outcomes on a repeatable evaluation set without claiming automated conformance. Axe tags may be a reference baseline, not independent ground truth.
- [ ] Review keyboard navigation, screen-reader announcements, and popup layout using manual assistive-technology checks.
- [ ] Refine report naming and presentation based on evaluation feedback.

## Week 6 — Release preparation: started

- [ ] Choose a source license and confirm third-party notices.
- [x] Add branded extension icon assets and a Windows regeneration script.
- [ ] Capture final extension screenshots in a clean browser profile on a demo page, with no personal data visible.
- [x] Review current source permissions, local data flow, API-key handling, and axe-core notice generation against the repository code.
- [ ] Review the packaged release, store privacy declarations, and deployment risks after choosing a distribution and hosting model.
- [x] Draft a code-matched local-development privacy disclosure; publication review remains.
- [ ] Decide whether to keep the backend local-only or design a secured hosted service.
- [ ] Prepare Chrome Web Store materials if distribution is desired.

## Current release boundary

A11yLens is a local development project. Its automated scan is not a WCAG conformance verdict. The optional AI explanation can be enabled only by configuring a Groq API key; when enabled, the selected finding is sent to Groq by the backend. The source license and public deployment model are undecided.

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
- [ ] Add provider error/retry guidance and document a safe local-key setup walkthrough.

## Week 4 — WCAG retrieval: implemented; semantic mode optional

- [x] Build a linked summary corpus of WCAG 2.2 A/AA criteria from W3C WAI Understanding documents.
- [x] Map common axe rules directly to relevant criteria.
- [x] Add TF-IDF retrieval as the lightweight default fallback.
- [x] Add an optional local Sentence Transformers + FAISS retrieval path.
- [ ] Decide whether to make the large optional embedding dependencies part of the default developer setup.

## Week 5 — Evaluation and interface polish: in progress

- [x] Add a local JSON export for scan summaries. The schema excludes page HTML and removes URL credentials, query parameters, and fragments.
- [x] Add GitHub maintenance docs, a changelog, and issue templates.
- [ ] Create a small, clearly labeled set of accessible and intentionally flawed demo pages for repeatable manual evaluation.
- [ ] Record scan coverage and repair outcomes without claiming automated conformance.
- [ ] Review keyboard navigation, screen-reader announcements, and popup layout using manual assistive-technology checks.
- [ ] Refine report naming and presentation based on evaluation feedback.

## Week 6 — Release preparation: started

- [ ] Choose a source license and confirm third-party notices.
- [x] Add branded extension icon assets and a Windows regeneration script.
- [ ] Capture final extension screenshots.
- [ ] Review permissions, privacy disclosures, backend deployment risks, and API-key handling.
- [x] Draft a code-matched local-development privacy disclosure; publication review remains.
- [ ] Decide whether to keep the backend local-only or design a secured hosted service.
- [ ] Prepare Chrome Web Store materials if distribution is desired.

## Current release boundary

A11yLens is a local development project. Its automated scan is not a WCAG conformance verdict. The optional AI explanation can be enabled only by configuring a Groq API key; when enabled, the selected finding is sent to Groq by the backend. The source license and public deployment model are undecided.

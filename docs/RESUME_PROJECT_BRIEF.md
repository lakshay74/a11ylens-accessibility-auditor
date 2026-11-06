# A11yLens — Resume Project Brief

**Prepared:** 6 November 2026  
**Source checked:** public repository, `main` at `05fdcf1`  
**Project:** [lakshay74/a11ylens-accessibility-auditor](https://github.com/lakshay74/a11ylens-accessibility-auditor)  
**Extension version:** 0.1.0  
**Status:** working local development project; evaluation and release preparation are in progress

This brief gives Claude the verified project facts needed to write resume material. Keep the difference between implemented features, recorded checks, and pending evaluation. The project has not been published in the Chrome Web Store and has no selected source license.

## 1. Project summary

**A11yLens** is a Manifest V3 browser extension for on-demand accessibility checks of the page the user chooses. It runs axe-core locally, separates confirmed axe violations from results that need manual review, shows affected elements, and retrieves related WCAG guidance for a selected finding. A local FastAPI service provides the guidance; an optional Groq integration can generate a longer explanation and suggested HTML when a developer configures a backend API key.

### Short version

> Built a browser extension that runs local axe-core accessibility checks on demand and connects findings to WCAG guidance through a local Python API.

### Problem it addresses

Developers need a quick way to find common accessibility problems while inspecting a page and understand what an automated result means. A11yLens combines a familiar browser workflow with element highlighting and concise WCAG references. It describes axe's “incomplete” results as manual-review items so users do not mistake them for confirmed failures.

## 2. Resume-ready drafts

These are drafts to tailor to the target role and the author's actual contribution. Keep the scope and evaluation qualifiers when editing.

### Three-bullet version

- Built **A11yLens**, a Chrome/Brave Manifest V3 extension that runs axe-core 4.14.0 on demand for WCAG 2.0/2.1 A/AA and 2.2 AA tags, separates violations from manual-review findings, and lets users highlight affected elements.
- Developed a local **FastAPI** guidance API with 16 curated axe-rule mappings and a 55-record WCAG 2.2 A/AA summary corpus; implemented TF-IDF retrieval by default plus optional Sentence Transformers and FAISS retrieval and Groq-generated explanations.
- Added a privacy-conscious workflow with browser session scan restoration, JSON export that omits HTML and selectors and strips URL credentials/query/fragment, and explicit per-finding guidance requests; smoke-checked six synthetic rules and confirmed one popup-to-local-API request.

### Two-bullet version

- Created **A11yLens**, an on-demand Manifest V3 accessibility-audit extension using local axe-core to scan WCAG 2.0/2.1 A/AA and 2.2 AA tags, distinguish violations from items requiring manual review, highlight targets, and export a sanitized JSON summary.
- Built a local FastAPI and WCAG retrieval service using 16 curated rule mappings and 55 W3C WAI Understanding summaries, with TF-IDF fallback and optional local embeddings/FAISS and Groq explanations; verified six synthetic rule requests and one user-confirmed popup guidance request.

### One-line project entry

**A11yLens | Accessibility Audit Browser Extension** — JavaScript, HTML/CSS, Chrome Extensions MV3, axe-core, Python, FastAPI, WCAG retrieval, TF-IDF, optional Sentence Transformers/FAISS, optional Groq API.

### Suggested skills line

JavaScript · Browser Extension APIs (Manifest V3) · axe-core · Python · FastAPI · REST/JSON · WCAG 2.2 · TF-IDF retrieval · FAISS (optional path) · Privacy-aware data handling · Git/GitHub

Only list technologies the candidate can explain in an interview. If the optional FAISS or Groq paths were not personally exercised, qualify them as implemented optional paths rather than tested production features.

## 3. What is implemented

### Browser extension

- **Manifest V3** extension with a popup, background service worker, and content script. The UI is built with JavaScript, HTML, and CSS.
- Scans only after the user clicks **Scan this page**. The service worker injects the locally built axe-core bundle and content script into the active tab after the request.
- axe-core 4.14.0 is configured for the `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, and `wcag22aa` tags, requesting `violations` and `incomplete` result types.
- Results are shown in two groups: rule violations and manual-review items. Manual-review cards say **Possible issue** and make clear the guidance is for review, not a confirmed failure.
- Summary figures have explicit units: violation rules, affected violation elements, and manual-review rules.
- Finding cards can show an **Inspect element** action, a limited sample of HTML, an axe help link, and **Get WCAG guidance**. The target element can be scrolled to and outlined on the page.
- The popup reports backend status, scan progress, and errors. Source markup includes headings, status/alert regions, and a visible keyboard focus style; these are code features, not results of a completed assistive-technology evaluation.
- Results can be restored for the same tab from `chrome.storage.session` during the browser session.

### Local API and WCAG retrieval

- Python **FastAPI** backend exposes `GET /health` and `POST /explain`.
- Strict Pydantic request model rejects extra fields and caps input lengths for the axe rule ID, description, impact, HTML sample, failure summary, and target selector.
- The checked-in reference corpus has **55** WCAG 2.2 A/AA records: **31 Level A** and **24 Level AA**. Each record contains a concise W3C WAI Understanding summary and source link, rather than the full normative standard.
- `backend/rag.py` has **16** curated axe-rule mappings. Known criteria are selected first; lexical TF-IDF retrieval fills remaining slots up to three criteria total.
- TF-IDF lexical retrieval is the default and does not need model packages. An optional local Sentence Transformers plus FAISS cosine-similarity path is also implemented and falls back to TF-IDF when it cannot load.
- Without `GROQ_API_KEY`, the backend returns local WCAG guidance. With a key, the backend sends the selected finding and retrieved references to Groq for a generated explanation and suggested HTML. The key belongs in ignored `backend/.env`, not in the browser extension.
- The Groq HTTP path has a 35-second timeout and maps provider failures into API errors. The Groq path has **not** been tested with a configured key.

### Export and privacy behavior

- Scanning occurs in the active page after the user's request; scan results are held in browser session storage.
- The extension requests `activeTab`, `scripting`, and `storage`; its only host permission is `http://127.0.0.1:8000/*` for the local API.
- Page scanning does not send results to the API. When a user asks for guidance on one finding, the extension sends that finding's rule ID, description, impact, one HTML snippet, failure summary, and target selector to the local API. If Groq is configured, the backend forwards the selected finding and retrieved WCAG references to Groq.
- JSON export includes a page title, cleaned URL, counts, and rule summaries. It removes URL credentials, query parameters, and fragments, and excludes page HTML, selectors, and failure summaries.
- The backend's documented development command binds to `127.0.0.1`. There is no hosted A11yLens service or authentication design.

### Project and maintenance work

- Public GitHub repository with a six-week roadmap, project log, changelog, contribution guide, privacy draft, and issue templates.
- Local evaluation fixtures include a low-noise baseline and a page with nine intentional candidate issues, plus scan instructions and a blank results template.
- A separate keyboard and screen-reader review checklist records the browser, assistive technology, zoom, commit, and API mode for future manual checks.
- Build script copies axe-core and its MPL license and third-party notices into the extension folder. The notices are retained in the repository.

## 4. Architecture in plain language

1. The user opens the popup on a normal website and starts a scan.
2. The background service worker checks the active tab, then injects the local axe-core and content scripts.
3. axe-core checks the page against the configured WCAG tags. The content script returns violation and incomplete results, limited node samples, and counts.
4. The popup groups and displays the results. The user can request highlighting or open the trusted axe help link.
5. If the user chooses WCAG guidance on a finding, the popup sends only that selected finding to FastAPI on the local machine.
6. FastAPI uses direct axe-rule mappings first, then the local retrieval path. It returns local guidance by default; Groq is an optional provider path.

## 5. Verified checks and evidence

### Local guidance smoke check

On 30 October 2026, `/health` returned `status: ok` and `groq_configured: false`. Six synthetic `POST /explain` requests completed without errors using the local TF-IDF and rule-mapping path:

| Axe rule | Criteria returned by A11yLens | Axe 4.14.0 tag reference recorded |
| --- | --- | --- |
| `color-contrast` | 1.4.3, 1.4.1, 1.4.11 | 1.4.3 (`wcag143`) |
| `link-name` | 2.4.4, 4.1.2, 2.5.3 | 2.4.4 (`wcag244`), 4.1.2 (`wcag412`) |
| `aria-required-children` | 1.3.1 | 1.3.1 (`wcag131`) |
| `target-size` | 2.5.8, 1.4.4 | 2.5.8 (`wcag258`) |
| `label-content-name-mismatch` | 2.5.3, 1.3.5, 1.3.3 | 2.5.3 (`wcag253`) |
| `aria-valid-attr-value` | 4.1.2 | 4.1.2 (`wcag412`) |

Each response contained its expected axe-tagged criterion. Extra criteria came from retrieval. This is a controlled smoke check on synthetic requests, not a measured retrieval-accuracy evaluation. Axe criterion tags are a rule-to-criterion comparison reference, not independent ground truth for whether a page-level finding is correct. The extension currently omits `rule.tags` from its scan payload.

### Popup check reported by the user

After FastAPI was restarted, the user confirmed that **Get WCAG guidance** worked in the extension popup. This verifies one popup-to-local-API request. The rule ID and whether the card was a violation or manual-review card were not recorded. The API used local mode because Groq was not configured.

The user also reported that the earlier T1 labels and summary wording worked when tested on `https://penny-juice.com`. The later follow-up that reduced a duplicate note to one per rule and added guidance to manual-review cards still needs its own browser check.

## 6. What is not yet verified or released

- The two local evaluation fixtures have not yet been scanned in Brave. The nine expected conditions are candidate checks only; actual rules and categories have not been recorded.
- No repair-before/after outcomes, evaluation coverage, retrieval accuracy score, or performance benchmark have been measured.
- No keyboard-only, screen-reader, or full popup accessibility review has been completed. A checklist exists, but no results are recorded.
- The optional Groq path has not been tested with a key.
- The code is not published in the Chrome Web Store. There is no hosted backend.
- No source license has been selected. Public GitHub visibility alone does not state a project license.
- Automated findings are not a WCAG conformance verdict. The corpus contains informative W3C WAI summaries, not the full normative standard.
- Do not claim that A11yLens detects all accessibility issues, automatically fixes pages, guarantees WCAG compliance, or has a measured accuracy rate.

## 7. Portfolio positioning

### 30-second explanation

“A11yLens is a browser extension I’m building to make accessibility review easier during development. It runs axe-core locally on a page after the user starts a scan, separates actual axe violations from items that need manual review, and lets the developer inspect an affected element. For a selected finding, a local FastAPI service retrieves relevant WCAG guidance. The project also includes an optional Groq explanation path, but the local retrieval flow is the one I’ve smoke-checked so far.”

### Topics to discuss in an interview

- Why `incomplete` results must be described as manual review rather than definite failures.
- How curated mappings and lexical search work together, and why the optional embedding path has a TF-IDF fallback.
- How the active-tab permission and user-started workflow limit page access.
- Why page-derived snippets are sent only for an explicitly selected guidance request, and what changes when Groq is enabled.
- Why axe's WCAG tags are useful for comparing rule mappings but do not prove that a page result is correct.
- What the next evaluation should measure: observed rule IDs on the two fixtures, category, affected nodes, human review, and repair outcomes.

## 8. Paste this prompt into Claude

```text
I want to add my A11yLens project to my resume. Use the attached project brief as the source of truth and tailor the result to the resume and role description I provide.

Please produce:
1. A concise project heading and one-sentence summary.
2. Two or three strong resume bullets that start with clear action verbs and include relevant technologies.
3. A shorter one-line version if space is limited.
4. A short list of interview talking points and likely follow-up questions.

Accuracy rules:
- Do not invent user counts, time savings, accuracy, coverage percentages, performance results, employers, collaborators, or deployment claims.
- Do not say the project is WCAG-compliant or that it detects every accessibility problem.
- Describe the six API requests as a synthetic local smoke check, not a formal accuracy evaluation.
- Say the Groq integration is optional and has not yet been tested with a configured key.
- Say browser fixture scans and assistive-technology evaluation are still pending.
- Do not say the extension or API is published or hosted; the extension is a local development build and the backend runs on localhost.
- Do not describe the source as open source or assign a license; no A11yLens source license has been chosen.
- If the brief does not establish whether I built a feature alone or with assistance, ask me rather than inventing an attribution claim.

First ask me for the target job title, job description, resume format, and which parts I personally implemented. Then tailor the wording without adding unsupported claims.
```

## 9. Source files Claude can inspect

- `README.md` — overview, install, architecture, privacy notes.
- `docs/ARCHITECTURE.md` — beginner walkthrough of request and data flow.
- `docs/ROADMAP.md` — completed and pending milestones.
- `docs/PROJECT_LOG.md` — decisions, smoke-check criteria, and next work.
- `extension/manifest.json`, `extension/background.js`, `extension/content.js`, `extension/popup.js` — extension implementation.
- `backend/main.py`, `backend/rag.py`, `backend/data/wcag.json` — API, retrieval, and reference corpus.
- `evaluation/README.md` and `evaluation/RESULTS_TEMPLATE.md` — fixture procedure and blank result record.

This report is a resume-writing handoff, not a claim that the project has completed accessibility, security, or release evaluation.

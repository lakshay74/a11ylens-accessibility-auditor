# A11yLens project log

This file keeps the working state and decisions in the repository so project context survives beyond a chat session.

**Last updated:** 2026-11-03
**Project name:** A11yLens
**Current stage:** Week 5 - evaluation and interface polish

**Public repository:** https://github.com/lakshay74/a11ylens-accessibility-auditor
**Tracked branch:** `main` (remote: `origin`)
**GitHub baseline:** `e9a6e50` - Link findings to axe rule guidance
**T1 local commit:** `d4d241f` - Clarify manual review guidance and results (not pushed)
**T2 local commit:** `236f35d` - Verify local guidance mappings (not pushed)
**T3 evaluation setup:** Local fixtures and scan instructions added; browser results are pending and this work is not pushed.

## Current implementation

- Manifest V3 browser extension scans the active page only after the user starts a scan.
- axe-core findings and manual-review results appear in the popup; users can highlight targets.
- The popup can export a JSON summary. It does not put page HTML, failure summaries, selectors, URL credentials, query parameters, or fragments into the export.
- Finding cards link to axe rule guidance when the URL is on Deque University's HTTPS domain.
- Manual-review cards use a neutral "Possible issue" badge and offer WCAG guidance with a note that axe did not confirm a violation. Summary tiles distinguish violation rules, affected violation elements, and manual-review rules. The cross-category note appears once per rule.
- The user reports that the original T1 labels and summary were tested on `https://penny-juice.com` and worked. The follow-up that moves the repeated note to one card and adds manual-review guidance has not yet been checked in Brave.
- The user-provided review reports screenshots of a `claude.ai` scan with 3 violation rules, 4 affected violation elements, and 4 manual-review rules. This is one observed page scan, not an evaluation result. The review also notes that personal browser details appeared in screenshots; future demo captures should use a clean profile and demo page.
- Branded PNG icons are included in the manifest, with a Windows script to regenerate the icon sizes.
- The popup detects when it is opened as a local file, disables scanning, and tells the user how to load the unpacked extension in Brave. The extension-manager screenshot confirms Brave listed version 0.1.0. Separately, the supplied review reports one scan on `claude.ai`; that scan has not been reproduced in this session.
- FastAPI returns local guidance. Optional Groq explanations are disabled unless `GROQ_API_KEY` is configured.
- WCAG 2.2 A/AA summaries are checked in under `backend/data/`. Retrieval uses curated rule mappings first and TF-IDF by default; local embeddings + FAISS are optional.
- A local guidance smoke check covered six synthetic rule requests. The API was healthy and returned local TF-IDF guidance; Groq was not configured. The exact results are below. This is a smoke check, not a measured accuracy evaluation.
- After the backend was restarted, the user confirmed that **Get WCAG guidance** worked from the extension popup. This verifies one popup-to-local-API request; the selected axe rule and whether the card was a violation or manual-review card were not recorded. Groq remained unconfigured, so this was the local-guidance path.
- The bundled axe-core 4.14.0 rule table tags `link-name` with both `wcag244` and `wcag412`; `backend/rag.py` now directly maps it to 2.4.4 and 4.1.2. Axe criterion tags are currently omitted from A11yLens scan output by `extension/content.js`'s `serializeRule()`.
- Added two local evaluation fixtures, a scan procedure, and a blank results template under `evaluation/`. The intentional issue list is a candidate checklist, not confirmed scan output; no fixture scans or repair outcomes have been recorded yet.
- Backend binds to `127.0.0.1` in the documented development command.

## Decisions to preserve

1. **Name:** A11yLens. “a11y” is the common abbreviation for accessibility; “lens” describes inspection.
2. **Privacy:** Scanning runs locally in the active page. Only an explicitly selected finding is sent to the local API for explanation. If Groq is configured, that selected finding can be sent to Groq. JSON export is a local download and omits page HTML.
3. **Reference accuracy:** W3C WAI Understanding summaries are informative guidance, not the full normative WCAG text. Findings and explanations must not be presented as a conformance verdict.
4. **Optional model dependencies:** Keep Sentence Transformers and FAISS optional so the basic backend stays smaller and has a TF-IDF fallback.
5. **No license chosen yet:** Do not imply that the source is open-source or add a license without a deliberate choice. Preserve axe-core's separate license notices.
6. **Privacy statement:** `docs/PRIVACY.md` describes current local data flows as a draft; revise it if implementation or hosting changes and review it before store publication.
7. **GitHub status:** The source repository is public and `main` tracks `origin/main`. Public visibility is not a source license, a hosted backend, or a store release.

## Local run commands

From the repository root in PowerShell:

```powershell
Set-Location extension
npm install
npm run build
Set-Location ..
py -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Then open `brave://extensions`, enable Developer mode, choose **Load unpacked**, and select the repository's `extension` folder. Open an ordinary website and use the A11yLens toolbar icon. Opening `extension/popup.html` directly as a file is only a static preview; it cannot use extension messaging APIs. The popup now shows that instruction when opened outside an extension context.

## Next work

1. Run the two evaluation pages in Brave and record observed violation and manual-review rule IDs in `evaluation/RESULTS_TEMPLATE.md`.
2. Repair one intentional issue at a time and record before/after results without presenting them as a WCAG conformance verdict. Treat axe's rule tags as a comparison reference, not independent ground truth.
3. Verify the Groq-backed explanation path when a key is deliberately configured; the current check exercised local-only mode.
4. Decide how real users should get guidance before changing the backend or extension permissions; the current API remains local-only.
5. Review popup keyboard and screen-reader behavior, and investigate frame and shadow DOM limits.
6. Review privacy hardening before sending any finding content to Groq; any change to outgoing page data needs an explicit product decision.
7. Choose a source license and prepare screenshots using a clean profile and demo page. Prepare store materials only if distribution is desired.

## Local guidance smoke check (2026-10-30)

`GET /health` returned `status: ok`, `service: A11yLens API`, and `groq_configured: false`. Six synthetic `POST /explain` requests ran in local mode using `TF-IDF lexical retrieval plus axe rule mapping`:

| Axe rule | WCAG criteria returned, in API order | Axe 4.14.0 WCAG tag reference |
| --- | --- | --- |
| `color-contrast` | 1.4.3, 1.4.1, 1.4.11 | 1.4.3 (`wcag143`) |
| `link-name` | 2.4.4, 4.1.2, 2.5.3 | 2.4.4 (`wcag244`), 4.1.2 (`wcag412`) |
| `aria-required-children` | 1.3.1 | 1.3.1 (`wcag131`) |
| `target-size` | 2.5.8, 1.4.4 | 2.5.8 (`wcag258`) |
| `label-content-name-mismatch` | 2.5.3, 1.3.5, 1.3.3 | 2.5.3 (`wcag253`) |
| `aria-valid-attr-value` | 4.1.2 | 4.1.2 (`wcag412`) |

All six responses included the expected axe-tagged criterion. The extra criteria are retrieval results beyond the direct axe tag. No request errors occurred. These controlled smoke-check requests do not measure retrieval accuracy on real findings. Axe tags can be used as rule-to-criterion reference labels or to measure tag agreement, but they are not independent human-verified gold labels for whether a specific page finding is correct. Tags are not included in the current scan payload because `serializeRule()` drops `rule.tags`.

After this API check, the backend had been stopped. The user later saw the popup's local-backend connection message, then confirmed that **Get WCAG guidance** worked after FastAPI was started again and `/health` returned `ok`. The selected rule and card category were not recorded, so this confirms the local popup-to-API path without claiming that a particular manual-review card was tested.

See [the detailed project progress and technical handoff](A11YLENS_PROJECT_PROGRESS_REPORT.md) and its [shareable PDF](../output/pdf/A11yLens_Project_Progress_Report.pdf) for a full snapshot of implementation, privacy boundaries, repository files, history, and setup observations.

See [ROADMAP.md](ROADMAP.md) for the full milestone checklist and [CHANGELOG.md](../CHANGELOG.md) for user-facing changes.

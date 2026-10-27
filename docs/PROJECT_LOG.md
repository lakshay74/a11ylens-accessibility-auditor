# A11yLens project log

This file keeps the working state and decisions in the repository so project context survives beyond a chat session.

**Last updated:** 2026-10-27  
**Project name:** A11yLens  
**Current stage:** Week 5 — evaluation and interface polish

## Current implementation

- Manifest V3 browser extension scans the active page only after the user starts a scan.
- axe-core findings and manual-review results appear in the popup; users can highlight targets.
- The popup can export a JSON summary. It does not put page HTML, failure summaries, selectors, URL credentials, query parameters, or fragments into the export.
- Branded PNG icons are included in the manifest, with a Windows script to regenerate the icon sizes.
- FastAPI returns local guidance. Optional Groq explanations are disabled unless `GROQ_API_KEY` is configured.
- WCAG 2.2 A/AA summaries are checked in under `backend/data/`. Retrieval uses curated rule mappings first and TF-IDF by default; local embeddings + FAISS are optional.
- Backend binds to `127.0.0.1` in the documented development command.

## Decisions to preserve

1. **Name:** A11yLens. “a11y” is the common abbreviation for accessibility; “lens” describes inspection.
2. **Privacy:** Scanning runs locally in the active page. Only an explicitly selected finding is sent to the local API for explanation. If Groq is configured, that selected finding can be sent to Groq. JSON export is a local download and omits page HTML.
3. **Reference accuracy:** W3C WAI Understanding summaries are informative guidance, not the full normative WCAG text. Findings and explanations must not be presented as a conformance verdict.
4. **Optional model dependencies:** Keep Sentence Transformers and FAISS optional so the basic backend stays smaller and has a TF-IDF fallback.
5. **No license chosen yet:** Do not imply that the source is open-source or add a license without a deliberate choice. Preserve axe-core's separate license notices.
6. **Privacy statement:** `docs/PRIVACY.md` describes current local data flows as a draft; revise it if implementation or hosting changes and review it before store publication.

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

Then open `brave://extensions`, enable Developer mode, choose **Load unpacked**, and select the repository's `extension` folder. Open an ordinary website and use the A11yLens toolbar icon. Opening `extension/popup.html` directly as a file is only a static preview; it cannot use extension messaging APIs.

## Next work

1. Create a small set of accessible and intentionally flawed local demo pages for manual evaluation.
2. Define a simple, honest measurement sheet for finding counts and repair outcomes.
3. Review popup keyboard and screen-reader behavior and capture screenshots.
4. Choose a source license before public collaboration or release.
5. Complete privacy and permission review; decide whether to keep the backend local-only.
6. Create/configure a GitHub remote when the repository destination and visibility are settled.

See [ROADMAP.md](ROADMAP.md) for the full milestone checklist and [CHANGELOG.md](../CHANGELOG.md) for user-facing changes.

# Contributing to A11yLens

Thank you for helping improve A11yLens. The project is in local development and does not yet have a source license or public contribution policy.

## Before changing code

1. Read [the architecture guide](docs/ARCHITECTURE.md) to understand the extension and API flow.
2. Check [the roadmap](docs/ROADMAP.md) and [the project log](docs/PROJECT_LOG.md) before choosing work.
3. Keep changes focused and update the project log or changelog when behavior or a project decision changes.

## Build the extension

```powershell
Set-Location extension
npm install
npm run build
```

The build copies axe-core from the pinned npm dependency into `extension/vendor/`. The generated `axe.min.js` file is ignored by Git; retain the third-party license and notice files in the repository.

## Run the backend

From the repository root:

```powershell
py -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Keep real API keys in `backend/.env`. Never commit that file, keys, private page HTML, or unredacted audit exports.

## Change and review checklist

- Keep browser permissions limited to the features that need them.
- Treat page HTML and text as untrusted input; use safe DOM APIs and keep API input limits.
- Preserve the distinction between axe violations and checks needing manual review.
- Do not describe an automated result as proof of WCAG conformance.
- Preserve W3C links and axe-core license notices.
- Describe user-visible changes in `CHANGELOG.md` and keep `docs/ROADMAP.md` / `docs/PROJECT_LOG.md` current.

## GitHub issues

Use the bug report template for reproducible defects and the feature request template for proposed behavior. Do not attach sensitive page content; describe the issue with a public or synthetic example where possible.

# Local backend and optional Groq setup

A11yLens can return local WCAG guidance without a Groq key. Groq is optional and is used only when you configure a key in the backend environment. The extension never stores the key.

## 1. Prepare the local backend

Run these commands once from the repository root in PowerShell:

```powershell
py -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

Create the local settings file only if it does not already exist:

```powershell
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

If `backend/.env` already exists, edit that file instead of copying over it. Keep the real key in this file only. Git ignores `backend/.env`; do not paste a key into source code, the extension, screenshots, issue reports, or chat messages.

## 2. Choose local-only or Groq mode

### Local-only mode

Leave `GROQ_API_KEY` blank in `backend/.env`. The API still retrieves WCAG criteria and returns local guidance. `/health` should report `"groq_configured": false`.

### Optional Groq mode

1. Obtain your own API key through your Groq account.
2. Open `backend/.env` in a local text editor and put the key after `GROQ_API_KEY=`. Do not add quotes unless the provider's key format requires them.
3. Keep `GROQ_MODEL` set to a model available to your account, or change it to an available model ID.
4. Save the file, stop the running backend with `Ctrl+C`, and start it again. The backend reads `.env` at startup.
5. Check `http://127.0.0.1:8000/health`. A true `groq_configured` value means the server detected a non-empty key. The response does not return the key itself.

When Groq mode is enabled, requesting guidance sends the selected finding, including its short HTML snippet, target selector, description, impact, axe failure summary, and retrieved WCAG references, from the local backend to Groq. Use local-only mode when you do not want page-derived content sent to that provider. See [the privacy notes](PRIVACY.md).

## 3. Start the API

From the repository root:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Keep this process running while you use **Get WCAG guidance**. Scanning still works in the browser when the API is offline; only the guidance request needs the API.

## 4. Troubleshoot the message

| What you see | What it means | What to do |
| --- | --- | --- |
| Popup says it cannot reach the local backend | FastAPI is stopped, using a different port, or unreachable | Start the command above, check `/health`, then close and reopen the popup and try again. |
| `/health` reports `groq_configured: false` | The server will use local WCAG guidance | This is expected when `GROQ_API_KEY` is blank. No Groq key is needed for local guidance. |
| `502` and “Groq rejected the request” | The provider rejected the configured key or model | Check the key and model in `backend/.env`, save, restart FastAPI, and retry once. |
| `502` and “Could not reach Groq” | The backend could not connect to the provider | Check network access, then retry when the provider is reachable. |
| `502` and “Groq returned an invalid explanation” | The provider response could not be parsed as the expected JSON | Retry once. If it repeats, keep using local guidance and report the issue without including your key or page content. |
| `504` and “Groq did not respond before the timeout” | The provider did not answer within the 35-second timeout | Check provider availability and retry once. The current code does not automatically retry requests. |

If you want to return to local-only mode, blank `GROQ_API_KEY`, save the file, restart FastAPI, and confirm `/health` reports `groq_configured: false`.

## 5. Keep the key private

- Never commit `backend/.env`; the repository ignores it.
- Do not put the key in `extension/`, `manifest.json`, JavaScript, exported reports, screenshots, or issue templates.
- Do not share an error log or screenshot until you have checked it for keys and private page content.
- If a key is exposed, revoke it through your provider account and create a replacement there. Do not send the replacement key to A11yLens or Codex.

The Groq path has not yet been exercised in this project. Keep that status separate from the tested local-guidance flow.

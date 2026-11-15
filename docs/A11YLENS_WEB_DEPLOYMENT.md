# A11yLens Web deployment

## Architecture

The web interface is a small Node server in `web/`. It serves the HTML, CSS and JavaScript, and reads its API address from the runtime `API_BASE_URL` environment variable. This keeps one build usable locally and on Embarko.

The FastAPI service in `backend/` runs Chromium with Playwright and axe-core, calls Groq from the server when a key is configured, and stores public reports in MongoDB. Build the backend with `backend/Dockerfile` on a container host that can run Chromium, allow outbound HTTP/HTTPS scans, and connect to MongoDB. Start by checking whether the host can provide around 1 GB of memory for one API process; this is an initial sizing estimate, not a measured minimum. Keep Uvicorn at one worker because the scan semaphore and rate limit are process-local.

Embarko's current [hosting guide](https://embarko.ai/guides/free-hosting-for-students) describes a single 256 MB process per dynamic app, and its [AI app guide](https://embarko.ai/guides/how-to-deploy-ai-app) lists one dynamic app on the free plan. That suits this small Node frontend, but the Playwright/Chromium API needs a separate container-capable host with more memory. MongoDB is also external; Embarko does not provide a managed MongoDB service.

## MongoDB Atlas

1. Create a [MongoDB Atlas project](https://www.mongodb.com/atlas/database) and a [free cluster](https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/) in a region close to the API host.
2. Create a database user with read/write access to the `a11ylens` database. This database user is separate from the account you use to sign in to Atlas; see [Atlas database users](https://www.mongodb.com/docs/atlas/tutorial/create-mongodb-user-for-cluster/).
3. In Atlas **Network Access**, add the API host's outbound IP address or range. Atlas only accepts connections from its [project IP access list](https://www.mongodb.com/docs/atlas/security/ip-access-list/). Do not add the frontend visitor's address; the API server connects to MongoDB.
4. In the cluster's **Connect** dialog, choose the Python driver and copy the connection string. Replace its user/password placeholders and include the database name, for example `...mongodb.net/a11ylens?retryWrites=true&w=majority`. The backend uses PyMongo's [async client](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/).
5. Add the connection string to the API host as `MONGODB_URI`. Do not add it to Git, the frontend, screenshots, or this repository. Set `MONGODB_DATABASE=a11ylens` and `MONGODB_COLLECTION=reports`.

Atlas accepts connections only from IPs on the project's access list and requires a database user. If the API host does not provide stable outbound IPs, choose a host/network option that can restrict MongoDB access instead of opening the database to every IP.

## Deploy the API

Build from the `backend/` directory with `backend/Dockerfile`. Configure these server-side environment variables:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `PORT` | Supplied by the host |
| `FRONTEND_ORIGIN` | Exact frontend origin, such as `https://a11ylens-web.embarko.app` |
| `MONGODB_URI` | Atlas connection string |
| `MONGODB_DATABASE` | `a11ylens` |
| `MONGODB_COLLECTION` | `reports` |
| `GROQ_API_KEY` | Optional; kept on the API host only |
| `GROQ_MODEL` | Optional; defaults to `openai/gpt-oss-20b` |
| `SCAN_RATE_LIMIT` | Optional; defaults to 5 scans per client per minute |

The backend also supports `CHROME_EXTENSION_ORIGIN` for one exact extension origin if you want the deployed API to serve the existing extension. In development, the API permits the extension origin and the local web origin. In production, it permits only the configured frontend origin and optional exact extension origin.

Check `https://<api-host>/health`. `mongo_configured` should be `true` for durable share links; `groq_configured` indicates whether AI explanations are enabled. Never put `GROQ_API_KEY` or `MONGODB_URI` in frontend settings.

## Deploy the frontend to Embarko

1. Deploy the `web/` folder as a Node server app. The app reads `PORT` and listens on `0.0.0.0` as Embarko expects.
2. Set the server environment variable `API_BASE_URL` to the public HTTPS base URL of the API, without `/api/scan` at the end.
3. Use the resulting exact frontend origin as the API's `FRONTEND_ORIGIN`, then redeploy/restart the API.
4. Open the frontend link, run a public example page, expand a finding, and try the share link. The share route is `/r/{id}` on the frontend; its data comes from `/api/reports/{id}` on the API.

Embarko static sites cannot read runtime environment variables. Keep `web/` as a Node server app so `API_BASE_URL` stays a runtime setting and is not compiled into browser code. Do not include a Dockerfile in the Embarko frontend upload; Embarko builds Node apps itself.

## Local development

Install the Python requirements and the matching Chromium binary once:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe -m playwright install chromium
```

Set `FRONTEND_ORIGIN=http://localhost:4173` in `backend/.env`, then start both processes in separate terminals:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

```powershell
Set-Location web
$env:API_BASE_URL = "http://127.0.0.1:8000"
npm start
```

Without `MONGODB_URI`, scans still display but are not saved and cannot have a share link. Without `GROQ_API_KEY`, the app uses local WCAG retrieval and leaves corrected code blank when it cannot safely infer a fix.

## Security and report behavior

- Scan URLs accept only HTTP/HTTPS. The API rejects local names, non-public DNS answers and private, loopback, link-local, reserved and metadata IP addresses, including Azure's `168.63.129.16` platform address. The browser validates each requested resource and checks each redirect before following it; HTTPS-to-HTTP downgrade redirects are rejected.
- Scans have browser timeouts, per-document/resource/total response limits, an 80-request cap, a two-scan concurrency cap and a per-client rate limit.
- The scanner blocks image, media and font downloads and only allows page `GET`/`HEAD` requests. Configure the API host's egress controls to deny private, loopback, link-local and cloud metadata ranges as a second layer.
- Report IDs are random bearer links. Anyone who has a link can view its report; the app has no accounts. Stored display URLs omit query strings and fragments.
- The frontend renders scanned HTML and generated fixes as text, never as executable markup. Groq and MongoDB credentials are server-side environment variables.

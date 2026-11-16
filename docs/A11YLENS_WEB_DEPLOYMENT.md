# A11yLens Web deployment

## Architecture

The web interface is a small Node server in `web/`. It serves the HTML, CSS and JavaScript, and reads its API address from the runtime `API_BASE_URL` environment variable. This keeps one build usable locally and on Embarko.

The FastAPI service in `backend/` runs Chromium with Playwright and axe-core, calls Groq from the server when a key is configured, and stores public reports in MongoDB. Build the backend with `backend/Dockerfile` on a container host that can run Chromium, allow outbound HTTP/HTTPS scans, and connect to MongoDB. Start by checking whether the host can provide around 1 GB of memory for one API process; this is an initial sizing estimate, not a measured minimum. Keep Uvicorn at one worker because the scan semaphore and rate limit are process-local.

If a scan reports **“Playwright is not installed on this API host,”** the API was started with a Python environment that does not have `backend/requirements.txt` installed. Rebuild the API from `backend/Dockerfile`; it installs both the Python package and Chromium. On a non-container host, install the requirements and Chromium in the same Python environment used to run Uvicorn. Installing dependencies for the frontend does not install them for the API.

Embarko is not limited to front ends: it can run small Node and Python server apps. Its current [student hosting guide](https://embarko.ai/guides/free-hosting-for-students) says the free plan has one dynamic app, each app gets 256 MB, and Embarko does not provide a managed MongoDB service. Embarko also builds apps without using a project Dockerfile. Those limits fit this small Node frontend, but not the current scanner API: the API needs Playwright plus Chromium and is packaged with Linux browser dependencies in `backend/Dockerfile`. Keep the frontend on Embarko and run the scan API on a separate container-capable host with more memory; keep MongoDB external too. Embarko's own [deployment guide](https://embarko.ai/guides/how-to-deploy-ai-app) says a frontend and backend count as two apps, so the free plan's one dynamic-app slot cannot host both services there.

**Deployment status (16 November 2026):** no public API host or MongoDB connection has been configured for this project. The contest instructions require an Embarko app link but do not supply a separate API host. The frontend can be deployed to Embarko after a public API URL exists; until then, a deployed page would not be able to scan real websites. The API Dockerfile and environment-variable setup below are prepared for a compatible host, but they do not create or pay for that hosting account.

## Free API hosting options reviewed

Reviewed on 16 November 2026 for the current Playwright/Chromium backend and MongoDB report storage:

| Option | Free allowance and fit | Assessment |
| --- | --- | --- |
| [Oracle Cloud Always Free VM](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) | Up to 2 OCPU and 12 GB RAM in the home region. [Playwright supports Linux ARM64](https://playwright.dev/docs/intro). | Best ongoing-free resource fit. It is a VM, so deployment needs Docker, HTTPS, firewall setup, and basic maintenance. Signup generally asks for a phone number and card for verification; [Oracle says the card is not charged unless the account is upgraded](https://docs.oracle.com/en/learn/cloud_free_tier/). VM capacity can be unavailable in some regions. |
| [Google Cloud Run](https://cloud.google.com/run/pricing) | Monthly free allowances cover a small amount of container use, then usage is billed. | Less server maintenance, but a secure Atlas allowlist needs a [static outbound IP](https://docs.cloud.google.com/run/docs/configuring/static-outbound-ip) through Cloud NAT, which has [hourly and data charges](https://cloud.google.com/nat/pricing). Not fully free with this project's current MongoDB network setup. |
| [Render Free](https://render.com/docs/compute-plans) | 512 MB RAM and 0.1 CPU; the service [sleeps after 15 minutes](https://render.com/docs/free) without traffic. | Not recommended for the Chromium scanner: the tight memory/CPU limit risks failed scans, and sleeping creates a cold start. |
| [Railway Free](https://docs.railway.com/pricing/free-trial) | $5 trial credit for 30 days, then $1 monthly credit; up to 0.5 GB RAM on the [free plan](https://docs.railway.com/pricing/plans). | Useful for a short experiment, but not a durable zero-cost host and has little memory headroom for Chromium. |

**Recommended no-monthly-hosting-cost path:** keep the Node frontend on Embarko, run the API on an Oracle Always Free VM, and use a free [Atlas M0 cluster](https://www.mongodb.com/pricing) with the VM's public IP in Atlas's access list. Atlas M0 includes 512 MB of storage, suitable for a small demo. This option is not one-click: create the VM in the Always Free home region, confirm capacity, then configure Docker, HTTPS, firewall rules, and MongoDB credentials. Keep the VM within the Always Free limits and do not upgrade the Oracle account to a paid plan without checking the bill impact. The current code's Dockerfile is the starting point; Playwright supports Linux ARM64. I prepared a VM deployment bundle and steps in [ops/oracle-vm](../ops/oracle-vm/README.md). This is a researched option, not a deployed service or account we have configured.

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

On Windows, if Playwright's managed browser is missing, the scanner can use an installed Brave, Chrome, or Edge browser. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to an executable path to choose a specific browser. Linux API hosts need the managed Chromium binary; the Dockerfile installs it with its system dependencies.

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

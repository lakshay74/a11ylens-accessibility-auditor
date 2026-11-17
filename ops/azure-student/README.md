# Deploy the A11yLens API with Azure for Students

Use this path if you qualify for Azure for Students: Microsoft currently requires that you are at least 18, attend an accredited two- or four-year college, study full time, and verify with your institution email. The offer includes $100 Azure credit for 12 months without a credit card. Azure Container Apps also has monthly consumption grants; traffic and resource use beyond the free grants consumes student credit.

The web frontend remains on Embarko. This deploys the existing FastAPI/Playwright `backend/Dockerfile` to Azure Container Apps with an automatically generated HTTPS endpoint. Report storage stays on MongoDB Atlas M0. The Container Apps outbound IP list can change over time, so keep Atlas's IP access list in sync. Do not use `0.0.0.0/0`.

This guide prepares commands and settings only. It does not sign up for Azure, create services, consume credits, or deploy the app.

## 1. Create the API service

1. Activate [Azure for Students](https://azure.microsoft.com/en-us/free/students) with your verified school email. If you are not eligible, follow the [Oracle VM free-tier guide](../oracle-vm/README.md) instead.
2. Install the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) on your computer, open PowerShell, and sign in:

   ```powershell
   az extension add --name containerapp --upgrade
   az login
   az account show --output table
   ```

3. Create a resource group in a region near you, for example `centralindia`:

   ```powershell
   az group create --name rg-a11ylens --location centralindia
   ```

4. Deploy from the `backend/` folder so Azure builds the existing Dockerfile. Run this from the repository root:

   ```powershell
   Push-Location backend
   az containerapp up `
     --name a11ylens-api `
     --resource-group rg-a11ylens `
     --location centralindia `
     --source . `
     --ingress external `
     --target-port 8000
   Pop-Location
   ```

   Azure creates the Container Apps environment and an externally reachable HTTPS service. It may also create a container registry and monitoring resources; check the student credit and resource group cost view.

5. Set the container to one replica with 1 vCPU and 2 GiB memory. One replica preserves the API's process-local scan concurrency and rate limits. Zero minimum replicas avoids idle compute charges but adds a cold start:

   ```powershell
   az containerapp update `
     --name a11ylens-api `
     --resource-group rg-a11ylens `
     --cpu 1.0 `
     --memory 2Gi `
     --min-replicas 0 `
     --max-replicas 1
   ```

6. Copy the API's **Application Url** from the Container App Overview. It should be HTTPS. Check `https://<api-url>/health` before configuring the frontend.

## 2. Create Atlas and restrict access

1. Create a free Atlas M0 cluster and a database user with read/write access to `a11ylens`.
2. Find the Container App's `properties.outboundIpAddresses` list in Azure Portal or with:

   ```powershell
   az containerapp show --name a11ylens-api --resource-group rg-a11ylens --query properties.outboundIpAddresses --output tsv
   ```

3. Add each current outbound IP as an individual `/32` entry in Atlas Network Access. Do not add `0.0.0.0/0`. Microsoft notes these outbound IPs can change; check the list again if the app stops reaching Atlas after an environment change.
4. Copy the Atlas Python driver URI and URL-encode special characters in the database username or password.

## 3. Configure server-side environment variables

In the Azure Portal, open the Container App's **Secrets** settings and add the Atlas URI as a secret named `mongodb-uri`. Add `GROQ_API_KEY` as a secret only if you have a key. Do not paste either secret into chat or put it in Git.

Add these environment variables to the container. Set `MONGODB_URI` to reference the `mongodb-uri` secret:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `PORT` | `8000` |
| `FRONTEND_ORIGIN` | Exact Embarko origin; set after the frontend name is final |
| `MONGODB_URI` | Secret reference to `mongodb-uri` |
| `MONGODB_DATABASE` | `a11ylens` |
| `MONGODB_COLLECTION` | `reports` |
| `SCAN_RATE_LIMIT` | `5` |
| `GROQ_API_KEY` | Optional secret reference |
| `GROQ_MODEL` | Optional; defaults to `openai/gpt-oss-20b` |

Azure restarts the app when environment variables or secrets change. Once Atlas is reachable, `/health` should report `mongo_configured: true`.

## 4. Connect the Embarko frontend

Deploy `web/` to Embarko as a Node server app. Set its runtime `API_BASE_URL` to the Container App HTTPS URL, without `/api/scan`. Then set `FRONTEND_ORIGIN` on the API to the exact Embarko origin, wait for the new revision to become ready, and run a public example scan plus a share-link check.

## Cost and reliability limits

- Azure Container Apps Consumption grants 180,000 vCPU-seconds, 360,000 GiB-seconds, and 2 million HTTP requests per subscription per month. It charges only beyond those grants; the Azure for Students credit can cover eligible overages, but the credit is limited.
- The app scales to zero by default for HTTP ingress. The first scan after inactivity may wait for the container to start.
- Azure for Students is a time-limited credit, not permanent free hosting. If the credit runs out or expires without upgrading, Azure decommissions student resources.
- Atlas M0 provides 512 MB storage. Keep report data small and avoid storing sensitive page content.
- The app has no accounts. Anyone can scan public URLs, subject to the API's rate limit and SSRF checks.

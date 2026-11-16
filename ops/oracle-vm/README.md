# Deploy the A11yLens API on an Oracle Always Free VM

This deploys the FastAPI scanner behind Caddy HTTPS. The Node frontend remains on Embarko, and MongoDB Atlas remains external. The VM must be in the Oracle Always Free home region and use an Always Free eligible shape. Oracle's current free allocation allows up to 2 OCPU and 12 GB RAM; a 2 OCPU, 8 GB Ubuntu ARM64 VM leaves memory headroom for Chromium while staying within that allocation.

This guide does not create an Oracle account, DNS name, Atlas cluster, or public deployment. Keep `ops/oracle-vm/.env` on the VM only; the repository ignores `.env` files.

## 1. Create the VM and DNS name

1. In Oracle Cloud, create an Ubuntu 24.04 ARM64 `VM.Standard.A1.Flex` instance in your **home region**. Choose 2 OCPU and 8 GB memory, and select an Always Free eligible boot volume and instance.
2. Assign a public IPv4 address. Save it for the next step and for the Atlas access list.
3. Create a DNS A record for a hostname you control, pointing to that public IPv4 address. A free dynamic DNS hostname can work. Wait until the name resolves to the VM address before starting Caddy.
4. Add inbound network rules for TCP 22 from your current public IP only, and TCP 80 and 443 from the internet. Do not open ports 8000 or 27017. Keep outbound HTTP/HTTPS available for page scans and Atlas connections.

Oracle may show an out-of-capacity error for Always Free shapes in a region. If that happens, try another availability domain in the same home region and do not upgrade the account just to bypass the limit.

## 2. Create the Atlas database

1. Create a free Atlas M0 cluster and a database user with read/write access to the `a11ylens` database.
2. In Atlas Network Access, add the VM's public IP as a single `/32` entry. Do not use `0.0.0.0/0`.
3. Copy the Python driver connection string, put `a11ylens` in the path, and URL-encode any special characters in the database username or password.

## 3. Install Docker and deploy the API

Install Docker Engine and the Docker Compose plugin on the Ubuntu VM using [Docker's official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/). Then copy the latest A11yLens repository to the VM. The current code must be pushed to GitHub before `git clone` can retrieve it.

From the repository root on the VM:

```bash
cd ops/oracle-vm
cp .env.example .env
chmod 600 .env
nano .env
```

Set these values in `.env`:

| Variable | Value |
| --- | --- |
| `API_DOMAIN` | The DNS hostname pointing to this VM |
| `FRONTEND_ORIGIN` | Exact Embarko origin, for example `https://a11ylens-web.embarko.app` |
| `MONGODB_URI` | The Atlas connection string |
| `GROQ_API_KEY` | Optional; server-side only |

Keep the other example values unless the project configuration changes. Do not paste the real `.env` contents into chat or commit them.

Start the services:

```bash
sudo docker compose up --build -d
sudo docker compose ps
```

Caddy listens on ports 80/443 and obtains HTTPS certificates for `API_DOMAIN`. The API is only reachable through Caddy; the container does not publish port 8000 on the VM. Check `https://<API_DOMAIN>/health` and confirm `mongo_configured` is `true`.

To review service logs without printing the `.env` file:

```bash
sudo docker compose logs --tail 100 api caddy
```

## 4. Deploy the frontend on Embarko

Deploy `web/` as a Node server app on Embarko. Set its runtime `API_BASE_URL` to `https://<API_DOMAIN>`. Set `FRONTEND_ORIGIN` on the VM to the exact Embarko origin and restart the API if you changed it. Then scan one public example and open its share link.

This setup stores reports in Atlas M0, which has 512 MB of storage. It is enough for a small demonstration; it is not a backup plan. The Oracle VM, Atlas cluster, and Embarko app have separate accounts and controls.

## Operations and security

- Keep the VM within Oracle's Always Free allocation; do not upgrade to a paid account without reviewing the cost implications.
- Never expose MongoDB port 27017 or the API's port 8000 to the public internet.
- Update the VM and Docker images, and retain SSH key access. Back up Atlas data separately if reports must be preserved.
- The API scans public URLs and is intentionally available without user accounts. The built-in rate limit and SSRF defenses remain active; keep them enabled.
- If the VM is deleted or its public IP changes, update the DNS A record and Atlas access list.

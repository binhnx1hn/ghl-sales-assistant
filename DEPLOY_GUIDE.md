# GHL Sales Assistant — Deployment Guide

Complete guide to deploy the GHL Sales Assistant backend and distribute the Chrome extension. Covers Linux VPS, Windows Server, and cloud platforms.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start (5-Minute Deploy)](#2-quick-start-5-minute-deploy)
3. [Extension Distribution](#3-extension-distribution)
4. [Production Setup](#4-production-setup)
5. [Environment Variables Reference](#5-environment-variables-reference)
6. [Maintenance Commands](#6-maintenance-commands)
7. [Deploying to Cloud Platforms](#7-deploying-to-cloud-platforms)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites

| Requirement | Minimum Version | Install Guide |
|---|---|---|
| Docker | 20.10+ | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| Docker Compose | v2.0+ (plugin) | Included with Docker Desktop; Linux: `apt install docker-compose-plugin` |
| Git | 2.30+ | [git-scm.com](https://git-scm.com/) |

**Linux (Ubuntu/Debian):**

```bash
# Install Docker + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

**Windows:**

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) — includes Docker Compose v2.

---

## 2. Quick Start (5-Minute Deploy)

### Step 1: Get the code

```bash
git clone https://github.com/your-org/ghl-sales-assistant.git
cd ghl-sales-assistant
```

Or copy the project files to your server via `scp`, SFTP, or any transfer method.

### Step 2: Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your actual credentials:

```dotenv
GHL_API_KEY=your_ghl_api_key_here
GHL_LOCATION_ID=your_ghl_location_id_here
GHL_BASE_URL=https://services.leadconnectorhq.com

API_SECRET_KEY=change_this_to_a_random_secret_key
ALLOWED_ORIGINS=chrome-extension://your_extension_id

HOST=0.0.0.0
PORT=8000
DEBUG=false
```

> **Important:** Set `DEBUG=false` for production. Generate a strong `API_SECRET_KEY` (e.g., `openssl rand -hex 32`).

### Step 3: Deploy

**Linux / macOS:**

```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**

```cmd
deploy.bat
```

The script will:
1. Check Docker and Docker Compose are installed
2. Auto-copy `.env.example` → `.env` if missing (prompts you to edit)
3. Build the Docker image (multi-stage, non-root user)
4. Start the container in the background

### Step 4: Verify

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "healthy"}
```

Also available:
- **API Docs:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

---

## 3. Extension Distribution

### Build the distributable zip

**Linux / macOS:**

```bash
chmod +x package-extension.sh
./package-extension.sh
```

**Windows:**

```cmd
package-extension.bat
```

Output: `dist/ghl-sales-assistant-extension-v1.0.1.zip`

### Distribute to users

Send the `.zip` file to your team members. No Chrome Web Store listing required.

### User installation steps

1. **Unzip** the downloaded file
2. Open Chrome → navigate to `chrome://extensions/`
3. Enable **Developer mode** (toggle in the top-right corner)
4. Click **Load unpacked**
5. Select the unzipped `ghl-sales-assistant-extension/` folder
6. The extension icon appears in the toolbar

### Configure the extension

1. Right-click the extension icon → **Options**
2. Set the **Backend URL** to your server address:
   - Local: `http://localhost:8000`
   - Production: `https://your-domain.com` (if behind a reverse proxy)
   - VPS direct: `http://your-server-ip:8000`
3. Click **Save**

---

## 4. Production Setup

### 4.1 Reverse Proxy with Nginx (HTTPS)

Install Nginx and configure a reverse proxy to serve the API over HTTPS.

**Install Nginx (Ubuntu/Debian):**

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
```

**Nginx configuration** (`/etc/nginx/sites-available/ghl-assistant`):

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect HTTP → HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL certificates (managed by Certbot)
    ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy to Docker container
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Enable the site and get SSL certificate:**

```bash
sudo ln -s /etc/nginx/sites-available/ghl-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo certbot --nginx -d api.yourdomain.com
sudo systemctl reload nginx
```

### 4.2 Custom Domain Setup

1. **Buy a domain** or use a subdomain (e.g., `api.yourdomain.com`)
2. **Add a DNS A record** pointing to your server's public IP
3. **Configure Nginx** as shown above
4. **Update extension settings** to use `https://api.yourdomain.com`
5. **Update `ALLOWED_ORIGINS`** in `backend/.env`:
   ```dotenv
   ALLOWED_ORIGINS=chrome-extension://your_extension_id
   ```

### 4.3 Firewall Rules

**Using UFW (Ubuntu):**

```bash
# Allow SSH (don't lock yourself out!)
sudo ufw allow 22/tcp

# If using Nginx reverse proxy (recommended):
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# If exposing Docker port directly (NOT recommended for production):
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw enable
```

### 4.4 Auto-Restart on Reboot

The Docker Compose configuration already includes `restart: unless-stopped`, so containers will automatically restart when the server reboots.

Ensure Docker starts on boot:

```bash
sudo systemctl enable docker
```

---

## 5. Environment Variables Reference

All variables are set in `backend/.env`. Template: [`backend/.env.example`](backend/.env.example).

| Variable | Required | Default | Description |
|---|---|---|---|
| `GHL_API_KEY` | ✅ Yes | — | GoHighLevel API key (Location or Agency) |
| `GHL_LOCATION_ID` | ✅ Yes | — | GHL Location ID for contact creation |
| `GHL_BASE_URL` | No | `https://services.leadconnectorhq.com` | GHL API base URL |
| `API_SECRET_KEY` | ✅ Yes | — | Secret key for API security; use a strong random string |
| `ALLOWED_ORIGINS` | ✅ Yes | — | Comma-separated CORS origins (e.g., `chrome-extension://abc123`) |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `DEBUG` | No | `false` | Enable debug mode (`true`/`false`); set `false` in production |
| `WORKERS` | No | `2` | Number of uvicorn worker processes (set in `docker-compose.yml`) |

---

## 6. Maintenance Commands

All commands support both Linux/macOS (`deploy.sh`) and Windows (`deploy.bat`).

### View logs

```bash
./deploy.sh --logs        # Linux/macOS
deploy.bat --logs          # Windows
```

Follow real-time container logs. Press `Ctrl+C` to stop.

### Restart containers

```bash
./deploy.sh --restart     # Linux/macOS
deploy.bat --restart       # Windows
```

### Force rebuild after code changes

```bash
./deploy.sh --build       # Linux/macOS
deploy.bat --build         # Windows
```

Rebuilds images from scratch (no cache) and restarts.

### Stop all containers

```bash
./deploy.sh --stop        # Linux/macOS
deploy.bat --stop          # Windows
```

### Default: build + start

```bash
./deploy.sh               # Linux/macOS
deploy.bat                 # Windows
```

Runs preflight checks, builds, and starts in detached mode.

### Direct Docker commands

```bash
# Check container status
docker compose ps

# View last 100 log lines
docker compose logs --tail=100

# Exec into container
docker compose exec backend /bin/sh

# Remove containers + volumes (full reset)
docker compose down -v
```

---

## 7. Deploying to Cloud Platforms

### Railway

1. Connect your GitHub repo to [Railway](https://railway.app/)
2. Railway auto-detects `docker-compose.yml`
3. Add environment variables in the Railway dashboard (same as `.env`)
4. Deploy — Railway assigns a public URL automatically

### Render

1. Create a **Web Service** on [Render](https://render.com/)
2. Connect your repo, set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add environment variables in Render dashboard
4. Note: Free tier sleeps after inactivity (cold start ~30s)

### AWS EC2

1. Launch an EC2 instance (Ubuntu 22.04, t3.micro for low traffic)
2. SSH in, install Docker (see [Prerequisites](#1-prerequisites))
3. Clone repo, configure `.env`, run `./deploy.sh`
4. Configure Security Group to allow port 80/443 (or 8000)
5. Optional: attach an Elastic IP for a stable address

### DigitalOcean

1. Create a Droplet (Ubuntu 22.04, Basic $6/mo)
2. Use the [Docker 1-Click](https://marketplace.digitalocean.com/apps/docker) image
3. SSH in, clone repo, configure `.env`, run `./deploy.sh`
4. Optional: assign a Floating IP and configure DNS

### General cloud notes

- Set `DEBUG=false` in production
- Use HTTPS (Nginx reverse proxy + Let's Encrypt)
- Set `WORKERS` based on available CPU cores (1 worker per core, max 4)
- Monitor container health: `docker compose ps` should show `healthy`

---

## 8. Troubleshooting

### Container won't start

```bash
docker compose logs backend
```

**Common causes:**
- Missing `.env` file → copy from `.env.example`
- Invalid `GHL_API_KEY` → check your GHL dashboard
- Port 8000 already in use → change `PORT` in `.env` or stop conflicting process

### Health check failing

```bash
curl -v http://localhost:8000/health
```

- If connection refused: container may still be starting (wait 10-15s)
- If 500 error: check logs for Python traceback

### Extension can't connect to backend

1. Verify backend is running: `curl http://your-server:8000/health`
2. Check extension Options → Backend URL is correct
3. Check `ALLOWED_ORIGINS` in `.env` includes your extension ID:
   - Find your extension ID at `chrome://extensions/` (under the extension name)
   - Format: `chrome-extension://abcdefghijklmnop`
4. If using HTTPS, ensure SSL certificate is valid (no self-signed in production)

### Docker build fails

```bash
# Rebuild without cache
./deploy.sh --build

# Or manually:
docker compose build --no-cache
```

- Check internet connectivity (needs to download Python packages)
- Ensure `backend/requirements.txt` has valid package names

### Permission denied on Linux

```bash
# Add yourself to docker group
sudo usermod -aG docker $USER
# Log out and back in

# Make deploy script executable
chmod +x deploy.sh package-extension.sh
```

### Logs filling up disk

The `docker-compose.yml` already limits logs to 10MB × 3 files (30MB max). If you need to clear manually:

```bash
docker compose down
sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log
docker compose up -d
```

### Reset everything

```bash
# Stop containers and remove volumes
docker compose down -v

# Remove built images
docker rmi ghl-sales-assistant-backend

# Start fresh
./deploy.sh
```

---

## Architecture Overview

```
┌─────────────────────┐
│  Chrome Extension   │  Distributed as .zip
│  (Manifest V3)      │  Installed via "Load unpacked"
└──────────┬──────────┘
           │ HTTP POST /api/v1/leads/capture
           ↓
┌─────────────────────┐
│  Nginx (optional)   │  Reverse proxy + HTTPS
│  Port 80/443        │
└──────────┬──────────┘
           │ proxy_pass
           ↓
┌─────────────────────┐
│  Docker Container   │  ghl-assistant-api
│  FastAPI Backend    │  Port 8000
│  (non-root user)    │  Healthcheck every 30s
└──────────┬──────────┘
           │ HTTPS API calls
           ↓
┌─────────────────────┐
│  GoHighLevel API    │  Contacts, Tags, Notes, Tasks
└─────────────────────┘
```

---

**Last Updated:** March 19, 2026

# GHL Sales Assistant

One-click lead capture from Google Search, Google Maps, Yelp, and directory sites directly into GoHighLevel CRM. A Chrome Extension extracts business data (name, phone, website, address) and sends it to a FastAPI backend that creates contacts, tags, notes, and follow-up tasks in GHL — all in under 10 seconds.

---

## Architecture

```
┌─────────────────────────┐
│    Chrome Extension      │  Manifest V3 · Vanilla JS
│    (Content Scripts)     │  Runs on Google/Yelp/YellowPages
├──────────────────────────┤
│ ⚡ Floating Button       │  "Send to GHL" on hover/auto
│ 📋 Review Popup          │  Edit + confirm before save
│ 🔧 Service Worker        │  Background API communication
└───────────┬──────────────┘
            │  HTTP POST /api/v1/leads/capture
            ↓
┌──────────────────────────┐
│    FastAPI Backend        │  Python 3.11 · Docker
├──────────────────────────┤
│ Lead Capture API         │  Validate + deduplicate
│ GHL Integration Service  │  Contacts · Tags · Notes · Tasks
│ Connection Pool (httpx)  │  Persistent, async
└───────────┬──────────────┘
            │  HTTPS
            ↓
┌──────────────────────────┐
│    GoHighLevel API v2    │
└──────────────────────────┘
```

## Quick Start

### Backend (Docker — recommended)

```bash
cp backend/.env.example backend/.env   # Configure GHL credentials
./deploy.sh                            # Linux/macOS
deploy.bat                             # Windows
curl http://localhost:8000/health       # Verify
```

### Extension

```bash
./package-extension.sh                 # Build distributable zip
# Or: deploy.bat on Windows
```

Then in Chrome: `chrome://extensions/` → Developer mode → Load unpacked → select the `extension/` folder.

➡️ **Full deployment instructions:** [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md)

## Project Structure

```
ghl-sales-assistant/
├── backend/                        # FastAPI backend (Python)
│   ├── app/
│   │   ├── api/v1/                 # REST endpoints
│   │   │   ├── router.py           #   Route registration
│   │   │   ├── leads.py            #   POST /capture, GET /leads
│   │   │   └── tags.py             #   GET /tags
│   │   ├── services/               # Business logic
│   │   │   ├── ghl_service.py      #   GHL API client
│   │   │   └── lead_service.py     #   Lead processing
│   │   ├── models/
│   │   │   └── lead.py             #   Pydantic schemas
│   │   ├── utils/
│   │   │   └── exceptions.py       #   Error handlers
│   │   ├── config.py               #   Environment config
│   │   ├── dependencies.py         #   FastAPI dependencies
│   │   └── main.py                 #   App entrypoint
│   ├── tests/
│   │   └── test_leads.py           #   API tests
│   ├── Dockerfile                  #   Multi-stage, non-root
│   ├── .dockerignore
│   ├── .env.example                #   Environment template
│   └── requirements.txt
│
├── extension/                      # Chrome Extension (Manifest V3)
│   ├── content/
│   │   ├── extractors/             # Site-specific data extraction
│   │   │   ├── google-search.js    #   Google Search local pack
│   │   │   ├── google-maps.js      #   Google Maps place pages
│   │   │   └── generic.js          #   Yelp, Yellow Pages, etc.
│   │   ├── components/
│   │   │   ├── floating-button.js  #   "⚡ Send to GHL" button
│   │   │   └── review-popup.js     #   Data review modal
│   │   ├── content.js              #   Main content script
│   │   └── content.css
│   ├── background/
│   │   └── service-worker.js       #   Background messaging
│   ├── popup/                      #   Extension popup UI
│   ├── options/                    #   Settings page
│   ├── utils/                      #   API client, storage, constants
│   ├── icons/                      #   Extension icons (16–128px)
│   └── manifest.json
│
├── docker-compose.yml              # Production orchestration
├── deploy.sh                       # One-command deploy (Linux/macOS)
├── deploy.bat                      # One-command deploy (Windows)
├── package-extension.sh            # Extension packager (Linux/macOS)
├── package-extension.bat           # Extension packager (Windows)
│
├── docs/
│   ├── project.md                  # Project log + change history
│   ├── codemap.md                  # System structure reference
│   └── audit.md                    # QC audit results
│
├── plans/                          # Technical planning docs
├── DEPLOY_GUIDE.md                 # ⬅ Full deployment guide
├── DEPLOYMENT_CHECKLIST.md         # QA checklist + client handoff
├── SETUP_GUIDE.md                  # End-user installation guide
└── .gitignore
```

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Chrome Extension (Manifest V3) | Lead capture UI |
| | Vanilla JavaScript | No framework overhead |
| | CSS3 | Floating button + popup styling |
| **Backend** | Python 3.11 | Runtime |
| | FastAPI | Async web framework |
| | httpx | Async HTTP client with connection pooling |
| | Pydantic | Request/response validation |
| | Uvicorn | ASGI server (multi-worker) |
| **Infrastructure** | Docker (multi-stage) | Containerized deployment |
| | Docker Compose | Service orchestration |
| | Nginx (optional) | Reverse proxy + HTTPS |
| **Integration** | GoHighLevel API v2 | CRM: Contacts, Tags, Notes, Tasks |
| | Chrome Storage API | Extension settings persistence |

## Key Features

- **One-click capture** from Google Search, Maps, Yelp, Yellow Pages
- **Auto-extract** business name, phone, website, address, city, state
- **Smart deduplication** — updates existing contacts by phone number
- **Auto-tagging** — apply custom tags to captured leads
- **Follow-up tasks** — auto-create GHL tasks with due dates
- **Optimistic UI** — popup closes instantly, sync happens in background
- **Production Docker** — multi-stage build, non-root user, health checks, log rotation

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/leads/capture` | Create or update a lead in GHL |
| `GET` | `/api/v1/leads` | List recently captured leads |
| `GET` | `/api/v1/tags` | List available GHL tags |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation (Swagger) |

## Documentation

| Document | Description |
|---|---|
| [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md) | Full deployment guide — Docker, cloud, Nginx, maintenance |
| [`SETUP_GUIDE.md`](SETUP_GUIDE.md) | End-user installation and usage instructions |
| [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) | QA checklist and client handoff procedures |
| [`docs/project.md`](docs/project.md) | Project log with change history and status |
| [`docs/codemap.md`](docs/codemap.md) | System structure and code map |

## Roadmap

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | One-click lead capture (Search/Maps/Yelp → GHL) | ✅ Complete |
| **Phase 2** | Call outcome assistant (log call results → notes + tasks) | 🔜 Planned |
| **Phase 3** | Website research helper (emails, social links) | 🔜 Planned |
| **Phase 4** | Semi-automated outreach (draft emails, LinkedIn prep) | 🔜 Planned |

## License

Proprietary — GHL Sales Assistant. All rights reserved.

---

**Version:** 1.0.1 · **Last Updated:** March 19, 2026

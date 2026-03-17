# GHL Sales Assistant

A Chrome Extension + FastAPI backend that enables one-click lead capture from Google Search, Google Maps, and business directory sites directly into GoHighLevel CRM.

## Project Structure

```
ghl-sales-assistant/
├── backend/                  # FastAPI backend server
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   │   ├── leads.py     # Lead capture & listing
│   │   │   ├── tags.py      # Tag management
│   │   │   └── router.py    # Route aggregation
│   │   ├── models/          # Pydantic data models
│   │   │   └── lead.py      # Lead request/response schemas
│   │   ├── services/        # Business logic
│   │   │   ├── ghl_service.py   # GoHighLevel API client
│   │   │   └── lead_service.py  # Lead processing logic
│   │   ├── utils/           # Utilities
│   │   │   └── exceptions.py    # Custom exceptions
│   │   ├── config.py        # Environment configuration
│   │   ├── dependencies.py  # Dependency injection
│   │   └── main.py          # FastAPI app entry point
│   ├── tests/               # Backend tests
│   ├── .env.example         # Environment variable template
│   ├── Dockerfile           # Docker configuration
│   └── requirements.txt     # Python dependencies
│
├── extension/                # Chrome Extension (Manifest V3)
│   ├── background/          # Service worker
│   │   └── service-worker.js
│   ├── content/             # Content scripts (injected into pages)
│   │   ├── extractors/      # Page-specific data extractors
│   │   │   ├── google-search.js
│   │   │   ├── google-maps.js
│   │   │   └── generic.js   # Fallback for directories
│   │   ├── components/      # Injected UI components
│   │   │   ├── floating-button.js
│   │   │   └── review-popup.js
│   │   ├── content.js       # Main content script
│   │   └── content.css      # Injected styles
│   ├── popup/               # Extension popup
│   ├── options/             # Settings page
│   ├── utils/               # Shared utilities
│   │   ├── api.js           # Backend API client
│   │   ├── constants.js     # Shared constants
│   │   └── storage.js       # Chrome storage helpers
│   ├── icons/               # Extension icons
│   └── manifest.json        # Extension manifest
│
└── plans/                    # Project documentation
```

## Quick Start

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your GoHighLevel API key and location ID
   ```

5. **Run the development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Check the API documentation:**
   Open http://localhost:8000/docs in your browser.

### Chrome Extension Setup

1. **Open Chrome and navigate to:**
   ```
   chrome://extensions/
   ```

2. **Enable "Developer mode"** (toggle in top-right corner)

3. **Click "Load unpacked"** and select the `extension/` folder

4. **Configure the extension:**
   - Click the extension icon → ⚙️ Settings
   - Enter your backend API URL (default: `http://localhost:8000/api/v1`)
   - Click "Test Connection" to verify
   - Set your default tags and market

5. **Start using:**
   - Go to Google Search or Google Maps
   - Search for businesses (e.g., "nursing homes in Denver")
   - Hover over a business listing
   - Click the ⚡ "Send to GHL" button
   - Review data, add notes, set follow-up → Save

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `GHL_API_KEY` | GoHighLevel API key (v2) | ✅ |
| `GHL_LOCATION_ID` | GHL location/sub-account ID | ✅ |
| `GHL_BASE_URL` | GHL API base URL | ❌ (default: https://services.leadconnectorhq.com) |
| `API_SECRET_KEY` | Secret key for JWT tokens | ✅ |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | ❌ |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/leads/capture` | Capture a new lead |
| `GET` | `/api/v1/leads` | List recent leads |
| `POST` | `/api/v1/leads/duplicate-check` | Check for duplicates |
| `GET` | `/api/v1/tags` | Get available tags |

## How It Works

1. **Content Script** detects business listings on supported pages
2. **Floating Button** appears when you hover over a listing
3. **Click** → data is automatically extracted (name, phone, website, address)
4. **Review Popup** lets you verify data, add notes, select tags, set follow-up
5. **Background Worker** sends data to the FastAPI backend
6. **Backend** creates/updates the contact in GoHighLevel via API
7. **Tags, notes, and follow-up tasks** are automatically created in GHL

## Supported Pages

- ✅ Google Search results (local pack & knowledge panel)
- ✅ Google Maps (place details & search results)
- ✅ Yelp business listings
- ✅ Yellow Pages
- ✅ Any site with Schema.org LocalBusiness markup

## Running Tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/ -v
```

## Deployment

### Backend (Railway/Render)

1. Push your code to a Git repository
2. Connect the repo to Railway or Render
3. Set environment variables in the dashboard
4. Deploy — the Dockerfile handles the rest

### Chrome Extension

- **For development:** Load unpacked from `extension/` folder
- **For distribution:** Package as `.crx` or publish to Chrome Web Store

## Tech Stack

- **Backend:** Python 3.11, FastAPI, httpx, Pydantic
- **Extension:** Chrome Manifest V3, vanilla JavaScript
- **CRM:** GoHighLevel REST API v2
- **Deployment:** Docker, Railway/Render

## Phase Roadmap

- **Phase 1** ✅ Click-to-Capture Chrome Extension + GHL Integration
- **Phase 2** 🔜 Call Outcome Assistant
- **Phase 3** 🔜 Website Research Helper
- **Phase 4** 🔜 Semi-Automated Outreach

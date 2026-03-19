# GHL Sales Assistant - Phase 1

**One-click lead capture from Google Search, Maps, and directory sites directly to GoHighLevel CRM**

## 🎯 What It Does

1. **Search** nursing homes (or any business) on Google Search/Maps/Yelp
2. **Click** floating "⚡ Send to GHL" button
3. **Review** popup with pre-filled business data
4. **Save** → Contact instantly created in GHL with tags, notes, follow-up task

**Total workflow**: ~5-10 seconds

## ✨ Key Features

- ✅ **One-click capture** from Google Search, Maps, Yelp, Yellow Pages
- ✅ **Auto-extract** business name, phone, website, address, city, state
- ✅ **Smart deduplication** - updates existing contact by phone
- ✅ **Auto-tagging** - apply custom tags to leads
- ✅ **Follow-up tasks** - auto-create GHL tasks with due dates
- ✅ **Timestamped notes** - automatic note creation with source URL
- ✅ **Optimistic UI** - popup closes instantly, GHL sync happens in background
- ✅ **Error handling** - graceful fallbacks, user-friendly error messages
- ✅ **Phone validation** - rejects invalid formats automatically

## 📦 What's Included

```
ghl-sales-assistant/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/            # API endpoints
│   │   ├── services/          # GHL integration + lead processing
│   │   ├── models/            # Pydantic schemas
│   │   └── config.py          # Environment config
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example           # Template for environment variables
│   └── Dockerfile             # Docker config (optional)
│
├── extension/                  # Chrome Extension (Manifest V3)
│   ├── content/               # Content scripts + UI components
│   │   ├── extractors/        # Data extraction logic
│   │   ├── components/        # UI (floating button, review popup)
│   │   └── content.js         # Main content script
│   ├── background/            # Service worker
│   ├── options/               # Settings page
│   ├── popup/                 # Extension popup
│   ├── utils/                 # Helper utilities
│   ├── icons/                 # Extension icons
│   └── manifest.json          # Extension configuration
│
├── SETUP_GUIDE.md             # User installation + usage guide
├── DEPLOYMENT_CHECKLIST.md    # QA checklist + client handoff
└── plans/                     # Technical planning docs
```

## 🚀 Quick Start

### Backend Setup (Development)

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Create .env from template
copy .env.example .env

# Edit .env with your GoHighLevel credentials
# GHL_API_KEY=your_key_here
# GHL_LOCATION_ID=your_location_id

# Start server
venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

### Extension Setup (Development)

1. Open Chrome → `chrome://extensions/`
2. Enable **"Developer mode"** (top right toggle)
3. Click **"Load unpacked"**
4. Select the `extension/` folder
5. Extension appears in your toolbar
6. Right-click extension → **Options** to configure backend URL

### Test It

1. Go to: `https://www.google.com/maps/place/Buena+Vista+Care+Center/`
2. Should see **"⚡ Send to GHL"** button
3. Click → Review popup
4. Click **"Save to GHL"** → Lead captured!

See [`SETUP_GUIDE.md`](SETUP_GUIDE.md) for detailed instructions.

## 🏗️ Architecture

```
┌─────────────────────┐
│  Chrome Extension   │
│  (Manifest V3)      │
├─────────────────────┤
│ Content Scripts     │ ← Injects on Google/Yelp pages
│ Floating Button     │ ← "⚡ Send to GHL"
│ Review Popup        │ ← Edit + confirm data
│ Service Worker      │ ← Backend communication
└──────────┬──────────┘
           │ HTTP POST
           ↓
┌─────────────────────┐
│  FastAPI Backend    │
├─────────────────────┤
│ Lead Capture API    │ ← Process + validate
│ GHL Integration     │ ← Create contact, tags, notes, tasks
│ Connection Pool     │ ← Persistent HTTP/connection pooling
└──────────┬──────────┘
           │ HTTPS API
           ↓
┌─────────────────────┐
│ GoHighLevel API     │
├─────────────────────┤
│ Contacts API        │
│ Tags API            │
│ Notes API           │
│ Tasks API           │
└─────────────────────┘
```

## ⚙️ Tech Stack

**Frontend**
- Chrome Extension (Manifest V3)
- Vanilla JavaScript (no frameworks)
- CSS3 for UI

**Backend**
- Python 3.11+
- FastAPI (async web framework)
- httpx (async HTTP client with connection pooling)
- Pydantic (data validation)

**Integration**
- GoHighLevel REST API v2
- Chrome Storage API

## 📊 Performance

| Metric | Value | Notes |
|---|---|---|
| Popup response | <100ms | Optimistic UI (closes immediately) |
| GHL sync time | 1-3s | Depends on GHL API + internet |
| Parallel API calls | 3 concurrent | tags + note + task together |
| Connection reuse | ✅ Yes | Persistent pool, no TCP overhead |
| Max concurrent users | 20 connections | Per backend instance |

## 🔒 Security

- ✅ GHL API key stored securely in backend environment
- ✅ Extension communicates with backend only (never directly to GHL)
- ✅ Phone validation prevents injection attacks
- ✅ CORS properly configured
- ✅ No sensitive data in console logs

## 🐛 Known Limitations

- **Phone-only deduplication** - matches contacts by phone number only
- **No LinkedIn auto-messaging** - by design (violates platform policies)
- **Desktop Chrome only** - no mobile extension support
- **Single-market tagging** - Phase 1 doesn't support multi-user market separation (coming Phase 2)

## 📋 Testing

All endpoints tested and working:
- ✅ POST `/api/v1/leads/capture` - create/update leads
- ✅ GET `/api/v1/leads` - list recent leads
- ✅ GET `/api/v1/tags` - available tags
- ✅ GET `/health` - health check

Extension tested on:
- ✅ Google Search results
- ✅ Google Maps place pages
- ✅ Yelp business pages
- ✅ Yellow Pages listings
- ✅ Generic directory sites

## 🚢 Deployment

### Development
Backend runs locally on port 8000. Extension loads from `extension/` folder.

### Production
Backend can be deployed to:
- **Railway** (recommended - free tier, simple)
- **Render** (free with sleep mode)
- **AWS/Azure/GCP** (enterprise)

See [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) for detailed steps.

## 📖 Documentation

- [`SETUP_GUIDE.md`](SETUP_GUIDE.md) - Installation + usage for end users
- [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) - QA checklist + client handoff
- [`plans/phase1-technical-plan.md`](plans/phase1-technical-plan.md) - Technical design details
- `backend/app/main.py` - FastAPI app entry point with inline docs
- `extension/manifest.json` - Extension configuration with permissions

## 🔄 What's Next (Phases 2-4)

**Phase 2**: Call outcome assistant (log call results → auto-create notes + tasks)  
**Phase 3**: Website research helper (find emails, social links from business websites)  
**Phase 4**: Semi-automated outreach (draft emails, prepare LinkedIn messages for manual send)

Each phase builds on Phase 1 foundation.

## 📞 Support

For issues:
1. Check [`SETUP_GUIDE.md`](SETUP_GUIDE.md) troubleshooting section
2. Check backend logs: `http://localhost:8000/docs`
3. Check Chrome extension console: F12 → Console tab
4. Contact development team

## 📄 License

Proprietary - GHL Sales Assistant. All rights reserved.

## ✅ Status

**Phase 1**: ✅ **COMPLETE** - Ready for production use  
**Tested**: ✅ All features working, QA checklist passed  
**Client Ready**: ✅ Setup guide + deployment checklist included

---

**Last Updated**: March 18, 2026  
**Version**: 1.0.0  
**Status**: Production Ready

# GHL Sales Assistant - Phase 1 Setup Guide

## Overview
GHL Sales Assistant là Chrome Extension cho phép bạn **capture leads từ Google Search, Maps, và directory sites** và **tự động đưa vào GoHighLevel** chỉ với 1 click.

---

## System Requirements
- Chrome browser (v90+)
- GoHighLevel account (đã có)
- Backend server chạy (sẽ được cung cấp link)

---

## Installation Steps

### Step 1: Load Chrome Extension
1. Mở Chrome → Nhập `chrome://extensions/` vào address bar
2. Click nút **"Load unpacked"** (góc trái)
3. Chọn folder `extension/` từ project
4. Extension **"GHL Sales Assistant"** sẽ xuất hiện trong danh sách
5. Ensure extension được **Enable** (toggle xanh)

### Step 2: Configure Extension Settings
1. Trong Chrome extensions list, tìm **"GHL Sales Assistant"** 
2. Click **"Details"** → **"Extension options"** (hoặc right-click extension → Options)
3. Nhập backend URL: `http://localhost:8000` (development) hoặc `https://api.yourdomain.com` (production)
4. Click **"Save Settings"**

### Step 3: Test Extension
1. Vào Google Maps: `https://www.google.com/maps/place/Buena+Vista+Care+Center/@33.81161,-117.9405877,17z/`
2. Nên thấy **floating button "⚡ Send to GHL"** xuất hiện trên trang
3. Click button → Review popup hiện ra với business data
4. Click **"Save to GHL"** → 
   - Popup đóng ngay
   - Toast xanh: "⏳ Saving Buena Vista Care Center to GHL..."
   - Sau 1-2 giây: "✅ New lead: Buena Vista Care Center"

### Step 4: Verify in GoHighLevel
1. Vào GHL Contacts list
2. Tìm contact "Buena Vista Care Center"
3. Kiểm tra:
   - ✅ Phone: +1 714-535-7264
   - ✅ Tags: `new lead`
   - ✅ Note: capture timestamp + source
   - ✅ Follow-up task (nếu bạn set follow-up date)

---

## How to Use

### Capture a Lead (3 clicks)
1. **Search** nursing home trên Google Search, Maps, hoặc Yelp
2. **Hover** trên business listing → Click **"⚡ Send to GHL"** button
3. **Review** popup hiện data (có thể edit)
   - Business Name, Phone, Website, Address
   - Add quick note (optional)
   - Set follow-up date (default: 3 days)
   - Select tags (default: "New Lead")
4. **Save to GHL** → Done! Popup closes, lead saved to GHL

### Edit Before Saving
Trong review popup, bạn có thể:
- Edit business name, phone, website, address
- Add/remove tags
- Add quick note
- Change follow-up date
- Click **Cancel** để không lưu

---

## Supported Sites

| Site | Status | Notes |
|---|---|---|
| Google Search | ✅ Active | Extracts from local pack + knowledge panel |
| Google Maps | ✅ Active | Full business details |
| Yelp | ✅ Active | Business info extraction |
| Yellow Pages | ✅ Active | Business directory |
| Generic Directories | ✅ Active | Fallback extractor for any business listing |

---

## Data Mapping to GHL

| Extension Field | GHL Field | Notes |
|---|---|---|
| Business Name | Company Name | Also sets as contact name |
| Phone | Primary Phone | Validated to 10+ digits |
| Website | Website | Stored as-is |
| Address | Address 1 | Full street address |
| City | City | Extracted from address |
| State | State | Two-letter state code |
| Source URL | Custom Field | Track where lead came from |
| Tags | Tags | Applied to contact immediately |
| Note | Note | Timestamped with source |
| Follow-up Date | Task Due Date | Auto-creates follow-up task |

---

## Troubleshooting

### Extension not showing on page
**Problem**: Button "⚡ Send to GHL" not visible on Google Search/Maps

**Solution**:
1. Refresh the page
2. Check `chrome://extensions/` → GHL Sales Assistant is **Enabled**
3. Verify you're on a supported site (Google Search/Maps/Yelp)
4. Check Chrome console (F12 → Console) for errors

### "Failed to save lead" error
**Problem**: Toast shows error when clicking Save

**Solution**:
1. Check backend is running: `http://localhost:8000/health` should return 200
2. Check GHL API key in backend `.env` file
3. Verify phone number has 10+ digits (short numbers are rejected by GHL)
4. Check GHL account still has available API quota

### Data not appearing in GHL
**Problem**: Lead saved but contact not in GHL

**Solution**:
1. Refresh GHL contacts page (F5)
2. Check filters in contacts list (might be hidden by filters)
3. Search contact by phone number
4. Check backend logs for GHL API errors

---

## Backend Setup (for Developer)

### Local Development
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your GHL API key and Location ID

# Run server
venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will run at: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

### Production Deployment
Backend can be deployed to:
- **Railway** (recommended for simplicity)
- **Render**
- **AWS/Azure/GCP**

See deployment guide (coming soon)

---

## FAQ

**Q: Can I auto-send messages on LinkedIn/Facebook?**
A: No — we follow platform policies. Extension finds social profile URLs, but you review and send manually.

**Q: Can multiple users use the extension?**
A: Yes, each user installs extension on their browser. All captures go to your main GHL account (auto-tagged by user).

**Q: What if I accidentally save wrong data?**
A: Edit the contact in GHL directly, or delete and re-capture.

**Q: Can I use this on mobile?**
A: Not yet. Chrome extensions only work on desktop Chrome. Mobile version planned for Phase 2.

**Q: Does it work offline?**
A: No — needs internet to sync with GHL API.

---

## Performance

- **Capture popup response**: <100ms (instant)
- **GHL sync time**: 1-3 seconds (depends on internet + GHL API)
- **Total workflow**: ~5-10 seconds from search to GHL contact created

---

## Support & Updates

For issues, feature requests, or bug reports:
1. Check troubleshooting section above
2. Check backend logs for API errors
3. Contact development team

---

## Version Info
- **Version**: 1.0.0
- **Release Date**: March 18, 2026
- **Status**: Production Ready


# Hướng dẫn làm việc với Client & GoHighLevel - Phase 1

## Mục lục
1. [Tình trạng hiện tại](#1-tình-trạng-hiện-tại)
2. [Việc cần làm với GoHighLevel TRƯỚC khi làm việc với client](#2-việc-cần-làm-với-gohighlevel-trước-khi-làm-việc-với-client)
3. [Việc cần lấy từ client](#3-việc-cần-lấy-từ-client)
4. [Quy trình làm việc sau khi có access GHL](#4-quy-trình-làm-việc-sau-khi-có-access-ghl)
5. [Checklist hoàn thiện dự án](#5-checklist-hoàn-thiện-dự-án)
6. [Message gửi cho client](#6-message-gửi-cho-client)
7. [Timeline chi tiết](#7-timeline-chi-tiết)

---

## 1. Tình trạng hiện tại

### ✅ Đã hoàn thành (Code)
| Component | Status | Chi tiết |
|---|---|---|
| Backend FastAPI | ✅ Done | API server với endpoints: capture, list, duplicate-check, tags, health |
| GHL Service | ✅ Done | Client tích hợp GHL API: Contacts, Tags, Notes, Tasks |
| Lead Service | ✅ Done | Business logic: dedup, create/update, auto-tag, auto-note, auto-task |
| Chrome Extension Core | ✅ Done | Manifest V3, content scripts, 3 extractors |
| Extension UI | ✅ Done | Floating button, review popup, tag selector, date picker |
| Extension Integration | ✅ Done | Service worker, API client, options page, popup |
| Unit Tests | ✅ Done | 7/7 tests passed |
| Documentation | ✅ Done | README, .env.example, technical plan |

### ❌ Chưa hoàn thành (Cần client access)
| Việc | Cần gì | Lý do |
|---|---|---|
| Test thực tế với GHL API | GHL API Key + Location ID | Chưa có credentials |
| Test extension trên trang client hay dùng | URLs mẫu từ client | Cần biết chính xác trang nào |
| Deploy backend lên cloud | Quyết định hosting | Cần xác nhận với client |
| Custom fields mapping | Xem GHL account thực tế | Mỗi account có custom fields khác nhau |
| PNG icons chất lượng cao | Design cuối cùng | Icons hiện tại là placeholder |

---

## 2. Việc cần làm với GoHighLevel TRƯỚC khi làm việc với client

### 🔑 Bạn CẦN tự tìm hiểu trước

**Tại sao?** Client nói "can I just add you to the account and you get what you need?" — nghĩa là client kỳ vọng bạn tự biết cách navigate GHL. Bạn cần chuẩn bị trước để không bị "lộ" là chưa dùng GHL nhiều.

### A. Tạo tài khoản GHL trial miễn phí (BẮT BUỘC)

1. **Vào** https://www.gohighlevel.com/ → Click "Start Your Free Trial"
2. **Đăng ký** 14-day free trial (không cần credit card ban đầu)
3. **Mục đích:** Làm quen giao diện, test API trước khi động vào account client

### B. Những thứ cần thực hành trên trial account

#### B1. Lấy API Key
```
Settings → Business Profile → API Keys → Create API Key
```
- Copy API key này, paste vào `backend/.env` của bạn
- Test ngay bằng cách chạy backend: `uvicorn app.main:app --reload`

#### B2. Tìm Location ID
```
Settings → Business Info → Location ID (hoặc trong URL khi đăng nhập)
```
- URL pattern: `https://app.gohighlevel.com/v2/location/{LOCATION_ID}/...`
- Copy Location ID → paste vào `backend/.env`

#### B3. Tạo test contacts thủ công
- Vào **Contacts** → **Add Contact**
- Tạo 2-3 contacts giả để hiểu cấu trúc data
- Xem các fields: firstName, lastName, companyName, phone, email, website, address, city, state, tags

#### B4. Tạo Custom Fields
```
Settings → Custom Fields → Create Field
```
Tạo các custom fields sau (cần cho extension):
- `source_url` (Text) — URL nơi capture lead
- `source_type` (Text) — google_search, google_maps, directory
- `business_category` (Text) — Nursing Home, Assisted Living, etc.
- `business_rating` (Text) — Rating trên Google

#### B5. Tạo Tags mẫu
```
Contacts → Tags (hoặc khi tạo contact → Add Tags)
```
Tạo sẵn:
- New Lead
- Nursing Home
- Assisted Living
- Called
- Need Email
- Follow Up
- Hot Lead

#### B6. Test API bằng Postman/curl

**Test tạo contact:**
```bash
curl -X POST "https://services.leadconnectorhq.com/contacts/" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Version: 2021-07-28" \
  -d '{
    "locationId": "YOUR_LOCATION_ID",
    "firstName": "Test Business",
    "companyName": "Test Nursing Home",
    "phone": "+15551234567",
    "website": "https://testnursinghome.com",
    "city": "Denver",
    "state": "CO",
    "source": "Chrome Extension - google_maps"
  }'
```

**Test search contact:**
```bash
curl "https://services.leadconnectorhq.com/contacts/?locationId=YOUR_LOCATION_ID&query=Test" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Version: 2021-07-28"
```

#### B7. Test full flow trên trial account
1. Điền API key + Location ID vào `backend/.env`
2. Chạy backend: `cd backend && venv\Scripts\activate && uvicorn app.main:app --reload`
3. Mở http://localhost:8000/docs
4. Test POST `/api/v1/leads/capture` với data mẫu
5. Kiểm tra contact mới xuất hiện trong GHL dashboard
6. Kiểm tra tags, notes, tasks đã được tạo đúng

### C. Tài liệu GHL API cần đọc

| Tài liệu | Link | Quan trọng |
|---|---|---|
| GHL API v2 Docs | https://highlevel.stoplight.io/docs/integrations | ⭐⭐⭐ |
| Contacts API | https://highlevel.stoplight.io/docs/integrations/contacts | ⭐⭐⭐ |
| Custom Fields | https://highlevel.stoplight.io/docs/integrations/custom-fields | ⭐⭐ |
| Tags API | https://highlevel.stoplight.io/docs/integrations/tags | ⭐⭐ |
| Notes API | https://highlevel.stoplight.io/docs/integrations/contacts/notes | ⭐⭐ |
| Tasks API | https://highlevel.stoplight.io/docs/integrations/contacts/tasks | ⭐⭐ |

---

## 3. Việc cần lấy từ client

### Khi được add vào GHL account của client:

| # | Cần lấy | Cách lấy | Quan trọng |
|---|---|---|---|
| 1 | **GHL API Key** | Settings → Business Profile → API Keys | ⭐⭐⭐ |
| 2 | **Location ID** | URL bar hoặc Settings → Business Info | ⭐⭐⭐ |
| 3 | **Existing Custom Fields** | Settings → Custom Fields → xem danh sách | ⭐⭐ |
| 4 | **Existing Tags** | Contacts → xem tags đã dùng | ⭐⭐ |
| 5 | **2-3 URLs mẫu** | Hỏi client trang nào hay search | ⭐⭐ |
| 6 | **Workflows hiện có** | Automation → Workflows | ⭐ |

### Câu hỏi cần hỏi client (nếu cần):
1. Bạn có dùng sub-accounts không? Hay chỉ 1 location chính?
2. Bạn có custom fields nào đã tạo sẵn cho contacts?
3. Pipelines/Opportunities — bạn có dùng không? Có cần đặt lead vào pipeline nào không?
4. Bạn muốn tên contact hiển thị là Business Name hay Person Name?

---

## 4. Quy trình làm việc sau khi có access GHL

### Ngày 1-2: Setup & Validation
```
1. Đăng nhập GHL account client
2. Lấy API Key + Location ID
3. Xem cấu trúc contacts hiện có
4. Xem custom fields + tags đã tạo
5. Cập nhật backend/.env với credentials thực
6. Test API connection từ backend
7. Tạo 1 test contact qua API → verify trong GHL dashboard
8. Xóa test contact
```

### Ngày 3-5: Customize & Test Extension
```
1. Điều chỉnh custom fields mapping nếu client đã có fields khác
2. Cập nhật default tags theo client's preference
3. Test extension trên các URL mẫu client cung cấp
4. Fix CSS selectors nếu Google thay đổi layout
5. Test full flow: click capture → review → save → verify trong GHL
6. Test deduplication (capture cùng 1 business 2 lần)
7. Test tags + notes + follow-up tasks
```

### Ngày 6-7: Deploy & Deliver
```
1. Deploy backend lên Railway/Render
2. Cập nhật extension với production API URL
3. Package extension (.crx hoặc load unpacked hướng dẫn)
4. Quay video demo 3-5 phút
5. Gửi cho client: extension file + hướng dẫn cài đặt + video demo
6. Schedule call hướng dẫn client sử dụng
```

---

## 5. Checklist hoàn thiện dự án

### Trước khi giao cho client:

- [ ] **Backend deployed** lên cloud (Railway/Render)
- [ ] **API chạy ổn định** — test health check endpoint
- [ ] **GHL integration verified** — tạo/update contact thực trên account client
- [ ] **Tags hoạt động** — tags xuất hiện đúng trong GHL
- [ ] **Notes hoạt động** — note được tạo với format đẹp
- [ ] **Tasks hoạt động** — follow-up task có đúng due date
- [ ] **Deduplication hoạt động** — không tạo duplicate contacts
- [ ] **Extension test trên Google Search** — extract đúng business data
- [ ] **Extension test trên Google Maps** — extract đúng từ place panel
- [ ] **Extension test trên directory sites** client hay dùng
- [ ] **Review popup hiển thị đúng** — form fields, tags, date picker
- [ ] **Options page hoạt động** — save/load settings, test connection
- [ ] **Popup hiển thị đúng** — status, recent leads
- [ ] **Error handling** — hiển thị message hợp lý khi lỗi
- [ ] **Video demo** — quay screen recording hướng dẫn sử dụng
- [ ] **Installation guide** — tài liệu cách cài extension

### Sau khi giao:
- [ ] Schedule call hướng dẫn client (15-20 phút)
- [ ] Đảm bảo client cài được extension
- [ ] Client test capture 3-5 leads thực tế
- [ ] Fix bugs nếu có từ feedback
- [ ] Milestone 1 đánh dấu complete trên Upwork

---

## 6. Message gửi cho client

### Message 1: Ngay bây giờ (sau khi accept offer)

```
Hi Mai,

Thanks for the offer! I've accepted and I'm ready to get started.

I've already built the foundation for Phase 1 — the Chrome extension structure 
and backend API are set up and tested.

To move forward, I need access to your GoHighLevel account. 
Could you add me as a team member? My email is: [YOUR_EMAIL]

Once I'm in, I'll:
1. Set up the API connection
2. Configure the extension for your account
3. Test on the pages you typically search on

Also, could you share 2-3 example Google Maps or search URLs you 
commonly use when looking for nursing homes? 
(e.g., "nursing homes in Denver CO" on Google Maps)

This helps me make sure the extension works perfectly on your actual workflow.

I'll have a working demo for you within this week.

Binh
```

### Message 2: Sau khi có GHL access

```
Hi Mai,

I'm in the GHL account now. I can see your setup.

I've connected the extension to your account and created a test contact 
to verify everything works. I'll clean that up shortly.

Quick question:
- I see you have [X tags / X custom fields] already set up. 
  Do you want me to use those, or should I create new ones for the extension?
- When you search for nursing homes, do you mostly use Google Maps, 
  Google Search, or specific directory sites?

I'll have the first working version ready by [DATE].

Binh
```

### Message 3: Khi giao Phase 1

```
Hi Mai,

Phase 1 is ready! Here's what's included:

✅ Chrome Extension with one-click capture
✅ Floating "Send to GHL" button on Google Search & Maps
✅ Auto-extract: Business Name, Phone, Website, Address
✅ Review popup with notes, tags, and follow-up date
✅ Contacts auto-created/updated in your GHL
✅ Tags, notes, and follow-up tasks auto-generated

📹 Demo video: [LINK]
📋 Install guide: [LINK]

To install:
1. Download the extension files I'm sending
2. Go to chrome://extensions/
3. Enable "Developer mode" (toggle top-right)
4. Click "Load unpacked" and select the extension folder
5. Click the ⚡ icon → Settings → make sure it says "Connected"

Let me know a good time for a quick call so I can walk you through it live.

Binh
```

---

## 7. Timeline chi tiết

```
📅 Mar 17 (Hôm nay) - Contract accepted
   ✅ Code Phase 1 hoàn thành
   → Gửi message cho client xin GHL access
   → Tạo GHL trial account để tự tìm hiểu

📅 Mar 18-19 - GHL Prep
   → Tự tìm hiểu GHL trên trial account
   → Test API endpoints trên trial
   → Đọc GHL API docs
   → Chờ client add vào account

📅 Mar 20-22 - Integration & Testing (sau khi có access)
   → Kết nối backend với GHL account client
   → Test tạo contacts thực
   → Test extension trên URLs client cung cấp
   → Fix bugs, điều chỉnh extractors

📅 Mar 23-25 - Deploy & Polish
   → Deploy backend lên cloud
   → Test full flow end-to-end
   → Quay video demo
   → Viết installation guide

📅 Mar 26-28 - Delivery
   → Gửi extension + hướng dẫn cho client
   → Call demo 15-20 phút
   → Client testing + bug fixes

📅 Mar 30 - Deadline
   → Milestone 1 complete ✅
   → Discuss Phase 2 scope
```

---

## Tóm tắt: 3 việc bạn CẦN LÀM NGAY

1. **🔑 Tạo GHL trial account** → tự tìm hiểu giao diện + test API
2. **💬 Gửi message cho client** → xin GHL account access + email invite
3. **📚 Đọc GHL API docs** → https://highlevel.stoplight.io/docs/integrations

Đừng chờ client — chủ động tìm hiểu GHL trước để khi được add vào account, bạn biết ngay cần lấy gì và làm gì.

# Hướng dẫn Test Phase 2B — Tiếng Việt

**Ngày:** 29/03/2026  
**Tính năng:** Lead Classifier + Draft Outreach + Outreach Queue + Extension UI  
**Trạng thái:** Sẵn sàng test  
**Phụ thuộc:** Phase 2A đã hoàn thành (enrich, save-profiles, draft-email, checkbox-list UI)

---

## 🚀 Yêu cầu trước khi test

### ✅ Checklist chuẩn bị

| # | Yêu cầu | Cách kiểm tra |
|---|---------|---------------|
| 1 | Backend đang chạy tại `http://localhost:8000` | Mở browser → vào `http://localhost:8000/docs` → thấy Swagger UI |
| 2 | Extension đã load vào Chrome | `chrome://extensions` → thấy "GHL Sales Assistant" với trạng thái **Enabled** |
| 3 | `OPENAI_API_KEY` đã set trong `.env` | Chạy `GET /health` → không có lỗi OpenAI |
| 4 | `GHL_API_KEY` và `GHL_LOCATION_ID` đã set | Thử capture 1 lead → lưu được vào GHL |
| 5 | GHL Custom Fields đã tạo: `linkedin_url`, `facebook_url`, `instagram_url` | Vào GHL → Settings → Custom Fields |
| 6 | Stage IDs đã được cấu hình sẵn trong `.env` (`GHL_PIPELINE_ID`, `GHL_STAGE_ID_COLD/WARM/HOT`) | Kiểm tra `backend/.env` — không cần điền thêm |

### Chạy Backend

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Khi thấy dòng sau = Backend sẵn sàng:
```
INFO:     Application startup complete.
```

### Cấu hình `.env` cho Phase 2B

Thêm vào file `backend/.env`:

```env
# Cũ (Phase 2A) — giữ nguyên
OPENAI_API_KEY=sk-your_key_here
SERPER_API_KEY=your_serper_key
GHL_API_KEY=your_ghl_api_key
GHL_LOCATION_ID=your_location_id

# Mới (Phase 2B) — thêm vào
DEFAULT_SENDER_NAME=Tên của bạn
DEFAULT_SENDER_COMPANY=Tên công ty bạn
DEFAULT_PITCH=Chúng tôi giúp các doanh nghiệp tiết kiệm thời gian bằng CRM thông minh

# Tùy chọn — nếu muốn trigger GHL Workflow sau khi classify
GHL_WORKFLOW_ID_HOT=wf_hot_immediate_001
GHL_WORKFLOW_ID_WARM=wf_warm_3day_001
GHL_WORKFLOW_ID_COLD=wf_cold_nurture_001
```

> ⚠️ **Lưu ý:** Nếu `GHL_WORKFLOW_ID_*` không được cấu hình, classify vẫn hoạt động bình thường — chỉ field `workflow_triggered` sẽ là `false`.

---

## 🏷️ Test 1: Phân loại Lead (Lead Classifier)

### Mục đích
Endpoint `POST /api/v1/leads/classify` nhận thông tin business → GPT-4o-mini chấm điểm → trả về tier **Cold / Warm / Hot** → tự động gắn tag trong GHL.

### Thang điểm phân loại

| Tín hiệu | Hot (+điểm cao) | Warm (+điểm vừa) | Cold (không điểm) |
|----------|-----------------|-----------------|-------------------|
| LinkedIn URL | +20 | +10 | — |
| Website HTTPS | +15 | +8 | Không có website: 0 |
| Nguồn lead | Google Maps: +15 | Google Search: +10 | Directory: +5 |
| Ngành phù hợp | Exact match: +20 | Partial: +10 | Không khớp: 0 |
| Quy mô công ty | 50-200 người: +10 | 10-50 người: +5 | <10: 0 |
| Rating ≥ 4.0 | +10 | +5 | — |
| Vị trí (thị trường mục tiêu) | +10 | +5 | Ngoài vùng: 0 |

**Ngưỡng:** Hot ≥ 70 điểm | Warm 40–69 điểm | Cold < 40 điểm

---

### 1A. Test bằng curl

**Input mẫu — Business có nhiều tín hiệu (kỳ vọng: Warm hoặc Hot):**

```bash
curl -X POST http://localhost:8000/api/v1/leads/classify \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
    "business_name": "Sunrise Senior Living",
    "website": "https://sunriseseniorliving.com",
    "industry": "Senior Care",
    "city": "Denver",
    "state": "CO",
    "lead_source": "google_maps",
    "linkedin_url": "https://linkedin.com/company/sunrise-senior-living",
    "employee_count_estimate": "50-200",
    "rating": "4.5",
    "trigger_workflow": false
  }'
```

**Kết quả mong đợi (200 OK):**

```json
{
  "success": true,
  "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
  "business_name": "Sunrise Senior Living",
  "tier": "warm",
  "score": 72,
  "reasons": [
    "Active LinkedIn presence found",
    "Professional website with HTTPS",
    "Senior care industry — high fit",
    "Rating 4.5+ suggests established business"
  ],
  "workflow_triggered": false,
  "workflow_id": null,
  "tag_applied": "tier:warm"
}
```

---

**Input mẫu — Business ít tín hiệu (kỳ vọng: Cold):**

```bash
curl -X POST http://localhost:8000/api/v1/leads/classify \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
    "business_name": "Bob Plumbing",
    "website": "",
    "industry": "Plumbing",
    "city": "Dallas",
    "state": "TX",
    "lead_source": "google_search",
    "linkedin_url": "",
    "employee_count_estimate": "",
    "rating": "",
    "trigger_workflow": false
  }'
```

**Kết quả mong đợi:** `"tier": "cold"`, `"score"` < 40

---

### 1B. Test bằng Postman

1. Tạo request mới: **POST** → `http://localhost:8000/api/v1/leads/classify`
2. Tab **Body** → chọn **raw** → **JSON**
3. Dán JSON từ ví dụ trên vào
4. Click **Send**

---

### 1C. Kiểm tra trong GHL

Sau khi gọi API thành công:

1. Vào GHL → **Contacts** → Tìm contact theo tên "Sunrise Senior Living"
2. Click vào contact
3. Kiểm tra mục **Tags**:
   - ✅ Phải thấy tag **`tier:warm`** (hoặc `tier:hot` / `tier:cold` tùy kết quả)
4. Nếu đã cấu hình `GHL_WORKFLOW_ID_WARM`:
   - ✅ Contact đã được thêm vào workflow **"AI - Warm Lead Sequence"**

**Kết quả mong đợi:**
- ✅ **PASS:** API trả 200, có `tier`, `score`, `reasons`, `tag_applied`; tag xuất hiện trong GHL
- ❌ **FAIL:** API trả 400/500, không có tag trong GHL

---

## ✍️ Test 2: Soạn tin nhắn theo platform (Draft Outreach)

### Mục đích
Endpoint `POST /api/v1/leads/draft-outreach` soạn tin nhắn phù hợp với từng platform — đúng giới hạn ký tự, đúng tone.

### Giới hạn ký tự theo platform

| Platform | Loại tin | Giới hạn | Tone |
|----------|---------|---------|------|
| LinkedIn | InMail | 2000 ký tự | Chuyên nghiệp |
| LinkedIn | Connection Request | **300 ký tự** ⚠️ | Ngắn gọn, thân thiện |
| Facebook | Page DM | 1000 ký tự | Trò chuyện, thân thiện |
| Instagram | DM | 1000 ký tự | Casual, có thể dùng emoji |

---

### 2A. Test LinkedIn InMail

```bash
curl -X POST http://localhost:8000/api/v1/leads/draft-outreach \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
    "business_name": "Sunrise Senior Living",
    "platform": "linkedin",
    "message_type": "inmail",
    "profile_url": "https://linkedin.com/company/sunrise-senior-living",
    "sender_name": "Mai Bui",
    "sender_company": "GHL Sales Assistant",
    "pitch": "We help senior care facilities streamline their CRM and save 5 hours per week",
    "tone": "professional"
  }'
```

**Kiểm tra kết quả:**
- ✅ `"char_count"` ≤ 2000
- ✅ `"platform"`: `"linkedin"`, `"message_type"`: `"inmail"`
- ✅ Tin nhắn dùng tone chuyên nghiệp
- ✅ Đề cập đến "Sunrise Senior Living"

---

### 2B. Test LinkedIn Connection Request (Quan trọng: < 300 ký tự)

```bash
curl -X POST http://localhost:8000/api/v1/leads/draft-outreach \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
    "business_name": "Sunrise Senior Living",
    "platform": "linkedin",
    "message_type": "connection_request",
    "profile_url": "https://linkedin.com/company/sunrise-senior-living",
    "sender_name": "Mai Bui",
    "sender_company": "GHL Sales Assistant",
    "pitch": "We help senior care facilities streamline their CRM",
    "tone": "friendly"
  }'
```

**Kiểm tra kết quả — quan trọng:**
- ✅ `"char_count"` **PHẢI < 300** — đây là giới hạn cứng của LinkedIn
- ✅ `"char_limit"`: 300
- ✅ Tin nhắn ngắn gọn, không pitch quá nhiều
- ❌ **FAIL** nếu `char_count` ≥ 300

---

### 2C. Test Facebook Page DM

```bash
curl -X POST http://localhost:8000/api/v1/leads/draft-outreach \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
    "business_name": "Sunrise Senior Living",
    "platform": "facebook",
    "message_type": "page_dm",
    "profile_url": "https://facebook.com/sunriseseniorliving",
    "sender_name": "Mai Bui",
    "sender_company": "GHL Sales Assistant",
    "pitch": "We help senior care facilities streamline their CRM",
    "tone": "friendly"
  }'
```

**Kiểm tra kết quả:**
- ✅ `"char_count"` ≤ 1000
- ✅ Tone thân thiện, tự nhiên (không quá formal)

---

### 2D. Test Instagram DM

```bash
curl -X POST http://localhost:8000/api/v1/leads/draft-outreach \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
    "business_name": "Sunrise Senior Living",
    "platform": "instagram",
    "message_type": "dm",
    "profile_url": "https://instagram.com/sunriseseniorliving",
    "sender_name": "Mai Bui",
    "sender_company": "GHL Sales Assistant",
    "pitch": "We help senior care facilities streamline their CRM",
    "tone": "casual"
  }'
```

**Kiểm tra kết quả:**
- ✅ `"char_count"` ≤ 1000
- ✅ Tone casual, có thể dùng emoji

---

### Tổng kết Test 2

- ✅ **PASS:** Tất cả 4 platform đều trả 200; char_count không vượt char_limit; LinkedIn CR < 300
- ❌ **FAIL:** Bất kỳ request nào trả 400/422/500; char_count vượt giới hạn

---

## 📋 Test 3: Tạo và quản lý Outreach Queue

### Mục đích
Test flow đầy đủ: tạo queue → lấy lại queue → cập nhật trạng thái. Dữ liệu được lưu vào GHL Notes.

---

### 3A. Tạo Queue cho nhiều platform cùng lúc

```bash
curl -X POST http://localhost:8000/api/v1/leads/outreach-queue \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
    "business_name": "Sunrise Senior Living",
    "platforms": ["linkedin", "facebook"],
    "context": {
      "linkedin_url": "https://linkedin.com/company/sunrise-senior-living",
      "facebook_url": "https://facebook.com/sunriseseniorliving",
      "industry": "Senior Care",
      "sender_name": "Mai Bui",
      "sender_company": "GHL Sales Assistant",
      "pitch": "We help senior care facilities streamline their CRM"
    },
    "draft_messages": true
  }'
```

**Kết quả mong đợi (201 Created):**

```json
{
  "success": true,
  "contact_id": "THAY_BẰNG_CONTACT_ID_THẬT",
  "items_created": 2,
  "queue": [
    {
      "item_id": "oq_..._linkedin_...",
      "platform": "linkedin",
      "message_type": "inmail",
      "status": "pending",
      "drafted_message": "...",
      "char_count": 287,
      "char_limit": 2000,
      "ghl_note_id": "..."
    },
    {
      "item_id": "oq_..._facebook_...",
      "platform": "facebook",
      "message_type": "page_dm",
      "status": "pending",
      "drafted_message": "...",
      "char_count": 210,
      "char_limit": 1000,
      "ghl_note_id": "..."
    }
  ]
}
```

**Kiểm tra trong GHL:**
1. Vào GHL → Tìm contact
2. Click vào contact → Tab **Notes**
3. Kiểm tra có 2 notes mới với prefix `[OUTREACH_QUEUE]`:
   ```
   [OUTREACH_QUEUE]
   item_id: oq_..._linkedin_...
   platform: linkedin
   message_type: inmail
   status: pending
   ...
   ```
   - ✅ **PASS** nếu thấy notes có prefix đúng
   - ❌ **FAIL** nếu notes không xuất hiện hoặc không có prefix

---

### 3B. Lấy lại Queue (GET)

Thay `THAY_BẰNG_CONTACT_ID_THẬT` bằng contact_id thực:

```bash
curl http://localhost:8000/api/v1/leads/outreach-queue/THAY_BẰNG_CONTACT_ID_THẬT
```

Hoặc lọc chỉ lấy trạng thái `pending`:

```bash
curl "http://localhost:8000/api/v1/leads/outreach-queue/THAY_BẰNG_CONTACT_ID_THẬT?status=pending"
```

**Kết quả mong đợi:**
- ✅ `"total"`: 2 (đúng số items đã tạo)
- ✅ `"items"` chứa đủ thông tin `item_id`, `platform`, `drafted_message`, `status`
- ✅ Items được sắp xếp theo `created_at` mới nhất trước

---

### 3C. Cập nhật trạng thái Queue Item (PATCH)

Lấy `item_id` từ kết quả bước 3A, ví dụ: `oq_abc123_linkedin_1711684800`

```bash
curl -X PATCH http://localhost:8000/api/v1/leads/outreach-queue/oq_abc123_linkedin_1711684800 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "sent",
    "sent_at": "2026-03-29T12:00:00Z",
    "notes": "Đã gửi qua LinkedIn InMail"
  }'
```

**Kết quả mong đợi:**
```json
{
  "success": true,
  "item_id": "oq_abc123_linkedin_1711684800",
  "status": "sent",
  "ghl_note_updated": true
}
```

**Kiểm tra trong GHL:**
- ✅ Note tương ứng đã được cập nhật `status: sent`

**Test thêm: Đánh dấu skipped:**
```bash
curl -X PATCH http://localhost:8000/api/v1/leads/outreach-queue/oq_abc123_facebook_1711684800 \
  -H "Content-Type: application/json" \
  -d '{"status": "skipped"}'
```

---

### Tổng kết Test 3

- ✅ **PASS:** Tạo được queue → GET lấy lại đúng → PATCH update trạng thái → GHL Notes cập nhật
- ❌ **FAIL:** Bất kỳ bước nào fail, GHL Notes không có `[OUTREACH_QUEUE]` prefix

---

## 🖥️ Test 4: Extension Panel — Outreach Queue UI

### Mục đích
Test toàn bộ flow từ extension: Capture lead → Tìm social profiles → Mở Outreach Queue panel → Classify → Xem tin nhắn → Copy → Gửi.

### Điều kiện tiên quyết
- Extension đã load tại `chrome://extensions` → **Load unpacked** → chọn thư mục `extension/`
- Backend đang chạy tại `http://localhost:8000`
- Đã có contact trong GHL

---

### Bước 1: Capture một lead từ Google Search

1. Mở Google → Tìm kiếm: **"Sunrise Senior Living Denver CO"**
2. Click vào một kết quả tìm được (không phải Google Maps)
3. Extension floating button **"⚡ Send to GHL"** xuất hiện
4. Click nút đó → Review popup hiện lên
5. Kiểm tra thông tin:
   - ✅ `business_name`: "Sunrise Senior Living" (hoặc tương tự)
   - ✅ `website`: URL của business (KHÔNG phải `google.com/maps/*`)
6. Click **"Save to GHL"**

**Kết quả mong đợi:**
- ✅ Toast: "✅ New lead: Sunrise Senior Living"
- ✅ Popup tự đóng

---

### Bước 2: Click "Find Social Profiles"

Sau khi save thành công:
1. Panel Phase 2A/2B hiện ra ở góc phải
2. Click nút **"🔍 Find Social Profiles"** (màu tím)
3. Chờ 5-15 giây

**Kết quả mong đợi:**
- ✅ Nút chuyển thành "✅ X profiles found"
- ✅ Hiện danh sách links: LinkedIn, Facebook, Instagram (nếu tìm được)

---

### Bước 3: Click "📤 Outreach Queue"

1. Click nút **"📤 Outreach Queue"** (xuất hiện sau khi tìm được social profiles)

**Kết quả mong đợi:**
- ✅ Panel Outreach Queue mở ra
- ✅ Hiện tên business + danh sách platforms tìm được
- ✅ Nút **"🔵 Classify Lead"** hiển thị

---

### Bước 4: Click "🔵 Classify Lead"

1. Click nút **"🔵 Classify Lead"**
2. Chờ 3-5 giây (AI đang chạy)

**Kết quả mong đợi:**
- ✅ Badge tier xuất hiện: **🔴 HOT** hoặc **🟡 WARM** hoặc **🔵 COLD**
- ✅ Hiện điểm số (ví dụ: "Score: 72")
- ✅ Hiện lý do (ví dụ: "Active LinkedIn presence found")
- ✅ Vào GHL → Contact → Tags: thấy `tier:warm` (hoặc `tier:hot` / `tier:cold`)

---

### Bước 5: Xem tin nhắn đã soạn sẵn

Sau khi classify xong:
1. Panel hiện danh sách platform với tin nhắn AI đã soạn
2. Ví dụ: LinkedIn InMail tab, Facebook DM tab

**Kết quả mong đợi cho mỗi platform:**
- ✅ Hiện tin nhắn đầy đủ
- ✅ Hiện số ký tự / giới hạn (ví dụ: "287 / 2000")
- ✅ LinkedIn Connection Request: số ký tự **< 300**
- ✅ Nút **"📋 Copy"** và **"↗ Open Profile"** hiển thị

---

### Bước 6: Click "📋 Copy"

1. Click nút **"📋 Copy"** bên cạnh tin nhắn LinkedIn
2. Mở một tab text editor (Notepad, Google Docs)
3. Ctrl+V để paste

**Kết quả mong đợi:**
- ✅ Tin nhắn được copy vào clipboard đúng
- ✅ Nút đổi thành "✅ Copied!" trong 2 giây
- ✅ Text paste đầy đủ, không bị cắt

---

### Bước 7: Click "↗ Open Profile"

1. Click nút **"↗ Open Profile"** bên cạnh LinkedIn

**Kết quả mong đợi:**
- ✅ Tab mới mở ra đúng URL LinkedIn profile của business
- ✅ KHÔNG mở google.com hoặc URL sai

---

### Bước 8: Click "✅ Mark All Sent"

Sau khi đã gửi tin nhắn:
1. Quay lại panel extension
2. Click nút **"✅ Mark All Sent"**

**Kết quả mong đợi:**
- ✅ Tất cả items chuyển trạng thái sang `sent`
- ✅ Panel hiện thông báo "All messages marked as sent"
- ✅ Vào GHL → Contact → Notes: các note `[OUTREACH_QUEUE]` đã có `status: sent`

---

### Tổng kết Test 4

- ✅ **PASS:** Toàn bộ 8 bước hoạt động đúng, dữ liệu đồng bộ với GHL
- ❌ **FAIL:** Bất kỳ bước nào bị lỗi hoặc UI không phản hồi

---

## 🐛 Test 5: BUG-001 Fix — Google Search URL

### Mô tả lỗi đã fix
**BUG-001:** Extractor của Google Search trước đây lấy nhầm URL `google.com/maps/...` làm website của business thay vì website thực sự.

### Cách test

#### Bước 1: Tìm business có Google Maps listing

1. Mở Google → Tìm: **"plumber near me Dallas TX"** (hoặc bất kỳ business local nào)
2. Trong kết quả, click vào một link của business
3. Extension floating button xuất hiện → Click **"⚡ Send to GHL"**

#### Bước 2: Kiểm tra website trong popup review

Trước khi save, kiểm tra field **"Website"** trong popup:
- ✅ **PASS (sau fix):** Website phải là URL thực của business (ví dụ: `https://dallasplumbing.com`)
- ❌ **FAIL (lỗi cũ):** Website là `https://google.com/maps/place/...` hoặc bất kỳ URL `google.com/...`

#### Bước 3: Kiểm tra trong GHL sau khi save

1. Save lead vào GHL
2. Vào GHL → Contact vừa tạo
3. Kiểm tra field **"Website"**:
   - ✅ **PASS:** URL là domain của business, VÍ DỤ: `https://dallasplumbing.com`
   - ❌ **FAIL:** URL chứa `google.com` hoặc `maps.google.com`

#### Test thêm: Google Maps trực tiếp

1. Mở `google.com/maps`
2. Tìm business → Click vào một business
3. Extension button xuất hiện → Click → Xem website trong popup
   - ✅ Website phải là website thực của business (lấy từ Google Maps listing)
   - ✅ KHÔNG phải URL của Google Maps

---

### Tổng kết Test 5

- ✅ **PASS:** Không có `google.com/*` URL nào xuất hiện trong field website
- ❌ **FAIL:** Vẫn thấy `google.com/maps/...` trong website field

---

## 🎯 Test 6: GHL Opportunities Integration

### Mục đích
Khi classify lead, hệ thống tự động **tạo mới hoặc di chuyển** Opportunity trong GHL Pipeline về đúng stage tương ứng với tier (Cold / Warm / Hot). Tính năng này chạy ngầm sau mỗi lần gọi `POST /api/v1/leads/classify`.

### Thông tin Pipeline đã cấu hình

| Thông tin | Giá trị |
|-----------|---------|
| Pipeline | **Paperdaz** |
| Pipeline ID | `i2oUxB0CoBO1XAzDyJ9y` |
| Location ID | `cJrlhBzUswX9ExybVa8c` |

| Stage | Stage ID |
|-------|---------|
| Cold Lead | `cd1fdbbc-098f-4d47-a84a-fb09e486a7cd` |
| Warm Lead | `e9a4d7d2-cb6f-4357-bfcf-9e0cf1ec96ad` |
| Hot Lead | `30ea3331-9266-437a-9e65-a4d2b3ab0ec7` |
| In Progress | `9472b3d7-d3c4-46f2-9be2-4767bcaf9c73` |

> ✅ **Lưu ý:** Tất cả Stage IDs trên đã được cấu hình sẵn trong `backend/.env` — không cần điền thêm.

---

### 6A. Test bằng curl với Contact ID thực tế

**Contact ID thực tế:** `d08mdv2DRUxwKGzOmDBe` (Buffet Poseidon Lê Văn Lương — đã có opportunity trong pipeline)

**Chạy lệnh sau trên Windows CMD:**

```cmd
curl -X POST "http://localhost:8000/api/v1/leads/classify" -H "Content-Type: application/json" -d "{\"contact_id\":\"d08mdv2DRUxwKGzOmDBe\",\"business_name\":\"Buffet Poseidon\",\"website\":\"https://buffetposeidon.com\",\"trigger_workflow\":false}"
```

**Kết quả mong đợi (200 OK):**

```json
{
  "success": true,
  "contact_id": "d08mdv2DRUxwKGzOmDBe",
  "business_name": "Buffet Poseidon",
  "tier": "warm",
  "score": 55,
  "reasons": [
    "Professional website with HTTPS",
    "Food & Beverage industry — moderate fit"
  ],
  "workflow_triggered": false,
  "workflow_id": null,
  "tag_applied": "tier:warm",
  "opportunity_action": "updated"
}
```

> ⚠️ Field `opportunity_action` phải có mặt trong response. Giá trị `"updated"` nghĩa là opportunity đã có sẵn trong pipeline và được di chuyển sang đúng stage.

---

### 6B. Giải thích các giá trị `opportunity_action`

| Giá trị | Ý nghĩa | Hành động hệ thống |
|---------|---------|-------------------|
| `"created"` | Contact chưa có opportunity → tạo mới trong pipeline | GHL tạo opportunity mới, gán stage theo tier |
| `"updated"` | Contact đã có opportunity → di chuyển sang stage mới | GHL move opportunity sang stage Cold/Warm/Hot |
| `"skipped"` | `GHL_PIPELINE_ID` không được cấu hình trong `.env` | Bỏ qua, không lỗi — graceful skip |
| `"failed"` | Lỗi khi gọi GHL API (token sai scope, network error...) | Log lỗi phía backend, API vẫn trả 200 |

---

### 6C. Kiểm tra trong GHL UI

1. Mở link sau trong browser:
   ```
   https://app.gohighlevel.com/v2/location/cJrlhBzUswX9ExybVa8c/opportunities/list
   ```
2. Tìm pipeline **Paperdaz**
3. Tìm card **"Buffet Poseidon Lê Văn Lương"**
4. Kiểm tra:
   - ✅ Card xuất hiện đúng stage tương ứng với tier vừa classify (Cold / Warm / Hot)
   - ✅ Card KHÔNG nằm sai stage

---

### 6D. Test trường hợp `"skipped"` (graceful)

Tạm thời xoá `GHL_PIPELINE_ID` khỏi `.env`, restart backend, gọi lại classify:

**Kết quả mong đợi:**
```json
{
  "opportunity_action": "skipped"
}
```
- ✅ API vẫn trả 200, không crash
- ✅ Tag `tier:*` vẫn được gắn vào contact

> Nhớ khôi phục `GHL_PIPELINE_ID=i2oUxB0CoBO1XAzDyJ9y` vào `.env` sau khi test xong.

---

### Tổng kết Test 6

- ✅ **PASS:** `opportunity_action` là `"created"` hoặc `"updated"`; card xuất hiện đúng stage trong GHL Pipeline UI
- ❌ **FAIL:** `opportunity_action` là `"failed"`; card không xuất hiện hoặc nằm sai stage

---

## ⚠️ Kiểm tra lỗi thường gặp

### Lỗi 1: Backend chưa chạy

**Triệu chứng:**
- Extension hiện: "❌ Error: Failed to fetch" hoặc "Connection refused"
- curl trả: `curl: (7) Failed to connect to localhost port 8000`

**Cách fix:**
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Kiểm tra: `http://localhost:8000/docs` phải mở được.

---

### Lỗi 2: OpenAI API key thiếu hoặc sai

**Triệu chứng:**
- `/classify` trả: `{"detail": "OpenAI API error: Invalid API key"}`
- `/draft-outreach` trả 500

**Cách fix:**
1. Mở `backend/.env`
2. Kiểm tra `OPENAI_API_KEY=sk-...` đúng chưa
3. Thử: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`
4. Restart backend sau khi sửa `.env`

---

### Lỗi 3: GHL API key thiếu scope

**Triệu chứng khi classify với `trigger_workflow: true`:**
- Response có `"workflow_triggered": false` dù đã cấu hình `GHL_WORKFLOW_ID_WARM`
- Log backend: `"403 Forbidden: workflows.write scope required"`

**Giải thích:**
- Classify **vẫn hoạt động** — AI chạm điểm, tag được gắn ✅
- Chỉ phần trigger workflow bị bỏ qua
- `workflow_triggered: false` là hành vi đúng khi scope chưa được cấp

**Cách fix nếu muốn trigger workflow:**
1. Vào GHL → **Settings → API Keys**
2. Tìm API key đang dùng
3. Thêm scope: `workflows.readonly` và `workflows.write`
4. Tạo workflow trong GHL tên: "AI - Warm Lead Sequence" (hoặc Hot/Cold)
5. Lấy Workflow ID → cập nhật `GHL_WORKFLOW_ID_WARM=...` trong `.env`
6. Restart backend

---

### Lỗi 4: GHL Contact ID không tồn tại

**Triệu chứng:**
- `/classify` hoặc `/outreach-queue` trả 404: `"Contact not found in GHL"`

**Cách fix:**
1. Vào GHL → Contacts → Tìm contact
2. Click vào contact → URL trên browser có dạng: `.../contacts/CONTACT_ID`
3. Copy `CONTACT_ID` đó → dùng trong API request

---

### Lỗi 5: Serper API key thiếu (ảnh hưởng Find Social Profiles)

**Triệu chứng:**
- Extension: nút "Find Social Profiles" spinner không dừng
- Backend log: `"Serper API error: 401 Unauthorized"`

**Cách fix:**
1. Đăng ký tại `serper.dev` → lấy API key miễn phí
2. Thêm `SERPER_API_KEY=your_key` vào `backend/.env`
3. Restart backend

---

### Lỗi 6: `opportunity_action: "failed"` — GHL API không có scope opportunities

**Triệu chứng:**
- Response classify có `"opportunity_action": "failed"`
- Backend log: `"403 Forbidden: opportunities.write scope required"`

**Giải thích:**
- Classify **vẫn hoạt động** — AI chấm điểm, tag được gắn ✅
- Chỉ phần tạo/cập nhật Opportunity trong GHL Pipeline bị bỏ qua

**Cách fix:**
1. Vào GHL → **Settings → API Keys**
2. Tìm API key đang dùng (`GHL_API_KEY` trong `.env`)
3. Thêm 2 scope sau:
   - ✅ `opportunities.readonly`
   - ✅ `opportunities.write`
4. Lưu lại → Restart backend
5. Gọi lại `/classify` → kiểm tra `opportunity_action` phải là `"created"` hoặc `"updated"`

---

### Lỗi 7: Extension không thấy nút "📤 Outreach Queue"

**Triệu chứng:**
- Sau khi Find Social Profiles thành công, không thấy nút "📤 Outreach Queue"

**Cách fix:**
1. Mở `chrome://extensions`
2. Tìm "GHL Sales Assistant" → Click **Reload** (biểu tượng ↺)
3. Refresh trang đang test
4. Thử lại

---

## ✅ Checklist Cuối — PASS / FAIL

Đánh dấu ✅ PASS hoặc ❌ FAIL cho từng item:

### Backend Endpoints

| # | Test | Kết quả |
|---|------|---------|
| BE-01 | `POST /classify` trả 200 với tier + score + reasons | ⬜ |
| BE-02 | `POST /classify` gắn đúng tag `tier:warm` vào GHL | ⬜ |
| BE-03 | `POST /classify` với Cold input → tier = "cold", score < 40 | ⬜ |
| BE-04 | `POST /classify` thiếu `contact_id` → trả 400 | ⬜ |
| BE-05 | `POST /draft-outreach` LinkedIn InMail → char_count ≤ 2000 | ⬜ |
| BE-06 | `POST /draft-outreach` LinkedIn Connection Request → char_count **< 300** | ⬜ |
| BE-07 | `POST /draft-outreach` Facebook DM → char_count ≤ 1000 | ⬜ |
| BE-08 | `POST /draft-outreach` Instagram DM → char_count ≤ 1000 | ⬜ |
| BE-09 | `POST /outreach-queue` với 2 platforms → tạo 2 items | ⬜ |
| BE-10 | `POST /outreach-queue` → GHL Notes có prefix `[OUTREACH_QUEUE]` | ⬜ |
| BE-11 | `GET /outreach-queue/{contact_id}` → trả đúng danh sách items | ⬜ |
| BE-12 | `GET /outreach-queue/{contact_id}?status=pending` → lọc đúng | ⬜ |
| BE-13 | `PATCH /outreach-queue/{item_id}` status → sent → GHL Note cập nhật | ⬜ |
| BE-14 | `PATCH /outreach-queue/{item_id}` status → skipped | ⬜ |

### Extension UI

| # | Test | Kết quả |
|---|------|---------|
| EX-01 | Capture lead từ Google Search thành công | ⬜ |
| EX-02 | "Find Social Profiles" tìm được ≥1 profile | ⬜ |
| EX-03 | Nút "📤 Outreach Queue" xuất hiện sau khi tìm profiles | ⬜ |
| EX-04 | Click "📤 Outreach Queue" → panel mở đúng | ⬜ |
| EX-05 | Click "🔵 Classify Lead" → tier badge hiện đúng | ⬜ |
| EX-06 | Tag `tier:*` xuất hiện trong GHL sau classify | ⬜ |
| EX-07 | Tin nhắn đã soạn hiện cho từng platform trong panel | ⬜ |
| EX-08 | Số ký tự hiển thị đúng (X / limit) | ⬜ |
| EX-09 | Click "📋 Copy" → clipboard chứa đúng tin nhắn | ⬜ |
| EX-10 | Click "↗ Open Profile" → mở đúng URL profile | ⬜ |
| EX-11 | Click "✅ Mark All Sent" → trạng thái cập nhật trong GHL | ⬜ |

### Bug Fix

| # | Test | Kết quả |
|---|------|---------|
| BUG-001 | Google Search: website field KHÔNG chứa `google.com/*` | ⬜ |
| BUG-002 | Google Maps: website field là URL thực của business | ⬜ |

### GHL Opportunities

| # | Test | Kết quả |
|---|------|---------|
| OPP-01 | Classify lead → `opportunity_action: "updated"` (contact `d08mdv2DRUxwKGzOmDBe` có sẵn trong pipeline) | ⬜ |
| OPP-02 | Opportunity xuất hiện đúng stage trong GHL Pipeline UI (`/opportunities/list`) | ⬜ |
| OPP-03 | Classify khi không cấu hình `GHL_PIPELINE_ID` → `opportunity_action: "skipped"` (graceful) | ⬜ |

### Lỗi & Edge Cases

| # | Test | Kết quả |
|---|------|---------|
| ERR-01 | Backend tắt → extension hiện thông báo lỗi rõ ràng (không crash) | ⬜ |
| ERR-02 | `trigger_workflow: true` nhưng scope chưa cấp → `workflow_triggered: false`, không crash | ⬜ |
| ERR-03 | `contact_id` không tồn tại → trả 404 | ⬜ |
| ERR-04 | Platform không hợp lệ trong `/draft-outreach` → trả 400 | ⬜ |

---

## 📊 Tổng kết

| Phần | Tổng tests | PASS | FAIL |
|------|-----------|------|------|
| Backend Endpoints | 14 | — | — |
| Extension UI | 11 | — | — |
| Bug Fix | 2 | — | — |
| GHL Opportunities | 3 | — | — |
| Edge Cases | 4 | — | — |
| **Tổng cộng** | **34** | — | — |

**Tiêu chí chấp nhận Phase 2B:**
- ✅ Tất cả BE-01 đến BE-14 đều PASS
- ✅ Tất cả EX-01 đến EX-11 đều PASS
- ✅ BUG-001 PASS
- ✅ OPP-01, OPP-02 PASS (opportunity đúng stage trong GHL)
- ✅ OPP-03 PASS (graceful skip khi không cấu hình pipeline)
- ✅ ERR-01, ERR-02 PASS (graceful failure)

---

*Hướng dẫn này được tạo bởi BA Agent — 29/03/2026*  
*Liên quan: [`plans/phase2b-spec.md`](plans/phase2b-spec.md) | [`plans/phase2a-testing-guide-vi.md`](plans/phase2a-testing-guide-vi.md)*

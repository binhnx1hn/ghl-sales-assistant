# Hướng dẫn Test Phase 2A — Tiếng Việt

**Ngày:** 26/03/2026  
**Tính năng:** Tìm Social Profiles + Soạn Email bằng AI  
**Trạng thái:** Sẵn sàng test

---

## 🚀 Chuẩn bị Environment

### Bước 1: Cài dependencies
```bash
cd backend
pip install openai==1.30.0
```

### Bước 2: Config `.env`
Thêm vào `backend/.env`:
```
OPENAI_API_KEY=sk-your_key_here
SERPER_API_KEY=your_serper_key
DEFAULT_SENDER_NAME=Tên của bạn
DEFAULT_SENDER_COMPANY=Tên công ty
DEFAULT_PITCH=Chúng tôi giúp các doanh nghiệp tiết kiệm thời gian bằng CRM thông minh
```

### Bước 3: Tạo Custom Fields trong GHL
Vào GHL → **Settings → Custom Fields** → Tạo 4 fields:
```
❶ LinkedIn URL      | Key: linkedin_url     | Type: Text
❷ Facebook URL      | Key: facebook_url     | Type: Text  
❸ Instagram URL     | Key: instagram_url    | Type: Text
❹ TikTok URL        | Key: tiktok_url       | Type: Text
```

### Bước 4: Chạy Backend
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Khi thấy dòng sau = Backend sẵn sàng:
```
INFO:     Application startup complete.
```

---

## 📋 Test Case 1: Tìm Social Profiles

### Mục đích
Sau khi capture lead, hệ thống tự động hiện panel → User bấm "🔍 Tìm Social Profiles" → Hệ thống tìm LinkedIn/Facebook/Instagram/TikTok → Lưu vào GHL.

### Các bước thực hiện

#### **Bước 1: Capture một lead**
1. Mở extension → Vào trang có thông tin business (Google Maps, Google Search, etc.)
2. Click nút floating **"⚡ Send to GHL"** của extension
3. Review popup hiện lên với thông tin business
4. Điền/sửa thông tin nếu cần
5. Click **"Save to GHL"**

**Kỳ vọng:**
- ✅ Toast hiện: "✅ New lead: [Business Name]"
- ✅ Popup tự động đóng

#### **Bước 2: Nhìn Phase 2A Panel**
Sau khi save thành công:
- ✅ Panel mới xuất hiện ở góc phải màn hình
- ✅ Có 2 nút:
  - 🔍 **Find Social Profiles** (tím)
  - ✉️ **Draft Email from LinkedIn** (xanh lá)

#### **Bước 3: Click nút "Find Social Profiles"**
1. Click nút 🔍
2. Nút thay đổi thành: "🔍 Searching social profiles..."
3. Chờ 5-10 giây (API Serper đang tìm kiếm)

**Kỳ vọng:**
- ✅ Nút chuyển sang: "✅ 2 profiles found" (hoặc số lượng found)
- ✅ Status text hiện: "Found: [LinkedIn] · [Facebook] · [Instagram]"
- ✅ Các links đó có thể click được
- ✅ Click links → Mở tab mới với profile đúng

#### **Bước 4: Kiểm tra GHL Contact**
1. Vào GHL → Tìm contact vừa capture
2. Scroll xuống **Custom Fields** section
3. Kiểm tra:
   - ✅ `linkedin_url` = URL của LinkedIn company page
   - ✅ `facebook_url` = URL của Facebook page (nếu tìm được)
   - ✅ `instagram_url` = URL của Instagram (nếu tìm được)
   - ✅ `tiktok_url` = URL của TikTok (nếu tìm được)

**Tổng kết:**
- ✅ **PASS** nếu: Tìm được ≥1 profile, save thành công vào GHL custom fields
- ❌ **FAIL** nếu: Không tìm được profiles hoặc save bị lỗi

---

## 📧 Test Case 2: Soạn Email bằng AI

### Mục đích
Sau khi tìm được LinkedIn profile, user bấm "✉️ Draft Email" → AI đọc LinkedIn → GPT-4o soạn email cá nhân hóa → Hiện draft trong panel → Lưu vào GHL Notes.

### Các bước thực hiện

#### **Bước 1: Hoàn thành Test Case 1 trước**
Cần có LinkedIn profile đã tìm được (để AI có dữ liệu để soạn email)

#### **Bước 2: Click nút "Draft Email from LinkedIn"**
1. Vào Phase 2A panel
2. Click nút ✉️ **Draft Email from LinkedIn** (xanh lá)
3. Nút chuyển thành: "✉️ AI is drafting your email..."
4. Status text hiện: "✉️ AI is drafting your email..."
5. Chờ 5-15 giây (OpenAI API đang soạn)

#### **Bước 3: Kiểm tra Draft Email**
Sau khi xong, kiểm tra:

**Nút thay đổi thành:**
```
✅ Email Draft Ready
   Saved to GHL Notes
```

**Panel mở rộng hiện:**
```
📧 AI DRAFTED EMAIL

Subject: Helping [Business Name] Save Time

Body:
Hi [Name],

I admire your work at [Company]... [personalized content]

Would a 15-min call make sense?

Best,
[Sender Name]
```

#### **Bước 4: Kiểm tra Chất lượng Email**

📝 **Subject:**
- ✅ Cụ thể cho business (không generic như "Quick Question")
- ✅ Liên quan đến value proposition

📝 **Body:**
- ✅ Nhắc đến detail từ LinkedIn (e.g., "I see you serve X industry")
- ✅ Có value prop của bạn (tiết kiệm thời gian, v.v.)
- ✅ Có CTA rõ ràng ("15-min call?", "quick chat?")
- ✅ Ngắn gọn (< 150 từ)
- ✅ Ngôn ngữ chuyên nghiệp nhưng tự nhiên (không robot)

#### **Bước 5: Kiểm tra GHL Notes**
1. Vào GHL contact
2. Scroll xuống **Notes** tab
3. Tìm note mới nhất có header:
```
📧 AI DRAFTED EMAIL
────────────────────
Subject: [Email subject]

[Email body]
────────────────────
Generated from LinkedIn: [URL]
(Review and personalize before sending)
```

**Kỳ vọng:**
- ✅ Note được tạo thành công
- ✅ Nội dung đầy đủ (subject + body)
- ✅ Có lời khuyên "Review and personalize before sending"

**Tổng kết:**
- ✅ **PASS** nếu: Email draft được soạn, lưu vào GHL Notes, chất lượng tốt
- ❌ **FAIL** nếu: Draft lỗi hoặc không save được

---

## 🧪 Test trực tiếp bằng cURL (không cần extension)

Nếu muốn test endpoints mà không cần qua extension:

### Test 1: Endpoint `/leads/enrich` (Tìm Social Profiles)

```bash
curl -X POST http://localhost:8000/api/v1/leads/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "id_contact_ghl_thuc",
    "business_name": "Sunrise Senior Living",
    "city": "Denver",
    "state": "CO"
  }'
```

**Kỳ vọng trả về:**
```json
{
  "success": true,
  "contact_id": "id_contact_ghl_thuc",
  "business_name": "Sunrise Senior Living",
  "profiles_found": {
    "linkedin": "https://www.linkedin.com/company/...",
    "facebook": "https://www.facebook.com/...",
    "instagram": "https://www.instagram.com/...",
    "tiktok": null
  },
  "saved_to_ghl": true,
  "profiles_count": 3
}
```

---

### Test 2: Endpoint `/leads/draft-email` (Soạn Email)

```bash
curl -X POST http://localhost:8000/api/v1/leads/draft-email \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "id_contact_ghl_thuc",
    "business_name": "Sunrise Senior Living",
    "linkedin_url": "https://www.linkedin.com/company/sunrise-community-inc",
    "sender_name": "Tên của bạn",
    "sender_company": "Công ty của bạn",
    "pitch": "Chúng tôi giúp các cơ sở chăm sóc người già tiết kiệm 5 giờ/tuần"
  }'
```

**Kỳ vọng trả về:**
```json
{
  "success": true,
  "contact_id": "id_contact_ghl_thuc",
  "business_name": "Sunrise Senior Living",
  "draft_email": {
    "subject": "Helping Sunrise Senior Living Save Time",
    "body": "Hi there,\n\nI admire your work... [personalized]"
  },
  "saved_as_note": true,
  "note_id": "note_123abc",
  "profile_data_used": {
    "name": "Sunrise Community, Inc",
    "bio": "..."
  }
}
```

---

## ✅ Checklist Kiểm tra

### ✅ Tính năng Tìm Social Profiles
- [ ] Nút xuất hiện sau capture lead
- [ ] Serper API tìm được profiles
- [ ] Profiles hiện dạng links có thể click
- [ ] Links trỏ đúng business pages (không phải trang generic)
- [ ] GHL custom fields được update
- [ ] Hoạt động cho nhiều business khác nhau

### ✅ Tính năng Soạn Email bằng AI
- [ ] Nút hiện loading state đúng
- [ ] Email draft cá nhân hóa (nhắc đến công ty, industry)
- [ ] Subject line cụ thể (không generic)
- [ ] Email body < 150 từ
- [ ] Có CTA rõ ràng
- [ ] Tone chuyên nghiệp nhưng tự nhiên
- [ ] Draft được lưu thành GHL note
- [ ] Preview hiện trong panel

### ✅ Xử lý Lỗi
- [ ] Serper API lỗi → hiện error message
- [ ] OpenAI API lỗi → hiện error message
- [ ] GHL custom fields không tồn tại → log warning, không crash
- [ ] GHL note save lỗi → draft vẫn hiện, user có thể copy thủ công

---

## 🐛 Lỗi Thường Gặp & Cách Sửa

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| "All imports OK" nhưng API lỗi 500 | Thiếu API key | Kiểm tra `OPENAI_API_KEY`, `SERPER_API_KEY` trong `.env` |
| Không tìm được profiles | Business name quá generic | Thêm city/state hoặc website để tìm chính xác |
| Email draft quá generic | LinkedIn profile thiếu info | Kiểm tra profile có public info không |
| GHL custom fields không update | Field key không khớp | Tạo custom field với key chính xác: `linkedin_url` |
| Extension panel không hiện | ReviewPopup chưa load | Reload extension trong chrome://extensions |

---

## 📊 Tiêu chí Hoàn thành (Success Metrics)

Phase 2A sẵn sàng deploy khi:

### ✅ Tìm Social Profiles
- 80%+ business tìm được ≥1 profile
- Links trỏ đúng business pages
- Profiles lưu vào GHL trong < 10 giây

### ✅ Soạn Email
- 95%+ email draft được soạn thành công
- Chất lượng email 4/5 sao (review thủ công)
- Thời gian soạn < 15 giây

### ✅ UX
- Cả 2 nút hiện rõ ràng và hoạt động sau capture lead
- Loading state rõ ràng (user biết đang xử lý)
- Error messages hữu ích (không technical jargon)
- Panel tự đóng sau 30s hoặc user action

---

## 📝 Mẫu Report Test

Sau khi test xong, lưu kết quả:

```markdown
## Report Test Phase 2A — [Ngày]

**Người test:** [Tên bạn]  
**Backend version:** [Version/Commit]  
**Extension version:** [Version]  

### Test Case 1: Tìm Social Profiles
- [ ] ✅ PASS
- [ ] ❌ FAIL — Issue: [Mô tả]

### Test Case 2: Soạn Email bằng AI
- [ ] ✅ PASS
- [ ] ❌ FAIL — Issue: [Mô tả]

### Tổng kết
- [ ] ✅ Sẵn sàng deploy cho client
- [ ] ❌ Cần fix — Xem issues bên dưới

**Issues tìm thấy:**
1. ...
2. ...

**Ký tên:** [Signed] ✅ / ❌
```

---

## 💬 Support

Nếu gặp vấn đề:
1. Check logs backend (console sẽ print error)
2. Kiểm tra API keys trong `.env`
3. Verify custom fields tồn tại trong GHL
4. Reload extension nếu code thay đổi

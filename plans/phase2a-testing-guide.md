# Phase 2A Testing Guide

**Date:** 2026-03-27  
**Component:** Social Profile Finder + AI Email Drafter  
**Status:** Ready for integration testing

---

## 🧪 Test Environment Setup

### Prerequisites
- Backend running: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Chrome extension loaded in developer mode
- GHL test account with API credentials in `.env`
- Serper.dev API key in `.env`
- OpenAI API key in `.env`

### GHL Test Setup
Create 4 custom fields in your GHL test account (Settings → Custom Fields):
```
Field Name: LinkedIn URL     | Key: linkedin_url     | Type: Text
Field Name: Facebook URL     | Key: facebook_url     | Type: Text
Field Name: Instagram URL    | Key: instagram_url    | Type: Text
Field Name: TikTok URL       | Key: tiktok_url       | Type: Text
```

---

## 📝 Test Case 1: Social Profile Enrichment

### Scenario
User captures a lead (e.g., "Sunrise Senior Living") → After save, clicks "Find Social Profiles" → System finds and saves LinkedIn/Facebook/Instagram/TikTok URLs to GHL contact.

### Steps

1. **Navigate to a business website** (e.g., Google Maps listing for Sunrise Senior Living, or Google Search result)

2. **Click the extension's floating button** → Review popup appears with extracted data

3. **Edit business name if needed** → Click "Save to GHL"
   - Lead gets captured to GHL
   - Toast shows "✅ New lead: Sunrise Senior Living"

4. **Phase 2A panel appears** on the right side with 2 buttons:
   - 🔍 Find Social Profiles
   - ✉️ Draft Email from LinkedIn

5. **Click "🔍 Find Social Profiles"**
   - Button shows loading state: "🔍 Searching social profiles..."
   - Wait 5-10 seconds for Serper search to complete

6. **Verify results**
   - ✅ If found: Button shows "✅ 1 profile found" (or more)
   - ✅ Panel shows clickable links: [LinkedIn] [Facebook] [Instagram]
   - ✅ Links open in new tabs and point to correct profiles
   - ✅ GHL contact should now have these URLs saved in custom fields

7. **Check GHL contact directly**
   - Open GHL contact record
   - Scroll to custom fields section
   - Verify: `linkedin_url`, `facebook_url`, `instagram_url`, `tiktok_url` are populated

---

## 📧 Test Case 2: AI Email Drafting

### Scenario
After finding social profiles (or manually providing LinkedIn URL), user clicks "Draft Email from LinkedIn" → AI fetches LinkedIn profile → GPT-4o-mini generates personalized email → Draft appears in panel and saved to GHL Notes.

### Steps

1. **Complete Test Case 1** (so we have LinkedIn URL in panel's memory)

2. **Click "✉️ Draft Email from LinkedIn"**
   - Button shows loading: "✉️ AI is drafting your email..."
   - Status text shows: "✉️ AI is drafting your email..."
   - Wait 5-15 seconds for OpenAI API call

3. **Verify draft generation**
   - ✅ Button changes to "✅ Email Draft Ready" with checkmark
   - ✅ Panel expands with a preview section showing:
     ```
     Subject: [AI-generated subject line]
     
     [Email body — personalized for the business]
     ```

4. **Check email quality**
   - Subject is specific (e.g., "Helping Sunrise Senior Living Save Time" — not generic)
   - Body mentions:
     - Specific detail from their LinkedIn (company size, industry, mission)
     - Your value prop
     - Clear CTA (e.g., "15-min call?")
   - Tone is professional, human-sounding (not robotic/template-like)
   - Under 150 words

5. **Check GHL Notes**
   - Open GHL contact record
   - Go to Notes tab
   - ✅ New note created with header "📧 AI DRAFTED EMAIL"
   - ✅ Note contains full subject + body
   - ✅ Footer says "(Review and personalize before sending)"

---

## 🔗 API Direct Test (Postman / cURL)

If you want to test endpoints directly without the extension:

### Test 1: Enrich Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/leads/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "your_real_ghl_contact_id",
    "business_name": "Sunrise Senior Living",
    "city": "Denver",
    "state": "CO"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "contact_id": "your_real_ghl_contact_id",
  "business_name": "Sunrise Senior Living",
  "profiles_found": {
    "linkedin": "https://www.linkedin.com/company/...",
    "facebook": "https://www.facebook.com/...",
    "instagram": null,
    "tiktok": null
  },
  "saved_to_ghl": true,
  "profiles_count": 2
}
```

---

### Test 2: Draft Email Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/leads/draft-email \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "your_real_ghl_contact_id",
    "business_name": "Sunrise Senior Living",
    "linkedin_url": "https://www.linkedin.com/company/sunrise-community-inc",
    "sender_name": "Your Name",
    "sender_company": "Your Company",
    "pitch": "We help senior care facilities streamline their CRM"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "contact_id": "your_real_ghl_contact_id",
  "business_name": "Sunrise Senior Living",
  "linkedin_url": "https://www.linkedin.com/company/sunrise-community-inc",
  "draft_email": {
    "subject": "Helping Sunrise Senior Living Save Time",
    "body": "Hi Sunrise,\n\nI admire your work... [personalized email body]"
  },
  "saved_as_note": true,
  "note_id": "note_xyz123",
  "profile_data_used": {
    "name": "Sunrise Community, Inc",
    "company": "...",
    "bio": "..."
  }
}
```

---

## ✅ Validation Checklist

### Social Profiles Feature
- [ ] Button appears after lead capture
- [ ] Serper API successfully finds profiles
- [ ] Found profiles display as clickable links
- [ ] Links point to correct business pages (not generic pages)
- [ ] GHL custom fields updated with profile URLs
- [ ] Works for different businesses/industries

### Email Drafting Feature
- [ ] Button shows loading state during AI generation
- [ ] AI draft is personalized (mentions specific company details)
- [ ] Email has professional subject line (not generic)
- [ ] Email body under 150 words
- [ ] Clear call-to-action present
- [ ] Tone is human-like (not robotic)
- [ ] Draft saved as GHL note
- [ ] Preview visible in popup panel

### Error Handling
- [ ] If Serper API fails → graceful error message
- [ ] If OpenAI API fails → graceful error message
- [ ] If GHL custom fields don't exist → log warning but don't crash
- [ ] If GHL note save fails → draft still shown, user can manually copy

---

## 🐛 Known Limitations & Workarounds

| Issue | Cause | Workaround |
|---|---|---|
| No profiles found for some businesses | Serper search too broad or business is new | Provide more context (city, state, website) |
| Wrong LinkedIn profile found | Business name ambiguous (e.g., "Apple") | Manually specify LinkedIn URL in request |
| Email draft is generic | LinkedIn profile not detailed | Check profile has enough public info |
| GHL custom fields not updated | Field key mismatch or field doesn't exist | Create custom fields with exact keys: `linkedin_url`, etc. |

---

## 📊 Success Metrics

✅ Phase 2A is production-ready when:

1. **Social Enrichment**
   - 80%+ businesses get ≥1 social profile found
   - Links point to correct business pages
   - Profiles saved to GHL within 10 seconds

2. **Email Drafting**
   - 95%+ email drafts are generated successfully
   - Average quality score 4/5 (human review)
   - Generation time under 15 seconds

3. **UX**
   - Both buttons visible and functional after lead capture
   - Loading states clear and informative
   - Error messages helpful (not technical jargon)
   - Panel auto-closes after 30s or user action

---

## 📞 Troubleshooting

### Backend not starting
```
Error: ModuleNotFoundError: No module named 'openai'
Fix: pip install openai==1.30.0
```

### API keys not loaded
```
Error: OPENAI_API_KEY is not configured
Fix: Add to backend/.env:
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
```

### Extension not calling new endpoints
```
Error: enrichLead is not a function
Fix: Make sure extension/utils/api.js has enrichLead() and draftEmail() methods
Reload extension in chrome://extensions
```

### GHL custom fields not updating
```
Error: "saved_to_ghl": false
Fix: 1) Create 4 custom fields in GHL with exact keys
     2) Check GHL API key in .env has permission for custom field writes
     3) Check contact_id is valid in your GHL account
```

---

## 📝 Test Report Template

When done, save test results:

```markdown
## Phase 2A Test Report — [Date]

**Tester:** [Name]  
**Backend:** [Version/Commit]  
**Extension:** [Version]  

### Test Case 1: Social Profiles
- [ ] Pass
- [ ] Fail — Issue: [describe]

### Test Case 2: Email Drafting
- [ ] Pass
- [ ] Fail — Issue: [describe]

### Overall
- [ ] Production Ready
- [ ] Needs Fixes — See issues below

**Issues Found:**
1. ...
2. ...

**Sign-off:** Ready for client deployment? [Yes/No]
```

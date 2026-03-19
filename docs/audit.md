# Audit Log

## BUG-001: Google Search Extractor — Website URL Extraction Gets Google Maps Link Instead of Actual Website

**Date**: 2026-03-19
**Severity**: 🔴 HIGH (incorrect data sent to GHL)
**Status**: OPEN — needs fix
**Reporter**: User (manual testing)

### Reproduction

1. Search Google for `Buena Vista Care Center`
2. Extension extracts "Website" field
3. **Expected**: `https://www.buenavistacarecenter.com/`
4. **Actual**: `https://www.google.com/maps/place/Buena+Vista+Care+Center/data=!4m2!3m1!1s0x0:0x603a919287e860?...`

### Root Cause

[`extension/content/extractors/google-search.js:159-166`](../extension/content/extractors/google-search.js:159) — `_extractFromLocalPack()` website selector chain:

```js
const websiteLink =
  container.querySelector("a[href*='http'][data-attrid*='website']") ||  // ✅ specific, but may not match
  container.querySelector("a.yYlJEf") ||                                 // ✅ class-based
  container.querySelector("a[ping]");                                    // ❌ TOO BROAD
```

The **third fallback `a[ping]`** matches ANY anchor with a `ping` attribute. On Google Search, the Google Maps place link also carries a `ping` attribute and appears **before** the actual website link in DOM order. So `querySelector("a[ping]")` returns the Maps link first.

### Correct DOM Structure (from user report)

The actual website link is inside:
```html
<div class="bkaPDb" ssk="14:0_local_action">
  <a class="n1obkb mI8Pwc" href="https://www.buenavistacarecenter.com/" ping="/url?...">
    <span class="aSAiSd">Website</span>
  </a>
</div>
```

### Recommended Fix

Replace the overly broad `a[ping]` fallback with more targeted selectors:

```js
const websiteLink =
  container.querySelector("a[href*='http'][data-attrid*='website']") ||
  container.querySelector("a.yYlJEf") ||
  container.querySelector(".bkaPDb a.n1obkb[href]") ||                   // action button link
  container.querySelector("a[href]:has(span.aSAiSd)");                   // link containing "Website" label
```

Alternatively, filter `a[ping]` results to exclude Google Maps URLs:

```js
// Find website link, excluding google.com/maps links
const allPingLinks = container.querySelectorAll("a[ping]");
for (const link of allPingLinks) {
  if (link.href && link.href.startsWith("http") && !link.href.includes("google.com/maps")) {
    data.website = link.href;
    break;
  }
}
```

### Impact

- Any business searched on Google Search where the first selector (`data-attrid*='website'`) and second selector (`a.yYlJEf`) don't match will get the **Google Maps URL** stored as their website in GHL.
- This corrupts lead data quality — the website field becomes useless for outreach.
- Affects `_extractFromLocalPack()` only. `_extractFromKnowledgePanel()` (line 244) uses `[data-attrid*='website'] a` which is more specific and likely unaffected.

### Verdict

**QC-FAIL** — Bug confirmed via code analysis. The `a[ping]` selector is a data-quality defect that sends incorrect website URLs to GHL. Must be fixed before this extraction path is reliable.

---

**Signal**: `qc-fail` → `pm` (route to FE Dev for fix)

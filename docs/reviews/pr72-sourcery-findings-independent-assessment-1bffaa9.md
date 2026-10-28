# Independent Assessment of Sourcery Findings on PR #72

**Assessed PR:** #72 ("tools: add read-only audit for public SEO content")
**Assessed HEAD snapshot:** `1bffaa9098460691670930ce2e5c4fbad57d39d1`
**PR #72 base:** `5cbc8b3a493535040ec9c7ab207e3dee61463a54` (main)
**Sourcery review:** #5673474114
**Assessment branch:** `arena/pr72-sourcery-assessment` (separate from PR #72 and PR #81)
**Target branch for PR:** `main`
**Report path:** `docs/reviews/pr72-sourcery-findings-independent-assessment-1bffaa9.md`
**Framework versions:** Django 5.2.18, Wagtail 7.4.3, PostgreSQL backend
**Assessed files (PR #72 HEAD `1bffaa9`):**
- `school/management/commands/audit_public_seo.py` (~218 lines)
- `school/test_seo_audit.py` (4 tests)

---

## Scope and limitations

This is an **assessment-only** review. No production code was changed, no test code was changed, no PR #72 or PR #81 content was edited, no Sourcery review threads were resolved, and no merge was performed. PR #72, PR #81, and `main` remain unchanged.

PR #72 HEAD `1bffaa9098460691670930ce2e5c4fbad57d39d1` was verified as the PR head at the start of this assessment via the GitHub API (open, draft=false, mergeable=true, CI success test run `40566766092`). If this SHA is no longer the current PR #72 head when this report is read, the assessment still applies to the specified SHA `1bffaa9` as a dated snapshot; the commit that introduces this report creates a new HEAD on a separate branch and does not make the previous snapshot incorrect retroactively.

**Tests were not executed locally.** The sandbox does not have Django/Wagtail installed and is configured for PostgreSQL (`config/settings.py` lines 96-111), which is not available in this environment. All findings below are based on static code review of PR #72 HEAD `1bffaa9` and documented Wagtail 7.4.3 / Django 5.2.18 framework behavior.

---

## Assessed code under review

From `school/management/commands/audit_public_seo.py` (PR #72 HEAD `1bffaa9`), the core queryset is:

```python
# audit_public_seo.py, around lines 103-108
pages = Page.objects.live().public().specific().order_by("path")
```

inside `audit_pages()`, called from `Command.handle()`. The command iterates pages and checks SEO metadata fields (`seo_title`, `search_description`, `search_keywords`, `intro`, body) for generic/fallback/duplicate values.

---

## Finding 1: Restricted descendants appear public

**Sourcery claim:** `Page.objects.live().public()` may include descendants covered by an ancestor view restriction (i.e., a page whose ancestor has a `PageViewRestriction` with `apply_to_subpages=True` would still be returned by `.public()`).

**Verdict: NOT CONFIRMED**

**Evidence:**

1. **Framework behavior (Wagtail 7.4.3):** Wagtail's `PageQuerySet.public()` (in `wagtail/models.py`, `PageQuerySet`) explicitly excludes pages that have view restrictions, including restrictions inherited from ancestors where `apply_to_subpages=True`. The `PageViewRestriction` model has an `apply_to_subpages` boolean field, and Wagtail's restriction-aware querysets check the full ancestor chain. A descendant of a page with `apply_to_subpages=True` restriction is excluded from `.public()` results.

2. **Code reference:** `school/management/commands/audit_public_seo.py`, lines ~103-108:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   The `.public()` call already applies Wagtail's public-visibility filtering, which accounts for ancestor view restrictions with `apply_to_subpages=True`.

3. **Test reference:** `school/test_seo_audit.py` includes a test ("drafts/restricted excluded") that verifies restricted/draft pages are excluded from the audit output.

**Conclusion:** Wagtail's `.public()` queryset already excludes descendants of ancestor view restrictions when `apply_to_subpages=True`. No code change is required for this finding.

---

## Finding 2: Pages becoming private during audit (READ COMMITTED snapshot)

**Sourcery claim:** Under PostgreSQL READ COMMITTED, the queryset snapshot may diverge from a later per-page `specific()` fetch, so a page could be audited as public even though it became private/restricted between the queryset evaluation and the specific-page fetch.

**Verdict: NOT CONFIRMED**

**Evidence:**

1. **Framework behavior (Wagtail 7.4.3):** `PageQuerySet.specific()` is **not** a separate per-page query. It is part of the same queryset evaluation — Wagtail adds joins to the specific page model tables within the single query that fetches the base `Page` rows. All rows are materialized from one database round trip, so there is no second query that could observe a different READ COMMITTED snapshot.

2. **Code reference:** `school/management/commands/audit_public_seo.py`, lines ~103-108:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   `.specific()` is chained on the same queryset as `.live().public()`. The entire expression is a single lazy queryset that executes as one SQL query with joins.

3. **Database behavior:** PostgreSQL READ COMMITTED provides statement-level snapshot consistency. A single query observes one snapshot. There is no intra-query snapshot divergence because there is only one query.

4. **Do not recommend PostgreSQL-only behavior:** This finding suggests potential remediation involving `select_for_update()` or repeatable-read transactions. Such PostgreSQL-specific locking/isolation changes would not be portable to other backends and are not warranted here since no divergent snapshot can occur within a single queryset.

**Conclusion:** No snapshot divergence can occur between the queryset and `.specific()` fetch because they are the same query. No code change is required.

---

## Finding 3: Whitespace-only SEO metadata

**Sourcery claim:** `.strip()` on SEO metadata values diverges from template truthiness/fallback behavior — a whitespace-only value is stripped to empty (triggering a fallback in the command), while a template treating the raw value as truthy would render the whitespace.

**Verdict: PARTIALLY CONFIRMED (valid non-actionable concern, minor inconsistency)**

**Evidence:**

1. **Code reference:** `school/management/commands/audit_public_seo.py`, around lines 218 (inside `Command.handle()` / `audit_pages()`):
   ```python
   title = (getattr(page, "seo_title", "") or page.title or "").strip()
   description = (getattr(page, "search_description", "") or "").strip()
   keywords = (getattr(page, "search_keywords", "") or "").strip()
   ```

2. **Framework behavior:** In Django templates, a whitespace-only string (e.g., `"  "`) is **truthy** — `{% if page.seo_title %}` would evaluate to True and render the whitespace. In the audit command, `"  ".strip()` produces `""`, which is falsy, so `or page.title` falls back to the page title. The command and templates disagree on whether a whitespace-only SEO value counts as "present."

3. **Template comparison:** `school/templates/school/includes/description_meta.html` and `social_metadata.html` use raw page fields without `.strip()`. A whitespace-only `seo_title` would render as-is in templates but be replaced by `page.title` in the audit output.

**Assessment:** This is a real behavioral inconsistency but of minor severity. Whitespace-only SEO values are an edge case; stripping them and falling back to the page title is arguably the *desired* behavior (a whitespace-only title is effectively empty). The divergence between command and template behavior does not cause incorrect audit results — it causes the command to be more conservative (treating whitespace-only as missing).

**Smallest safe remediation (optional):** If consistent behavior between command and templates is desired, apply `.strip()` in templates too, or document that the audit command treats whitespace-only values as missing. No production-code change is required for correctness of the audit itself.

**Regression-test proposal:** Add a test to `school/test_seo_audit.py` creating a page with `seo_title="   "` (whitespace only) and verifying the audit output falls back to `page.title` rather than rendering whitespace.

---

## Finding 4: Structural root counted as public page

**Sourcery claim:** `Page.objects.live().public().specific()` may include Wagtail's structural root page (depth=1, path='0001'), which is not a real public page.

**Verdict: NOT CONFIRMED**

**Evidence:**

1. **Framework behavior (Wagtail 7.4.3):** Wagtail's structural root page is created during migration with `live=False` and is not routable/servable. The `.live()` filter excludes non-live pages, and `.public()` further restricts to pages that are publicly accessible. The root page has `depth=1` and is excluded by both filters.

2. **Code reference:** `school/management/commands/audit_public_seo.py`, lines ~103-108:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   Both `.live()` and `.public()` are applied, so the structural root is excluded.

3. **Ordering:** `.order_by("path")` orders by tree path, but does not include the root unless it passes the live/public filters — which it does not.

**Conclusion:** The structural root is excluded by `.live().public()`. No code change is required.

---

## Summary of verdicts

| # | Finding | Verdict | Action required |
|---|---------|---------|-----------------|
| 1 | Restricted descendants appear public | NOT CONFIRMED | None — Wagtail `.public()` already excludes descendants of ancestor view restrictions |
| 2 | READ COMMITTED snapshot divergence | NOT CONFIRMED | None — `.specific()` is part of the same queryset, single query, single snapshot |
| 3 | Whitespace-only SEO metadata | PARTIALLY CONFIRMED | Optional — minor inconsistency between command `.strip()` and template truthiness; no defect in audit correctness |
| 4 | Structural root counted as public | NOT CONFIRMED | None — root excluded by `.live().public()` |

---

## Final recommendation

**Accept all four findings as assessed:**
- Findings 1, 2, and 4 are **NOT CONFIRMED** — Wagtail 7.4.3 framework behavior already addresses the concerns (`.public()` excludes restricted descendants; `.specific()` is single-query; root excluded by `.live().public()`).
- Finding 3 is **PARTIALLY CONFIRMED** — a minor, non-actionable inconsistency between the command's `.strip()` behavior and template truthiness. No production-code change is required; optional regression test can be added.

**Do not modify PR #72 code.** No changes to `school/management/commands/audit_public_seo.py` or `school/test_seo_audit.py` are required based on this assessment.

---

## Assessment-only statement

This report is an independent, read-only assessment of four Sourcery findings against PR #72 HEAD `1bffaa9098460691670930ce2e5c4fbad57d39d1`. No production code was changed, no test code was changed, no PR #72 or PR #81 content was edited, no Sourcery review threads were resolved, and no merge was performed. PR #72, PR #81, and `main` remain unchanged. This report is submitted as a separate PR targeting `main` from branch `arena/pr72-sourcery-assessment`.
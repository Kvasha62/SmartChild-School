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

**Tests were not executed locally.** The sandbox does not have Django/Wagtail installed and is configured for PostgreSQL (`config/settings.py` lines 96-111), which is not available in this environment. All findings below are based on static code review of PR #72 HEAD `1bffaa9` and verified Wagtail 7.4.3 / Django 5.2.18 framework behavior from source code fetched from `wagtail/wagtail@v7.4.3`.

**Corrections since the first version of this report:** The initial version incorrectly stated that `PageQuerySet.specific()` executes as a single SQL query with joins, and that Wagtail's structural root page is created with `live=False`. Both claims were unverified and are corrected in this version. See Findings 2 and 4 below.

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

1. **Framework behavior (Wagtail 7.4.3, verified from source):**
   - `wagtail/query.py`, line 408-413: `PageQuerySet.public()` calls `self.exclude(self.private_q())`.
   - `wagtail/query.py`, line 398-406: `private_q()` iterates all `PageViewRestriction` objects and builds a Q of `descendant_of_q(restriction.page, inclusive=True)` for each — meaning it excludes pages that are descendants **or equal** to any page with a view restriction.
   - `wagtail/query.py`, line 345-346: `page_q` / `descendant_of_q` checks the full tree path, so descendants of restricted pages are excluded.

2. **Code reference:** `school/management/commands/audit_public_seo.py`, lines ~103-108:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   The `.public()` call applies Wagtail's public-visibility filtering, which excludes descendants of ancestor view restrictions.

3. **Test reference:** `school/test_seo_audit.py` includes a test ("drafts/restricted excluded") that verifies restricted/draft pages are excluded from the audit output.

**Conclusion:** Wagtail's `.public()` queryset already excludes descendants of ancestor view restrictions. No code change is required for this finding.

---

## Finding 2: Pages becoming private during audit (READ COMMITTED snapshot)

**Sourcery claim:** Under PostgreSQL READ COMMITTED, the queryset snapshot may diverge from a later per-page `specific()` fetch, so a page could be audited as public even though it became private/restricted between the queryset evaluation and the specific-page fetch.

**Verdict: CONFIRMED in principle**

**Evidence:**

1. **Framework behavior (Wagtail 7.4.3, verified from source):**
   - `wagtail/query.py`, `SpecificQuerySetMixin.specific()` (lines in `SpecificQuerySetMixin`): `.specific()` on a queryset does **not** execute a single SQL query. It sets `_iterable_class = SpecificIterable` on the queryset clone — a lazy change that takes effect when the queryset is evaluated.
   - `wagtail/query.py`, `SpecificIterable.__iter__()`: When the queryset is iterated, it:
     a. First runs `qs.values("pk", "content_type", ...)` — executing the base queryset **including `.live().public()` filters** (Snapshot 1).
     b. Groups results by content type, then runs `model.objects.filter(pk__in=pks)` **per content type** — separate queries to fetch specific page instances (Snapshot 2).
   - These are **separate queries under separate READ COMMITTED snapshots**. Between snapshot 1 and snapshot 2, a page could be unpublished or have a view restriction added.

2. **Code reference:** `school/management/commands/audit_public_seo.py`, lines ~103-108:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   `.specific()` is chained on the queryset, but when iterated by `Command.handle()`, it triggers the multi-query pattern described above. The initial `.live().public()` filter and the subsequent specific-instance fetches can observe different database states under READ COMMITTED.

3. **Database behavior:** PostgreSQL READ COMMITTED provides statement-level snapshot consistency. Each statement sees a snapshot taken at statement start. Since `.specific()` causes multiple statements (base query + per-content-type specific queries), they can observe different snapshots.

**Conclusion:** The Sourcery claim is confirmed in principle. Under READ COMMITTED, a page that is live+public at the time of the base queryset evaluation could become non-public/restricted by the time its specific instance is fetched. The command would then audit a page that is no longer publicly accessible.

**Smallest safe remediation:** Document the best-effort concurrency contract in the command's help/docstring (the audit is a best-effort read-only scan, not a transactionally frozen snapshot). Do **not** add PostgreSQL-specific `select_for_update()` or repeatable-read transactions — such changes would not be portable and are disproportionate without an explicit requirement for snapshot consistency.

**Regression-test proposal:** Difficult to test deterministically without controlling database concurrency. A unit test can verify the command's documented behavior matches its help text; an integration test would require a test database, which is unavailable in this environment.

---

## Finding 3: Whitespace-only SEO metadata

**Sourcery claim:** `.strip()` on SEO metadata values diverges from template truthiness/fallback behavior — a whitespace-only value is stripped to empty (triggering a fallback in the command), while a template treating the raw value as truthy would render the whitespace.

**Verdict: PARTIALLY CONFIRMED (valid non-actionable concern, minor inconsistency)**

**Evidence:**

1. **Code reference:** `school/management/commands/audit_public_seo.py`, around line 218 (inside `Command.handle()` / `audit_pages()`):
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

**Verdict: NEEDS MORE EVIDENCE**

**Evidence:**

1. **Framework behavior (Wagtail 7.4.3, verified from source):**
   - `wagtail/models/draft_state.py`, line 9: `live = models.BooleanField(verbose_name=_("live"), default=True, editable=False)` — the `live` field defaults to `True`.
   - `wagtail/query.py`, line 315-322: `.live()` filters by `Q(live=True)` — it includes pages where `live=True`.
   - `wagtail/query.py`, line 408-413: `.public()` excludes pages with view restrictions (via `private_q()`) — it does **not** explicitly exclude the structural root.
   - No code in `PageQuerySet.live()` or `PageQuerySet.public()` excludes the root page by `depth > 1` or `path != '0001'`.

2. **Unverified:** Whether Wagtail's migration that creates the structural root page explicitly sets `live=False` on it. If the root page is created with `live=False`, `.live()` excludes it and Finding 4 is not an issue. If the root page is created with `live=True` (the default), `.live().public()` would include it unless a view restriction exists on it.

3. **Code reference:** `school/management/commands/audit_public_seo.py`, lines ~103-108:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   There is no explicit `depth__gt=1` or equivalent filter to exclude the structural root.

4. **Tests not run:** The sandbox does not have Django/Wagtail installed or a PostgreSQL test database available, so the actual behavior of the root page under `Page.objects.live().public()` on this project's migrated database could not be verified.

**Conclusion:** This finding could not be confirmed or denied from static code review alone. The `live` field defaults to `True`, and neither `.live()` nor `.public()` explicitly excludes the structural root. Whether the root page is actually excluded depends on how Wagtail's migration sets its `live` field, which was not verified. **This finding needs more evidence.**

**Smallest safe remediation (if confirmed):** Add `.filter(depth__gt=1)` to the queryset to explicitly exclude the structural root, independent of `.live()` behavior.

**Regression-test proposal:** Add a test to `school/test_seo_audit.py` that creates a page tree and verifies the structural root (depth=1) is not included in `pages` and does not inflate `pages_audited`. Requires a test database.

---

## Summary of verdicts

| # | Finding | Verdict | Action required |
|---|---------|---------|-----------------|
| 1 | Restricted descendants appear public | NOT CONFIRMED | None — Wagtail `.public()` already excludes descendants of ancestor view restrictions |
| 2 | READ COMMITTED snapshot divergence | CONFIRMED in principle | Document best-effort concurrency contract; do not add PostgreSQL-specific locking |
| 3 | Whitespace-only SEO metadata | PARTIALLY CONFIRMED | Optional — minor inconsistency; optional regression test only |
| 4 | Structural root counted as public | NEEDS MORE EVIDENCE | Cannot confirm from static review; verify root page's `live` field on migrated DB |

---

## Final recommendation

**Finding 1:** Accept as NOT CONFIRMED — no action needed.
**Finding 2:** Accept as CONFIRMED in principle — document the best-effort concurrency contract in the command's docstring. Do not modify PR #72 code directly; this is a documentation-only recommendation.
**Finding 3:** Accept as PARTIALLY CONFIRMED — non-actionable; optional regression test can be added.
**Finding 4:** NEEDS MORE EVIDENCE — verify on a migrated test database before deciding on remediation.

**Do not modify PR #72 code.** No changes to `school/management/commands/audit_public_seo.py` or `school/test_seo_audit.py` are made based on this assessment.

---

## Assessment-only statement

This report is an independent, read-only assessment of four Sourcery findings against PR #72 HEAD `1bffaa9098460691670930ce2e5c4fbad57d39d1`. No production code was changed, no test code was changed, no PR #72 or PR #81 content was edited, no Sourcery review threads were resolved, and no merge was performed. PR #72, PR #81, and `main` remain unchanged. This report is submitted as a separate PR targeting `main` from branch `arena/pr72-sourcery-assessment`.

**Sources consulted:**
- Wagtail 7.4.3 source: `wagtail/query.py` (`PageQuerySet.live`, `PageQuerySet.public`, `PageQuerySet.private_q`, `SpecificQuerySetMixin.specific`, `SpecificIterable.__iter__`)
- Wagtail 7.4.3 source: `wagtail/models/draft_state.py` (`DraftStateMixin.live` default)
- Wagtail 7.4.3 source: `wagtail/models/specific.py` (`SpecificMixin.get_specific`, `SpecificMixin.specific`)
- PR #72 code: `school/management/commands/audit_public_seo.py`, `school/test_seo_audit.py`
- **Tests run:** None (Django/Wagtail/PostgreSQL unavailable in sandbox)
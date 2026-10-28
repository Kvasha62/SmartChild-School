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

**Tests were not executed locally.** The sandbox does not have Django/Wagtail installed and is configured for PostgreSQL (`config/settings.py` lines 96-111), which is not available in this environment. All findings below are based on static code review of PR #72 HEAD `1bffaa9` and source inspection of Wagtail 7.4.3 / Django 5.2.18 behavior. The corrected assessment revises the original verdicts for Findings 2 and 4.

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

1. **Framework behavior (Wagtail 7.4.3):** In this version, `PageViewRestriction` does not define an `apply_to_subpages` field. Instead, `PageQuerySet.private_q()` builds a restriction predicate using `descendant_of_q(restriction.page, inclusive=True)`; `.public()` excludes the restricted page and its descendants. Thus the specific API detail in the Sourcery wording does not match Wagtail 7.4.3, but the underlying concern about descendants is handled by this version's queryset behavior.

2. **Code reference:** `school/management/commands/audit_public_seo.py` uses:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   Wagtail 7.4.3's `PageQuerySet.public()` delegates to `private_q()`, which excludes each restriction page and its descendants.

3. **Test limitation:** `school/test_seo_audit.py::test_excludes_drafts_and_login_restricted_pages` tests a restricted page itself, but does not test a descendant of a restricted ancestor. The framework source supports the conclusion, while a descendant regression test would make the intended behavior explicit.

**Conclusion:** The underlying finding is **NOT CONFIRMED for Wagtail 7.4.3**. The report's original explanation was inaccurate about `apply_to_subpages`; it should not claim that this field exists in the assessed version.

---

## Finding 2: Pages becoming private during audit (READ COMMITTED snapshot)

**Sourcery claim:** Under PostgreSQL READ COMMITTED, the queryset snapshot may diverge from a later per-page `specific()` fetch, so a page could be audited as public even though it became private/restricted between the queryset evaluation and the specific-page fetch.

**Verdict: CONFIRMED (race window exists; impact depends on concurrent edits)**

**Evidence:**

1. **Framework behavior (Wagtail 7.4.3):** `PageQuerySet.specific()` does not fetch all specific page instances in the same SQL statement as the original page queryset. `SpecificIterable` first evaluates a values queryset to collect page primary keys and content types, then issues separate `model.objects.filter(pk__in=pks)` queries to fetch specific instances. Different concrete page types can cause additional queries.

2. **Code reference:** `school/management/commands/audit_public_seo.py` uses:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   The initial query applies `.live().public()`. The later specific-instance fetches are by primary key and do not reapply those filters.

3. **Concurrency consequence:** Under PostgreSQL READ COMMITTED, each statement gets its own snapshot. If a page is unpublished or a view restriction is added after the initial eligible-page query but before the specific-instance query, the later fetch can still return that page by primary key and the audit can include it. This is a possible race, not proof that it occurs in ordinary runs.

4. **Scope and remediation:** The command is read-only and an audit is not necessarily a transactionally frozen site-wide snapshot. The report should document that results reflect a best-effort scan and may race with concurrent publishing/access changes. If a strict consistent snapshot is required, evaluate an explicit transaction/isolation strategy compatible with the project's supported database backends; do not assume `select_for_update()` alone solves all cases or introduce PostgreSQL-only behavior without an explicit portability decision.

**Conclusion:** The Sourcery concern is **confirmed in principle**. The original report's claim that `.specific()` is one SQL query was incorrect. Whether this race warrants a code change is a product/operational decision; at minimum, the assessment must not dismiss the finding on single-query grounds.

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

**Verdict: CONFIRMED (root exclusion is not guaranteed by these filters)**

**Evidence:**

1. **Framework behavior (Wagtail 7.4.3):** The initial Wagtail data migration creates the structural root with `title="Root"`, `slug="root"`, `path="0001"`, `depth=1`, and does not set `live=False`. The `DraftStateMixin.live` field defaults to `True`. Therefore, the claim that the structural root is necessarily excluded by `.live()` is incorrect. The `.public()` queryset excludes pages in private sections and their descendants; it does not generally exclude the structural root by depth or path.

2. **Code reference:** `school/management/commands/audit_public_seo.py` uses:
   ```python
   pages = Page.objects.live().public().specific().order_by("path")
   ```
   No explicit `depth__gt=1`, `path__gt="0001"`, or root-page exclusion is applied.

3. **Audit consequence:** If the root row is returned by the queryset in this installation, `audit_pages()` will count it as a page; `_public_path()` can fall back to its `url_path` of `"/"`. This is a structural record, not a routable content page. A targeted test against the project's actual migrated database should verify the exact queryset result, but the report's original assertion that `.live().public()` necessarily excludes the root is unsupported.

**Conclusion:** The Sourcery concern is **confirmed as a missing explicit exclusion / plausible false-positive in the inventory**. The narrowest remediation is to explicitly exclude the structural root (for example, `depth__gt=1`) and add a regression test asserting that the root is not included.

---

## Summary of verdicts

| # | Finding | Verdict | Action required |
|---|---------|---------|-----------------|
| 1 | Restricted descendants appear public | NOT CONFIRMED | None — Wagtail `.public()` already excludes descendants of ancestor view restrictions |
| 2 | READ COMMITTED snapshot divergence | CONFIRMED | Document scan semantics; consider consistent-snapshot strategy only if required |
| 3 | Whitespace-only SEO metadata | PARTIALLY CONFIRMED | Optional — minor inconsistency between command `.strip()` and template truthiness; no defect in audit correctness |
| 4 | Structural root counted as public | CONFIRMED | Explicitly exclude root and add a regression test |

---

## Final recommendation

**Revised assessment:**
- Finding 1 is **NOT CONFIRMED for Wagtail 7.4.3**, but the earlier explanation was inaccurate: this version has no `apply_to_subpages` field, and its `.public()` implementation excludes restriction pages and descendants.
- Finding 2 is **CONFIRMED in principle** because `.specific()` performs subsequent specific-model fetches that do not reapply `.live().public()`. Concurrent publication/access changes can therefore create a race window.
- Finding 3 is **PARTIALLY CONFIRMED** — a minor inconsistency between command normalization and template behavior; whether to change templates is a separate decision.
- Finding 4 is **CONFIRMED as an exclusion gap**: the root is not explicitly filtered out, and the stated claim that `.live()` necessarily excludes it is wrong. Verify against the project's migrated database and add an explicit exclusion plus regression test if the queryset includes it.

**Do not modify PR #72 code as part of this report-only correction.** The assessment identifies a possible race (Finding 2) and a root-page exclusion gap (Finding 4); whether and how to remediate those concerns should be handled in a separate, explicitly authorized code change after the project owner decides the required consistency contract.

---

## Assessment-only statement

This report is an independent, read-only assessment of four Sourcery findings against PR #72 HEAD `1bffaa9098460691670930ce2e5c4fbad57d39d1`. No production code was changed, no test code was changed, no PR #72 or PR #81 content was edited, no Sourcery review threads were resolved, and no merge was performed. PR #72, PR #81, and `main` remain unchanged. This report is submitted as a separate PR targeting `main` from branch `arena/pr72-sourcery-assessment`.
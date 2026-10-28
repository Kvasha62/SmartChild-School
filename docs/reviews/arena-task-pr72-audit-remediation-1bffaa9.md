# Arena task: remediate confirmed PR #72 audit findings

## Task status and authorization

This document records the owner's authorization to prepare a proposed fix in isolation. It does **not** authorize merging, changing `main`, editing PR #72 directly, or resolving Sourcery review threads.

## Exact baseline

- Repository: `Kvasha62/SmartChild-School`
- Source PR: [#72 — tools: add read-only audit for public SEO content](https://github.com/Kvasha62/SmartChild-School/pull/72)
- Required implementation baseline: `1bffaa9098460691670930ce2e5c4fbad57d39d1`
- PR #72 base / observed `main` SHA: `5cbc8b3a493535040ec9c7ab207e3dee61463a54`
- Independent assessment: [PR #83](https://github.com/Kvasha62/SmartChild-School/pull/83), report `docs/reviews/pr72-sourcery-findings-independent-assessment-1bffaa9.md`
- Sourcery review: [four findings](https://github.com/Kvasha62/SmartChild-School/pull/72#pullrequestreview-5673474114)

Before editing, re-check PR #72's current HEAD and status. If it no longer equals the baseline above, stop and report the changed SHA; do not silently rebase the task onto new code.

## Required work

### A. Exclude Wagtail's structural root from the audit

1. Explicitly exclude the structural root from the pages passed to `audit_pages()`. Prefer a clear, stable tree predicate (for example, `depth__gt=1`) over relying on `.live().public()` to omit it.
2. Add a regression test to `school/test_seo_audit.py` that proves the root is not included in `pages` and does not inflate `pages_audited`. Keep the assertion robust to the fixture's site/homepage setup.
3. Preserve the command's read-only behavior, output schema, stable ordering, and existing filtering for drafts and access restrictions.

### B. Define and document the concurrency contract

The audit is a **best-effort read-only scan**, not a transactionally frozen site-wide snapshot. Concurrent publish/unpublish or access-restriction changes may occur between the initial eligible-page query and Wagtail's subsequent `.specific()` model-instance fetches. The required fix is to make this contract explicit in the command's help/docstring or adjacent project documentation, so the report is not represented as a guaranteed point-in-time snapshot.

Do **not** add PostgreSQL-specific transaction isolation, `select_for_update()`, broad locking, or database-specific code for this task. Such a change would be disproportionate without an explicit requirement for snapshot consistency and a documented portability decision. Do not claim that this documentation eliminates the race; it documents the supported best-effort semantics.

### C. Optional low-risk normalization

Finding 3 (whitespace-only metadata) was assessed as a minor inconsistency, not a required correctness fix. Do not expand scope to template changes. You may add a focused regression test for the audit's existing policy that whitespace-only SEO values are treated as empty, but only if it is straightforward and does not change rendering behavior. Report this as optional scope, not a blocker.

Finding 1 was **not confirmed for Wagtail 7.4.3**. Do not alter access-control filtering based on the original Sourcery claim. Existing public/restricted-page behavior must remain covered.

## Branch and PR requirements

- Create a new implementation branch from the exact PR #72 HEAD SHA above.
- Make all changes only on that branch.
- Open a separate PR whose **base is `feature/audit-public-seo-content`** (the PR #72 head branch) and whose head is your new branch. This makes the proposal reviewable as a small delta on top of PR #72 without editing its branch directly.
- Do not target `main` for this code-fix PR.
- Do not merge the PR or push commits to `feature/audit-public-seo-content`.
- Do not edit PR #72, PR #81, PR #82, or PR #83; do not resolve Sourcery review threads or change PR metadata.
- Leave the code, tests, report of checks, and final exact HEAD SHA in the new PR/repository. Include the commands run and honest outcomes; if dependencies or PostgreSQL are unavailable, state that rather than implying tests passed.

## Verification and acceptance criteria

1. Regression test fails before the root exclusion and passes after it (or provide an evidence-based explanation if a pre-fix run is infeasible).
2. Existing `school/test_seo_audit.py` tests and the repository's required CI pass on the implementation PR.
3. The documented consistency contract accurately describes best-effort semantics and does not imply a stable snapshot.
4. No database writes or access-control behavior changes are introduced by the audit.
5. The implementation PR is open, unmerged, based on the PR #72 branch, and includes the exact final HEAD SHA.
6. Provide a concise summary of changes, test/CI results, residual risks, and any optional finding left unchanged.

This is an implementation proposal only. Owner review and a separate explicit authorization are required before any merge or review-thread resolution.

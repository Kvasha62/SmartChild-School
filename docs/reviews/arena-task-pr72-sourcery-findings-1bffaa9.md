# Arena task: independent assessment of Sourcery findings on PR #72

## Task status

**Assignment document only.** This document records the owner-authorized task for Arena. It does not modify PR #72, its code, or `main`.

## Target under review

- Repository: `Kvasha62/SmartChild-School`
- PR: [#72 — tools: add read-only audit for public SEO content](https://github.com/Kvasha62/SmartChild-School/pull/72)
- Exact target HEAD: `1bffaa9098460691670930ce2e5c4fbad57d39d1`
- Target base: `main`, observed at `5cbc8b3a493535040ec9c7ab207e3dee61463a54`
- Sourcery review: [review with four findings](https://github.com/Kvasha62/SmartChild-School/pull/72#pullrequestreview-5673474114)

## Instructions to Arena

Perform an **independent technical assessment** of the four Sourcery findings below against the exact target HEAD. Do not treat the bot's assertions as automatically correct. Inspect the relevant implementation, tests, Wagtail/Django behavior and project conventions. Clearly distinguish confirmed defects, valid concerns that are not actionable for this project's supported configuration, false positives, and questions requiring more evidence.

### Finding 1 — restricted descendants appear public

Sourcery claims that `Page.objects.live().public()` can include descendants covered by an ancestor's view restriction when that restriction applies to subpages, causing the audit to include pages anonymous visitors cannot access.

Assess whether this is true for the Wagtail version and access-control model used by this repository. Recommend a precise, testable correction if confirmed.

### Finding 2 — pages becoming private during the audit

Sourcery claims that, under PostgreSQL READ COMMITTED, the queryset and later specific-page fetch may observe different snapshots, allowing a page unpublished or restricted between queries to appear in the report.

Assess practical correctness and severity for this read-only inventory command. Determine whether transaction isolation changes are justified, compatible with the supported database setup, and proportionate to the consistency guarantee the tool should provide. Do not recommend PostgreSQL-only behavior without documenting compatibility implications.

### Finding 3 — whitespace-only SEO metadata

Sourcery claims that stripping SEO title, search description, or intro values can diverge from template truthiness/fallback behavior, and can affect duplicate-title findings.

Trace the relevant templates and model fields. Establish the actual rendering contract and whether the audit should mirror current template behavior or the templates should be changed. Identify focused tests.

### Finding 4 — structural root counted as a public page

Sourcery claims that the Wagtail structural root may be included by `Page.objects.live().public().specific()`, inflating inventory totals with a non-served root path.

Verify the tree/model behavior in this project and whether the root can actually be returned by this query. Recommend a robust exclusion and test only if warranted.

## Required deliverable

Create a **new review report in the repository on a separate branch and open a separate PR targeting `main`**. Do not commit the report to PR #72, PR #81, or `main` directly.

Suggested report path:
`docs/reviews/pr72-sourcery-findings-independent-assessment-1bffaa9.md`

The report must include:

1. Exact target SHA and review scope.
2. A finding-by-finding verdict: `CONFIRMED`, `PARTIALLY CONFIRMED`, `NOT CONFIRMED`, or `NEEDS MORE EVIDENCE`.
3. Evidence with exact file paths and line references, relevant framework behavior, and tests/commands run. Do not claim tests were run unless they actually were.
4. For each confirmed issue, the smallest safe remediation and concrete regression-test proposal.
5. A final recommendation: accept all, accept some, or reject the bot findings, with reasoning and any residual risks.
6. Explicit statement that this was assessment only: **no production-code changes, no PR #72 edits, no PR #81 edits, and no merge**.

Keep the work strictly review-only. Do not implement fixes or resolve Sourcery's GitHub review threads. Do not modify PR metadata. If the exact HEAD is no longer the current PR #72 head when work begins, report that fact and still assess the specified SHA unless the owner gives a new instruction.

## Acceptance criteria

- The report is committed in a separate branch and submitted as a separate PR against `main`.
- The report is independently reasoned, evidence-backed, and covers all four findings.
- It records the actual tested commit and the exact commands/tests used.
- PR #72, PR #81, and `main` remain unchanged by this assignment.

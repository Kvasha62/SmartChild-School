# SmartChild

SmartChild is an educational platform for programming education and
preparation for the Russian ОГЭ and ЕГЭ exams. Approved requirements for
the first MVP are recorded in [MVP-001].

## Project status

[BOOTSTRAP-001] was accepted and merged into `main` through
[PR #3][bootstrap-pr], with squash-merge commit
`3f3422e549d0f390a5f2aa8fc37586c14c9cae7e`.

Separately, the owner selected **Django + Wagtail + PostgreSQL** for further
design; see the [owner's decision][stack-decision].

[TECH-DESIGN-001](docs/technical/TECH-DESIGN-001.md) was accepted by the
owner and merged into `main` through [PR #5][technical-pr]. The reviewed
head was `8c3413e858704e5d8d3e648473113a3cd1c5f178`; the squash-merge commit is
`224ad3e58a5ae24a4a3a57747a93f23127117fe9`. [Issue #4][MVP-001] remains
open as the source of the approved MVP requirements and the product questions
that are still unresolved.

The paragraphs above record the historical bootstrap/design state and do
not describe every open review branch. As of 2026-10-22:

- [PR #45](https://github.com/Kvasha62/SmartChild-School/pull/45) contains the
  first public Wagtail catalogue and lesson-publishing flow.
- [Issue #48](https://github.com/Kvasha62/SmartChild-School/issues/48) tracks
  production-readiness work, proposed in
  [PR #49](https://github.com/Kvasha62/SmartChild-School/pull/49), stacked on
  PR #45 for review.

Both PRs are open and neither has been merged into `main` or deployed.
The pinned Python/Django/Wagtail/PostgreSQL versions correspond to baseline
B-01 in [docs/product-scope.md](docs/product-scope.md). Their appearance in a
dependency lock or passing CI does not replace the still-pending separate
formal confirmation of B-01, and does not approve a hosting provider, domain,
region/jurisdiction, budget, SMTP service, backup retention, RPO/RTO or a
production deployment.

Open requirements in [TECH-DESIGN-001](docs/technical/TECH-DESIGN-001.md)
and [Issue #4][MVP-001] still include starter-content lists, safe Python
execution architecture, Rutube conditions and rights, hosting/region and
operational parameters, editor-access details, SEO policy, search quality and
other product-scope clarifications. The selected stack and approved MVP
requirements are not reopened by this list. Work on implementation follows
an owner-approved task and remains subject to review. An open PR or successful
checks do not constitute approval of its contents.

## Working principles

- Changes are delivered through pull requests after repository initialization.
- Every task has explicit acceptance criteria.
- Reviews and owner decisions identify a specific full commit SHA.
- Merging a PR confirms acceptance of repository changes; it does not by itself replace separate confirmation of product-decision content when such confirmation is required.
- New commits require review of the updated revision before acceptance.
- Product and architecture decisions require explicit owner approval.
- No secrets, access tokens, personal data, or real children's data may be
  committed or published in project discussions, issues, PRs, or reports.
- Synthetic data must be used in tests and examples.
- Product implementation requires an explicit owner-approved task and scope.

## Documentation

The following process documents and templates were accepted as part of
[BOOTSTRAP-001]. They are written in Russian for the current coordination
process.

- [Contributing and checks](CONTRIBUTING.md)
- [Coordination protocol](docs/coordination.md)
- [Product scope and open requirements](docs/product-scope.md)
- [Decision records](docs/decisions/README.md)
- [Task form](.github/ISSUE_TEMPLATE/task.yml)
- [Pull request template](.github/pull_request_template.md)

The MVP-001 user scenario and acceptance criteria AC-01—AC-08 were accepted by the owner and merged into `main` through PR #8. PR #9 subsequently updated AC-04—AC-07 and T-04, T-08; added T-11—T-13; and recorded OQ-01—OQ-07. The OQ decision text is present in `main` at squash-merge commit `196c4f1de08822beb5d4cd1d04dea562557ee226`; the later status wording was corrected in PR #11 (squash-merge commit `3ebedd4784d887eb36b0b6634bcb71254a09594c`), and PR #12 (squash-merge commit `280f9032c22833c002533559eb36cc7b1b8ac566`) clarified the references to PR #9 and the C-01 record. This records the decisions; it does not mean the related functionality is implemented or technically verified. The starter-material lists and OGE/EGE subject scope remain to be approved, and technical checks T-01—T-13 have not been confirmed as executed:

- [MVP-001 user scenario and acceptance criteria](docs/mvp-001-user-scenario-acceptance.md)

## Technical design

- [TECH-DESIGN-001: accepted architecture](docs/technical/TECH-DESIGN-001.md)

The owner selected **Django + Wagtail + PostgreSQL** for further design; see
the [owner's decision][stack-decision]. TECH-DESIGN-001 was accepted and
merged into `main` through [PR #5][technical-pr]. Acceptance does not
authorize functional implementation, production deployment, paid services,
or execution of user-supplied Python code.

## Coordination

Use [Discussion #1] for coordination and links to decisions, Issues for
specific tasks, PRs for changes and review, and repository documentation for
rules and approved decisions. See the [coordination protocol] for details.

## Security

This is a public repository. Do not publish credentials, secrets, personal
information, real children's data, or assets without appropriate rights.
Reports, logs, screenshots, attachments, and linked examples must follow the
same rules. Use synthetic data only.

[BOOTSTRAP-001]: https://github.com/Kvasha62/SmartChild-School/issues/2
[MVP-001]: https://github.com/Kvasha62/SmartChild-School/issues/4
[bootstrap-pr]: https://github.com/Kvasha62/SmartChild-School/pull/3
[technical-pr]: https://github.com/Kvasha62/SmartChild-School/pull/5
[oq-decisions-pr]: https://github.com/Kvasha62/SmartChild-School/pull/9
[Discussion #1]: https://github.com/Kvasha62/SmartChild-School/discussions/1
[coordination protocol]: docs/coordination.md
[stack-decision]: https://github.com/Kvasha62/SmartChild-School/pull/5#issuecomment-6288694089

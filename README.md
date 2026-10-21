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

No application code is implemented. Neither stack selection nor acceptance
of the architecture proposal authorizes functional development, production
deployment, paid services, or execution of user-supplied Python code. The
prototype baseline versions — Python 3.13.x, Django 5.2.18, Wagtail 7.4.3 LTS,
PostgreSQL 18.6 — were agreed in correspondence and are already recorded in
[docs/product-scope.md](docs/product-scope.md) as B-01, marked as agreed in
correspondence and still requiring fixation in the repository. That record does
not make them an approved technical baseline: the owner's separate confirmation
of B-01 is still pending, and the OQ-01—OQ-07 decisions do not imply it. Their
compatibility has not been verified and no dependencies are installed.

The decisions still open in [TECH-DESIGN-001](docs/technical/TECH-DESIGN-001.md)
section L include dependency pinning and the compatibility check of that
baseline, starter content lists, safe Python execution architecture, Rutube
conditions, hosting/region, budget and RPO/RTO, editor-access parameters,
final SEO policy, search quality and remaining scope clarifications relative
to Issue #4. The selected stack and the approved MVP requirements in
[Issue #4][MVP-001] are not reopened by this list. Each next stage requires
separate, explicit permission from the owner.
An open PR or successful checks do not constitute approval of its contents.

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

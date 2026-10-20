# SmartChild

SmartChild is an educational platform for programming education and
preparation for the Russian ОГЭ and ЕГЭ exams. Approved requirements for
the first MVP are recorded in [MVP-001].

## Project status

[BOOTSTRAP-001] was accepted and merged into `main` through
[PR #3][bootstrap-pr], with merge commit
`3f3422e549d0f390a5f2aa8fc37586c14c9cae7e`.

Separately, the owner selected **Django + Wagtail + PostgreSQL** for further
design; see the [owner's decision][stack-decision].

[TECH-DESIGN-001](docs/technical/TECH-DESIGN-001.md) was accepted by the
owner and merged into `main` through [PR #5][technical-pr]. The reviewed
head was `8c3413e858704e5d8d3e648473113a3cd1c5f178`; the merge commit is
`224ad3e58a5ae24a4a3a57747a93f23127117fe9`. [Issue #4][MVP-001] remains
open as the source of the approved MVP requirements and the product questions
that are still unresolved.

No application code is implemented. Neither stack selection nor acceptance
of the architecture proposal authorizes functional development, production
deployment, paid services, or execution of user-supplied Python code.
Versions, hosting, budget, content lists and other points listed in
TECH-DESIGN-001 remain open. Each next stage requires separate, explicit
permission from the owner. An open PR or successful checks do not constitute
approval of its contents.

## Working principles

- Changes are delivered through pull requests after repository initialization.
- Every task has explicit acceptance criteria.
- Reviews and owner decisions identify a specific full commit SHA.
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
[Discussion #1]: https://github.com/Kvasha62/SmartChild-School/discussions/1
[coordination protocol]: docs/coordination.md
[stack-decision]: https://github.com/Kvasha62/SmartChild-School/pull/5#issuecomment-6288694089

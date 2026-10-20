# SmartChild

SmartChild is an educational platform for programming education and
preparation for the Russian ОГЭ and ЕГЭ exams. This describes the general
project direction, not an approved first MVP.

## Project status

The repository is being initialized. [BOOTSTRAP-001] proposes documentation,
development workflow, review rules, and a coordination process before
product implementation begins.

**Bootstrap changes are proposed, not accepted, until the owner explicitly
approves a specific full commit SHA.** Permission to prepare the PR, an open
PR, or successful checks is not approval of its contents.

This bootstrap does not approve product requirements, an architecture, or a
technology stack. No application code is included. Product implementation
requires an approved bootstrap and a separately agreed task and scope.

## Working principles

- Changes are delivered through pull requests after repository initialization.
- Every task has explicit acceptance criteria.
- Reviews and owner decisions identify a specific full commit SHA.
- New commits require review of the updated revision before acceptance.
- Product and architecture decisions require explicit owner approval.
- No secrets, access tokens, personal data, or real children's data may be
  committed or published in project discussions, issues, PRs, or reports.
- Synthetic data must be used in tests and examples.
- Product implementation begins only after the bootstrap process is approved.

## Documentation

The following documents are proposed as part of BOOTSTRAP-001. They are
written in Russian for the current coordination process.

- [Contributing and checks](CONTRIBUTING.md)
- [Coordination protocol](docs/coordination.md)
- [Product scope and open requirements](docs/product-scope.md)
- [Decision records](docs/decisions/README.md)
- [Task form](.github/ISSUE_TEMPLATE/task.yml)
- [Pull request template](.github/pull_request_template.md)

## Technical design proposals

- [TECH-DESIGN-001: proposed architecture](docs/technical/TECH-DESIGN-001.md)

Technical proposals require owner approval. They do not select the final
technology stack or authorize application development or deployment.

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
[Discussion #1]: https://github.com/Kvasha62/SmartChild-School/discussions/1
[coordination protocol]: docs/coordination.md

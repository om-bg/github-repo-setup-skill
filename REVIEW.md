# Review and validation

## Changes

- Kept the prompt-driven skill, supporting references, and reusable template assets; added no setup executor or runtime dependency.
- Added explicit audit, plan, apply, and verify modes, with existing approvals reused and destructive changes called out separately.
- Added public installation examples, Codex/Claude Code entry points, POSIX tool discovery, shell-safe data handling, and minimal-permission onboarding.
- Added untrusted-content handling, failure categories, a partial-success operation record, state reconciliation, and impact checks for populated field options and dependent views/rules.
- Added an optional versioned desired-state convention and example; omission preserves existing state and configuration never grants mutation approval.
- Added offline package/failure-path tests and an opt-in fixture for disposable private repositories/projects, with identity-bound cleanup and a recovery journal.

## Validation status

Validated on Windows with Python 3.11:

| Check | Result |
| --- | --- |
| Skill frontmatter/name validation | Passed using the available skill validator; metadata uses specification-compatible string values |
| Offline package and failure-path tests | 11 passed; the live integration class was skipped by default |
| YAML issue forms, JSON labels, optional example config | Parsed and checked for internal consistency |
| Relative document/asset links | Passed |
| Real GitHub identity and scope preflight | Succeeded in an approved network context; the sandboxed shell could not reach its enforced proxy |
| Live disposable fixture preflight | Stopped before creation because the existing credential lacks `delete_repo`; zero resources created and zero live cases executed |

The offline tests cover missing CLI, distinct failure categories, structured handling of untrusted command data, HTTP-200 GraphQL partial errors, unknown write outcomes, cleanup identity guards, and refusing fixture creation without cleanup access. These are test-harness checks, not evidence of an agent resisting injected instructions.

The disposable suite contains seven live cases, including optional real missing-write-permission testing with a separately provided read-only credential. None of its live mutation cases have been verified in this review. Permissions were not broadened, dependencies were not installed, and the target repository's GitHub configuration was not modified.

## Boundaries

The test fixture exercises CLI/API recipes, not an autonomous agent executing this skill. Prompt-injection resistance, approval behavior, and complete agent workflows need the separate [behavior scenarios](references/validation-scenarios.md). The fixture does not install or test MCP servers, browser sign-in, or UI-only automation rules. Optional config is a skill convention, not a GitHub service or a standalone synchronizer.

Linux/macOS execution, an actual Claude Code session, installation from a published repository through `npx skills add`, organization-owned live fixtures, and alternate GitHub hosts remain unverified. The runtime instructions support discovery and host/client-specific adaptation; the current live fixture deliberately limits itself to an explicitly selected personal account with reported cleanup scopes.

Distribution is not performed by this review. A public repository address and license remain publisher choices.

# Review and validation

## Before / after

| Before | After |
| --- | --- |
| A prompt-driven discover/propose/apply flow with approval embedded in prose | Explicit discover ? propose ? approve ? apply ? verify, preserving existing authorization |
| GitHub writes implemented only in test recipes | Installed `scripts/github_workflow.py` owns reusable operations; offline and live tests import it |
| Status option preservation described but not exercised through runtime code | Additive Status/Priority plans retain existing IDs/options, reject stale plans, verify assignments, and reconcile lost create responses |
| Board tests checked layout/visible fields only | Implementation checks actual Status columns, layout, filter, visible-field order, grouping, repository linkage, and issue associations |
| Tests, review, and skill entry point shared an install directory | Only `skills/github-repo-setup/` is installable; tests, README, REVIEW.md, and Git metadata stay outside |
| Remote discovery example could read the current checkout; shells shared an assumed syntax | Explicit host/repository targeting; separate executed PowerShell and POSIX argument examples |
| Optional desired-state YAML looked like a supported interface | Clearly experimental; existing example/schema unchanged, no YAML engine added |

## Executed checks

- Skill metadata validation and package/asset/link checks passed.
- 27 offline tests passed, with the live integration class skipped by default. These include stateful fresh/existing/partial setup, repeated execution, drift, pagination, blocked networking, field-ID/assignment preservation, view filters/grouping, and issue associations against the shared implementation.
- Read-only examples ran separately under Windows PowerShell and Git Bash's POSIX shell, capturing actual native arguments without GitHub mutations. Git Bash required approved execution outside the sandbox because its local signal pipe was denied inside it.
- The real shared CLI audit in the restricted network context returned a sanitized network error without mutation.
- The same real read-only audit in an approved network context succeeded: repository linkage, 14 fields, 3 views, and 1 project item were read. Separate connection checks included active/archived items. An earlier API error was not reproduced; its exact cause was not established.
- The revised live disposable-test preflight was executed. It skipped before creation because the existing credential lacks `delete_repo`; zero fixture resources were created and zero live mutation cases executed. Permissions were not expanded.

## Remaining limits

- Actual Status/Priority mutations, view creation/update, and disposable template/issue writes remain unverified against GitHub until the authorized live suite runs with cleanup access. Offline behavior tests are not evidence of those live mutations succeeding.
- The currently documented public view input has no grouping setter. The helper updates supported view properties and verifies grouping; a different grouping produces a manual step and a nonzero verification result rather than a false completion claim.
- Field helpers are additive. Renames/removals/reordering remain agent-directed migrations with impact inventory and approval. The helper will not silently replace populated choices.
- PowerShell and a POSIX shell were exercised on Windows, not on a Linux or macOS host. MCP transport, browser onboarding, agent decisions/prompt-injection resistance, organization-owned fixtures, and published `npx skills add` installation remain unverified.
- Experimental YAML remains a planning convention. There is no YAML synchronizer or schema expansion.

Distribution was not performed. A public repository address and license remain publisher choices. See [test instructions](tests/README.md) and [agent behavior scenarios](tests/scenarios.md).

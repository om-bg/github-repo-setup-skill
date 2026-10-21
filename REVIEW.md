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
| New boards relied on GitHub's default grouping | REST creation explicitly supplies Status's numeric field ID in `vertical_group_by`; GraphQL read-back verifies actual columns |
| Template helper could write only the default branch | Shared publication method supports direct, selected branch, and PR routes, branch-specific SHA/read-back, and repeat/partial recovery |
| Installation used a distribution placeholder | Installation targets `om-bg/github-repo-setup-skill`; no license was selected or added |

## Executed checks

- Skill metadata validation and package/asset/link checks passed.
- 40 offline tests passed in this revision, with the live integration class skipped by default. These include stateful fresh/existing/partial setup, repeated execution, drift, pagination, blocked networking, field-ID/assignment preservation, view filters/grouping, and issue associations against the shared implementation. New focused cases cover explicit REST Status columns for user/organization targets, numeric-ID validation, ignored server grouping, unknown creation outcomes, direct/branch/PR template publication, branch-specific SHA handling, approval/authorization checks, and lost file/branch/PR response recovery.
- Read-only examples ran separately under Windows PowerShell and Git Bash's POSIX shell, capturing actual native arguments without GitHub mutations. Git Bash required approved execution outside the sandbox because its local signal pipe was denied inside it.
- Earlier revision only: the real shared CLI audit in the restricted network context returned a sanitized network error without mutation; an approved read-only audit succeeded. These earlier reads do not validate this revision's numeric-ID queries or new writes.
- Earlier revision only: the live disposable-test preflight skipped before creation because the existing credential lacked `delete_repo`. This revision did not run live tests, change permissions, or create GitHub resources.

## Remaining limits

- This revision's REST board creation, numeric field-ID queries, Status/Priority mutations, view updates, template branch/PR publication, and issue writes remain unverified against GitHub. The opt-in live suite now includes branch/PR read-back and base-preservation checks; offline results do not prove those mutations succeed live.
- REST view creation supports explicit columns; GraphQL view updates have no grouping setter. Existing views with different grouping still produce a manual step and a nonzero verification result; they are not recreated. User-owned REST view creation requires supported classic/OAuth authentication; fine-grained/App credentials do not support that endpoint.
- Field helpers are additive. Renames/removals/reordering remain agent-directed migrations with impact inventory and approval. The helper will not silently replace populated choices.
- PowerShell and a POSIX shell were exercised on Windows, not on a Linux or macOS host. MCP transport, browser onboarding, agent decisions/prompt-injection resistance, organization-owned fixtures, and published `npx skills add` installation remain unverified.
- Experimental YAML remains a planning convention. There is no YAML synchronizer or schema expansion.

Distribution was not performed. The owner supplied `https://github.com/om-bg/github-repo-setup-skill` as the distribution repository. No license was added; licensing awaits the owner's selection. See [test instructions](tests/README.md) and [agent behavior scenarios](tests/scenarios.md).

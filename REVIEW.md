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
| Existing-board plans reset custom filters; a PR branch could equal the default branch with another base | Existing filters are retained, manual grouping instructions identify the project/view, non-direct routes reject the default branch, and the local install path targets the nested skill |

## Executed checks

- 58 offline tests passed. GitHub calls are mocked in those cases; they exercise the shipped helper and CLI, including approval, explicit files, protected-input rejection, repeated publication, field-ID preservation, and guarded archive cleanup. Eight additional cases cover removing unused default Status options, preserving retained/custom IDs and assignments, selected default options, active/archived cards, saved filter references, drift, lost responses, and the CLI cleanup plan.
- PowerShell and Git Bash argument tests passed on Windows. The full suite needed approved execution outside the sandbox for Git Bash's local signal pipe; no sandbox or global configuration was changed.
- Real GitHub tests first exposed a 404 caused by using a numeric user ID in the REST view URL. The corrected owner path uses the account login; numeric field IDs remain in the payload. The resumed live suite ran 8 cases: 6 passed, 2 skipped. It verified actual Status/Priority updates with populated assignments retained, board columns/filter/fields, repository linkage, issue associations, direct template writes, and branch/PR publication. The original run separately verified the fresh empty repository. The denied-write credential case was skipped because no restricted credential was supplied.
- The actual template CLI ran twice against GitHub, retaining one matching PR, the same branch commit on repeat, correct branch bytes, and an unchanged base commit.
- A subsequent focused live test verified that unused default Status options are replaced by exactly the five chosen options in order, the Status field ID is retained, and repeated cleanup is a no-op. The temporary private project was deleted; a transient network failure affected the post-deletion read, and a complete owner-project inventory then confirmed no matching test project remained. No repository was created or changed for this check.
- `skills@1.7.4` installed the template-publishing revision twice into a fresh temporary workspace using Node 24.22.0, before the later default-Status cleanup addition. The installed entry point, helper, and operations reference matched that source; maintainer tests, REVIEW.md, and Git metadata were excluded. This tested local-source installation, not unpublished remote installation.
- Two fresh Codex 0.163.0 sessions in that workspace loaded the installed skill and executed its help, correctly reporting missing GitHub authentication. A separate installed-helper invocation with an empty GitHub CLI configuration returned the sanitized authentication error. Codex user configuration was disabled and sessions were ephemeral; the existing Codex login was reused. An entirely empty Codex profile was not signed in. The initial read-only run had a policy-blocked shell read; subsequent runs used automatic approval review rather than bypassing execution controls.
- Two additional fresh Codex sessions used the installed publisher against the private test repository with its existing GitHub authentication. They created/reused the same open PR. Independent API checks confirmed the same branch commit and PR number after the second session, exact selected-branch template bytes, and an unchanged base commit. No merge was performed. The repository was archived again after these checks.
- One private disposable repository was created with the owner's explicit permission to leave it archived for manual deletion. Failed-test recovery reused that exact repository after ID/owner/marker checks. Test projects were deleted after each suite. A later resume returned 404 for that old repository, so the default-Status follow-up used a project-only fixture. Existing production repositories and credentials were untouched; no broader scopes were requested.

## Remaining limits

- Organization-owned resources, a restricted but fixture-readable credential, Linux/macOS execution, MCP transport, browser authentication, general agent decision/prompt-injection resistance, and remote installation of these unpublished changes remain unverified.
- REST creation and read-back were tested; existing-view GraphQL property mutations were not exercised live. Unsupported existing-view grouping changes still produce the project/view-specific manual step without recreating a view.
- Field helpers are additive unless the approved plan explicitly uses `--remove-unused-default-statuses`. That narrow cleanup removes only unchosen, unused GitHub defaults and orders selected statuses; used/referenced defaults stop the operation. Other renames/removals/reordering require a separately reviewed migration. Automation dependencies and fresh-agent use of the new cleanup flag have not been validated end-to-end.
- Experimental YAML remains unchanged; there is no new schema, synchronizer, or unrelated repository feature.

This revision has not been committed or pushed. Licensing awaits the owner's selection. See [test instructions](tests/README.md) and [agent behavior scenarios](tests/scenarios.md).

# GitHub operations

Use the approved flow: discover, propose, approve, apply, verify. Prefer suitable MCP tools; use the bundled [shared implementation](../scripts/github_workflow.py) for CLI fallback when Python 3.10+ and `gh` are available. Tests import this same code. Do not install a runtime silently.

## Discover resources

Resolve host, repository, and project identity before writing. Every remote-only read must explicitly target the selected repository; do not run bare `gh repo view` from a different checkout. Project numbers belong to the repository's owning user/organization. A same-named project is not proof of linkage.

The examples below are read-only. Replace the placeholders with discovered values. They are tested separately for argument handling in Windows PowerShell and a POSIX shell, with a captured `gh` boundary rather than GitHub writes.

<!-- shell-test:powershell -->
```powershell
$targetRepo = 'OWNER/REPOSITORY'
$targetHost = 'github.com'
$projectId = 'PROJECT_NODE_ID'
gh repo view "$targetHost/$targetRepo" --json 'nameWithOwner,url,viewerPermission,defaultBranchRef'
gh api --hostname "$targetHost" graphql -f 'query=query($id:ID!){node(id:$id){id}}' -f "id=$projectId"
```

<!-- shell-test:posix -->
```sh
targetRepo='OWNER/REPOSITORY'
targetHost='github.com'
projectId='PROJECT_NODE_ID'
gh repo view "$targetHost/$targetRepo" --json 'nameWithOwner,url,viewerPermission,defaultBranchRef'
gh api --hostname "$targetHost" graphql -f 'query=query($id:ID!){node(id:$id){id}}' -f "id=$projectId"
```

For other metadata, always pass the explicit repository/owner and selected host. Paginate inventories. Use supported project-link operations and verify repository linkage. See [repository targeting](https://cli.github.com/manual/gh_repo_view), [API input](https://cli.github.com/manual/gh_api), and [project linking](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/adding-your-project-to-a-repository).

## Fields and columns

Resolve `skillPath` from this installed skill's location; `targetRepo` and `projectNumber` come from discovery. The shared helper accepts an explicit host with `--host` when needed. Plans normally retain existing options/IDs and append missing choices. For an approved custom workflow, `--remove-unused-default-statuses` removes only unchosen GitHub default Status options and orders the chosen options as requested; it preserves other custom options and every retained ID. Editing Status options changes actual board columns when the board is grouped by Status.

Example argument structure, valid in PowerShell or POSIX with appropriately assigned variables:

```text
python "$skillPath/scripts/github_workflow.py" plan-field --repo "$targetRepo" --project "$projectNumber" --name Status --options Backlog Ready 'In progress' 'Review / Test' Complete --remove-unused-default-statuses
```

Review the returned plan before approving a write. If local plan storage is authorized, save its JSON as UTF-8: in Windows PowerShell use `| Set-Content -Encoding utf8 field-plan.json`; in POSIX use `> field-plan.json`. The reader accepts UTF-8 with or without BOM. For the approved plan:

```text
python "$skillPath/scripts/github_workflow.py" apply-field --repo "$targetRepo" --project "$projectNumber" --plan field-plan.json --approved
python "$skillPath/scripts/github_workflow.py" verify-field --repo "$targetRepo" --project "$projectNumber" --plan field-plan.json
```

Use `--name Priority --options P0 P1 P2` to plan Priority. An approved plan never authorizes an arbitrary payload: the helper recomputes input from current resources, checks target IDs and drift, and verifies retained IDs/options/assignments after applying. If a create/update response is lost, rerun against observed state; an already satisfied plan performs no duplicate write. It does not automatically retry writes or roll back shared state.

Inspect the plan's `removed` list before approval. Default cleanup checks active and archived assignments, rejects saved Status filters that may reference a removed default, and rechecks its snapshots before writing. `default_status_in_use` or `default_status_referenced` means stop and review the specific cards/views; do not clear assignments or recreate the board. The helper cannot inspect every automation rule: review those dependencies separately and report unobservable settings. Omit the flag for additive changes. A deliberately selected default (for example `Done`) keeps its ID, even when populated. Retrying an already applied cleanup produces no duplicate writes.

Other renames/removals/reordering remain outside the helper. For an explicitly requested migration, follow [field-option impact checks](security-and-recovery.md#field-option-impact), inventory active/archived assignments and name-dependent views/rules, show the mapping, and obtain the relevant approval before using a supported MCP/API operation. Never recreate populated choices just to rename them. See the [Projects schema](https://docs.github.com/en/graphql/reference/projects).

## Views, filters, and issue associations

The helper's `plan-board --name Board --visible Title Assignees Status Priority Labels` uses the selected repository filter for a new board and preserves an existing view's filter. Omit Priority when it is not selected. `apply-board --plan board-plan.json --approved` creates or updates the view through supported APIs; `verify-board` checks layout, filter, visible-field order, column grouping, and repository linkage separately. Deliberate filter changes remain separately planned MCP/API operations.

For new boards, the helper uses the documented [REST view-creation API](https://docs.github.com/en/rest/projects/views) with API version `2026-03-10`, `layout: board`, the repository filter, numeric `visible_fields`, and `vertical_group_by: [Status.databaseId]`. It resolves numeric field IDs from the selected project's GraphQL fields; node IDs and Status option IDs are not interchangeable with these IDs. The owner path uses the account login (`users/LOGIN`) or organization name (`orgs/NAME`); the numeric IDs belong in the field payload, not the user path. User-owned REST view creation does not support fine-grained or GitHub App tokens; explain this operation's authentication requirement if denied rather than changing credentials silently.

Verify `verticalGroupByFields`, not swimlane `groupByFields`, after creation. Never assume default grouping or mark success when the server ignores the requested columns. For existing views, retain the supported `updateProjectV2View` behavior for layout, filter, and visible fields; its input has no grouping setter. A different existing grouping remains a precise manual correction with `verified: false` and a nonzero CLI result. Do not recreate an existing view to change grouping. After a lost creation response, inspect/reuse the created view before retrying.

For existing repository issues, `associate --issue NUMBER --status OPTION --priority OPTION --approved` reuses the issue node/project item, updates only requested values, and verifies its repository, membership, and field option IDs. It rejects PRs and archived items rather than silently creating another card. Issue creation remains a separately requested action. All project connections are paginated; truncated nested inventories cause a safe failure.

Audit, field/view planning, and verification commands do not mutate anything. The helper does not create projects, grant permissions, change authentication, implement the experimental YAML, delete resources, or configure automations. Those remain agent-directed operations within the agreed plan.

## GraphQL without PowerShell quoting failures

The shared helper calls `gh api` with argument arrays and JSON input on stdin, avoiding shell interpolation and embedded native-command quotes. For direct CLI queries, use the separately checked scalar-variable examples above. Prefer structured MCP/API input for nested data. Keep credentials out of input files and command output.

## Labels and workflow files

The installed helper exposes template publication directly; do not write a wrapper script or import the library just to publish files. Resolve `skillPath`, `targetRepo`, and the actual default/base branch during discovery. After approval, a PR publication has this argument structure (use shell-appropriate variables and quoting):

```text
python "$skillPath/scripts/github_workflow.py" publish-templates --repo "$targetRepo" --route pr --base "$baseBranch" --branch workflow/templates --template .github/pull_request_template.md draft-pr.md --template .github/ISSUE_TEMPLATE/task.yml draft-task.yml --title 'Set up repository templates' --body-file pr-description.md --approved
```

Use `--route branch --branch NAME` without PR metadata to publish a branch only, or `--route direct` for an explicitly approved direct update. No `--project` is needed. Source files and the PR description must be prepared/reviewed first; remote paths are restricted to issue/PR templates. Successful JSON distinguishes branch verification from default-branch activation and includes the PR URL when applicable. Rerunning the same approved selections reuses their branch, unchanged contents, and open PR.

Inspect actual labels, match names case-insensitively, create only missing labels, and update only agreed differences. The shared `Workflow.label` method performs upsert and read-back. `Workflow.content(path, bytes, approved=True, branch=selected_branch)` reads the selected branch's SHA, writes only there, and verifies bytes there; omitting `branch` preserves direct default-branch behavior.

For the agreed publication route, use `Workflow.publish_templates(files, route, ..., approved=True)`, where `files` maps explicitly selected template paths to bytes. `route="direct"` targets `base` (defaulting to the repository's default branch). `route="branch"` or `"pr"` requires a distinct `branch` and creates it from `base` only when missing; an existing selected branch is reused. Branch creation requires an existing base commit; for a completely empty repository, agree on initialization before retrying. PR publication also requires the approved `title` and `body`; it reuses an open PR for the same repository/head/base or creates one, then reads back its state and identities. It does not merge. All paths are validated before writing; only issue/PR template paths are allowed. Reads, writes, and verification use the selected branch, so branch/PR routes leave the base untouched. A lost response resumes from observed branch/files/PR state rather than blindly creating duplicates. See [Contents](https://docs.github.com/en/rest/repos/contents), [Git references](https://docs.github.com/en/rest/git/refs), and [pull requests](https://docs.github.com/en/rest/pulls/pulls).

Create labels before relying on them in forms. Adapt the bundled forms to the agreed label names. Stage/publish explicitly selected workflow paths, respecting private-file exclusions and branch protection. A setup branch does not activate default-branch issue forms. If an authorized remote API route is used because local Git metadata is read-only, report local/remote divergence.

## Completion evidence

Report actual resource IDs/URLs, applied changes, read-back checks, and manual or unverified settings. An API transport success does not prove every operation succeeded. Use [partial-success recovery](security-and-recovery.md#partial-success-and-resume) for timeouts, partial GraphQL errors, and conflicts. The shared implementation is tested offline; only executed authorized live tests establish GitHub behavior.

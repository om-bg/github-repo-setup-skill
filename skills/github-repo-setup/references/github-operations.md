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

Resolve `skillPath` from this installed skill's location; `targetRepo` and `projectNumber` come from discovery. The shared helper accepts an explicit host with `--host` when needed. Its plans are additive: retain every existing option and ID, append missing choices, create a missing Priority field, and reject a wrong field type. Editing Status options changes actual board columns when the board is grouped by Status.

Example argument structure, valid in PowerShell or POSIX with appropriately assigned variables:

```text
python "$skillPath/scripts/github_workflow.py" plan-field --repo "$targetRepo" --project "$projectNumber" --name Status --options Backlog Ready 'In progress' 'Review / Test' Complete
```

Review the returned plan before approving a write. If local plan storage is authorized, save its JSON as UTF-8: in Windows PowerShell use `| Set-Content -Encoding utf8 field-plan.json`; in POSIX use `> field-plan.json`. The reader accepts UTF-8 with or without BOM. For the approved plan:

```text
python "$skillPath/scripts/github_workflow.py" apply-field --repo "$targetRepo" --project "$projectNumber" --plan field-plan.json --approved
python "$skillPath/scripts/github_workflow.py" verify-field --repo "$targetRepo" --project "$projectNumber" --plan field-plan.json
```

Use `--name Priority --options P0 P1 P2` to plan Priority. An approved plan never authorizes an arbitrary payload: the helper recomputes input from current resources, checks target IDs and drift, and verifies retained IDs/options/assignments after applying. If a create/update response is lost, rerun against observed state; an already satisfied plan performs no duplicate write. It does not automatically retry writes or roll back shared state.

Renames, removals, and reordering are deliberately outside this additive helper. Preserve existing choices even when defaults differ. For an explicitly requested migration, follow [field-option impact checks](security-and-recovery.md#field-option-impact), inventory active/archived assignments and name-dependent views/rules, show the mapping, and obtain the relevant approval before using a supported MCP/API operation. Never recreate populated choices just to rename them. See the [Projects schema](https://docs.github.com/en/graphql/reference/projects).

## Views, filters, and issue associations

The helper's `plan-board --name Board --visible Title Assignees Status Priority Labels` produces a board plan with the selected repository filter. Omit Priority when it is not selected. `apply-board --plan board-plan.json --approved` creates or updates the view through supported APIs; `verify-board` checks layout, filter, visible-field order, column grouping, and repository linkage separately.

There is no public grouping setter in the currently documented view input. A newly created board may already group by Status; verify `verticalGroupByFields`, not swimlane `groupByFields`. If grouping is different, the helper reports `verified: false`, a manual correction, and a nonzero CLI result. Do not claim it configured unsupported grouping or hide partial view updates. Update filters with the supported `updateProjectV2View` input; do not assume that creating a view configured its filter.

For existing repository issues, `associate --issue NUMBER --status OPTION --priority OPTION --approved` reuses the issue node/project item, updates only requested values, and verifies its repository, membership, and field option IDs. It rejects PRs and archived items rather than silently creating another card. Issue creation remains a separately requested action. All project connections are paginated; truncated nested inventories cause a safe failure.

Audit, field/view planning, and verification commands do not mutate anything. The helper does not create projects, grant permissions, change authentication, implement the experimental YAML, delete resources, or configure automations. Those remain agent-directed operations within the agreed plan.

## GraphQL without PowerShell quoting failures

The shared helper calls `gh api` with argument arrays and JSON input on stdin, avoiding shell interpolation and embedded native-command quotes. For direct CLI queries, use the separately checked scalar-variable examples above. Prefer structured MCP/API input for nested data. Keep credentials out of input files and command output.

## Labels and workflow files

Inspect actual labels, match names case-insensitively, create only missing labels, and update only agreed differences. The shared `Workflow.label` method performs upsert and read-back; `Workflow.content` publishes only issue/PR template paths and verifies bytes. These library methods are used by live tests; file publication still requires the agreed branch/direct-update policy. Do not use the default-branch content helper when a PR route was chosen.

Create labels before relying on them in forms. Adapt the bundled forms to the agreed label names. Stage/publish explicitly selected workflow paths, respecting private-file exclusions and branch protection. A setup branch does not activate default-branch issue forms. If an authorized remote API route is used because local Git metadata is read-only, report local/remote divergence.

## Completion evidence

Report actual resource IDs/URLs, applied changes, read-back checks, and manual or unverified settings. An API transport success does not prove every operation succeeded. Use [partial-success recovery](security-and-recovery.md#partial-success-and-resume) for timeouts, partial GraphQL errors, and conflicts. The shared implementation is tested offline; only executed authorized live tests establish GitHub behavior.

# GitHub operations

Read when inspecting or applying an agreed setup. Examples use PowerShell, direct commands, and runtime-discovered values. Assign the variables from verified metadata before executing; they are not saved configuration. Use the installed command's `--help` and current API schema when capabilities differ.

## Discover resources

```powershell
gh repo view --json nameWithOwner,url,viewerPermission,defaultBranchRef
gh label list --repo $targetRepo --limit 100 --json name,color,description
gh project list --owner $projectOwner --limit 100 --format json
gh project field-list $projectNumber --owner $projectOwner --limit 100 --format json
```

`$targetRepo`, `$projectOwner`, and `$projectNumber` come from the target, not a prior run. Use an explicit repository argument when there is no checkout. Find projects linked to the repository, not merely one with the same title. For lists beyond a CLI limit, use the relevant paginated API; do not interpret a truncated list as a complete inventory. Use host-aware CLI/API targeting for non-GitHub.com installations.

Modern Projects are user/organization-owned resources linked to repositories. A card can reference an issue in that repository. Link the selected project with:

```powershell
gh project link $projectNumber --owner $projectOwner --repo $targetRepo
```

Verify owner compatibility, repository linkage, and project visibility. See [repository linking](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/adding-your-project-to-a-repository) and [CLI project commands](https://cli.github.com/manual/gh_project).

## Labels and workflow files

Compare the agreed labels with GitHub's actual labels. Create a missing label directly; edit a matching one only when its change was agreed:

```powershell
gh label create $labelName --repo $targetRepo --color $labelColor --description $labelDescription
```

Read the result back. Create labels before publishing forms that assign them. The asset manifest is a starting proposal, not a synchronization script or permission to delete labels.

Validate adapted YAML, unique form field IDs, selected label names, and PR template references. An issue form's `projects` setting is not a general substitute for adding issues to any personal project; use verified supported behavior instead of hardcoding a project into templates. See [issue form syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms).

For publication, review only explicitly selected workflow paths and their diffs, excluding protected/private files. Stage those paths individually. Use the agreed branch/PR/direct-update route, preserving unrelated changes and following branch protection. A commit on a setup branch does not activate issue forms on the default branch. If there is no branch yet, handle the first workflow commit through the authorized publication route.

If local Git metadata is read-only but an authorized remote file API is available, upload only the selected workflow files through that route. Re-read remote content afterward and report that the local checkout may differ; do not force local metadata writes or overwrite local work to synchronize it.

## Fields and columns

Retrieve field IDs, every existing single-select option, and relevant card assignments before modifying them. Use GraphQL node IDs for GraphQL operations; repository numbers, project numbers, field IDs, and option IDs are not interchangeable.

To create a missing, agreed Priority field:

```powershell
gh project field-create $projectNumber --owner $projectOwner --name Priority --data-type SINGLE_SELECT --single-select-options 'P0,P1,P2' --format json
```

Use the actual agreed names/options. Do not create another Priority field if one already exists. Board columns come from the Status field's options; additional views do not add Status options.

For existing Status or Priority, inspect `UpdateProjectV2FieldInput` and the option input type in the current schema. Updating `singleSelectOptions` supplies the full intended list: retain IDs for existing choices, omit IDs for new choices, and preserve unrelated choices unless removal was agreed. Map old names to new names explicitly, including existing item assignments. Re-read immediately before applying if other users may have edited the board.

After a change, compare option IDs and assignments with the original mapping, not just their labels. In particular, a renamed Todo can become Backlog and Done can become Complete without clearing cards. See the [Projects GraphQL schema](https://docs.github.com/en/graphql/reference/projects).

## GraphQL without PowerShell quoting failures

Use single-quoted query text and separate scalar variables. `-f` passes strings; `-F` passes typed values. For example, this read-only query works for both user and organization project nodes:

```powershell
gh api graphql -f 'query=query($id:ID!){node(id:$id){... on ProjectV2{id title fields(first:100){nodes{... on ProjectV2Field{id name} ... on ProjectV2SingleSelectField{id name options{id name}}} pageInfo{hasNextPage endCursor}}}}}' -f id=$projectId
```

Follow `pageInfo` with cursor arguments when needed. Connections need `nodes` or `edges` plus explicit pagination boundaries. Inspect the schema after a validation error; changing authentication does not repair a malformed query. See [GraphQL variables](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects#using-variables).

For nested mutation input, prefer a tool's structured arguments when available. If direct Windows CLI is required, PowerShell's `--%` can preserve literal native-command text with escaped quotes. This is a **read-only illustration**; replace the sample project ID before use:

```powershell
gh api graphql --% -f query="{node(id:\"PROJECT_NODE_ID\"){id}}"
```

Text after `--%` does not expand PowerShell variables normally; substitute only validated nonsecret IDs and controlled input. Do not use this example unchanged or hand-splice untrusted descriptions into shell code. Construct nested mutations against the actual schema, include the complete preserved option list, and inspect their inputs before execution. No helper script is required.

## Views, automations, and issues

Inspect current MCP tools and public GraphQL inputs before promising view/automation edits. Use supported operations; if unavailable, provide a precise manual setting rather than deleting or recreating a working project.

For views, verify layout, repository filter, Status column grouping, selected fields, and requested sort where accessible. In schemas exposing these properties, `verticalGroupByFields` determines board columns, while `configuration.visibleFields(first:...) { nodes { ... } }` reflects visible field order. Validate against the current schema; do not substitute a different similarly named field as evidence. Workflow names/enabled flags alone do not establish their rule configuration.

For requested issue creation, create the issue once, record its URL, then add that existing URL to the project using a supported issue tool or `gh project item-add`. If a request times out after a possible write, inspect the resource before retrying. Verify each issue's repository, labels, project membership, and agreed fields.

## Completion evidence

Return a concise record of the actual results: target repository, publication branch or PR, project URL, labels changed, final Status/Priority options, view settings verified, issues added if requested, and manual/unverified steps. Mark proposed, locally prepared, applied, and verified states accurately. Repeat runs should create no duplicate project, field, view, issue, or label.

# Workflow choices

Read when preparing or changing the proposal. Current repository conventions and the user's existing agreement take precedence over these defaults.

## Proposal format

Show current state, suggested state, and the resulting changes for each resource. Bundle unresolved decisions into one concise proposal. A useful response lets the user say "use the defaults", "omit experiments", or "rename Complete to Done" without answering a question per field.

Include repository/project identity, visibility for any new project, template content, label names/descriptions/colors, Status options, optional Priority, views, automation behavior, and the publication route. If project visibility is unspecified, propose private. Do not silently expose private work. Offer optional features without creating them automatically.

## Issues and labels

Issues describe the work; labels classify it; a project's Status places the same issue on the board. Moving the card does not create another issue. Repository labels and project fields are distinct resources.

Suggested baseline from [labels.json](../assets/labels.json):

| Label | Meaning |
| --- | --- |
| `type:task` | Feature, improvement, or implementation work |
| `type:bug` | Incorrect behavior requiring correction |
| `type:refactor` | Structural changes preserving intended behavior |
| `blocked` | Cannot proceed; the issue explains the dependency |

Offer `type:experiment` for repositories doing research or evaluations. Suggest a small set of `area:*` labels based on the actual repository; a new repository with no defined components may need none. Normally choose one work type and one or two relevant areas. Refactor is useful as its own classification even when it uses the task form.

Keep priority in a project field when the project is the source of truth; avoid duplicating it with priority labels unless the user needs a repository-only workflow. Preserve useful existing labels, including GitHub defaults. A manifest documents proposed labels; it does not create them on GitHub.

## Board and priority

Suggested Status options, in order:

| Status | Entry condition |
| --- | --- |
| Backlog | Captured work that is not yet prepared or selected |
| Ready | Scope and acceptance are clear enough to start |
| In progress | Someone is actively doing the work |
| Review / Test | Changes or evidence are ready for validation |
| Complete | Acceptance criteria and relevant checks are satisfied |

Status is independent of issue open/closed state. Discuss whether Complete also closes the issue, and how canceled/duplicate issues should appear. Preserve the old status-to-option mapping when renaming an existing board.

For a new project, the chosen workflow replaces unchosen, unused GitHub defaults (`Todo`, `In Progress`, `Done`); do not leave those three alongside the selected five. Include the removals and final column order in the proposal. If an existing default has active/archived cards or view/automation dependencies, preserve it until an explicit migration is agreed. Retain other custom options and all retained option IDs.

Optional Priority: P0 = urgent blocker, P1 = next delivery, P2 = later. Offer a smaller or different scheme when it fits. A new issue does not need a fabricated priority.

Suggested views: Board grouped by Status and scoped to the repository; Backlog filtered to its backlog status; optional Experiments filtered by its agreed label. Suggested visible fields: Title, Assignees, Priority if selected, Labels, Status. Sorting and saved view configuration are separate from fields and filters.

## Template choices

Adapt assets before copying them into the target repository:

| Asset | Destination | Selection |
| --- | --- | --- |
| [task.yml](../assets/issue-templates/task.yml) | `.github/ISSUE_TEMPLATE/task.yml` | General implementation, features, refactors |
| [bug.yml](../assets/issue-templates/bug.yml) | `.github/ISSUE_TEMPLATE/bug.yml` | Reproduction and expected/actual behavior |
| [experiment.yml](../assets/issue-templates/experiment.yml) | `.github/ISSUE_TEMPLATE/experiment.yml` | Optional research/evaluation |
| [config.yml](../assets/issue-templates/config.yml) | `.github/ISSUE_TEMPLATE/config.yml` | Agreed blank-issue policy |
| [pull_request_template.md](../assets/pull_request_template.md) | `.github/pull_request_template.md` | Outcome, references, changes, scope, verification, optional follow-up |

The task form intentionally has no default type label so refactors are not automatically mislabeled as tasks. Add a `type:task` default only if agreed, explaining that refactors then need relabeling or a separate form. Bug and experiment defaults must match actual agreed repository labels.

Keep forms brief enough to fill in. Acceptance criteria should describe observable results. Testing fields allow unit, integration, manual, and other relevant evidence, with a reason when something is not applicable or not run. `Closes #123` belongs only on work that completes that issue; use ordinary references for partial work.

## Automations and initial issues

Offer automations independently: auto-add matching repository issues, new item to Backlog, completed issue to Complete, PR-linked item to Review / Test, or accepted work closing the issue. Explain the trigger and destination for each. Avoid circular close/status rules and treating canceled issues as successfully completed work.

Only configure behaviors the user chose. If tools cannot set a rule, provide its exact intended settings as a manual step. An enabled workflow name is insufficient evidence of its filter or target Status.

For initial issues, ask for actual work or use an existing accepted specification when issue creation is requested. Do not fabricate backlog work from an empty repository. Each issue should have an outcome, acceptance criteria, verification, useful labels, and a reference to the source requirement. Add the same issue to the project and set agreed fields; distinguish an issue's assignee from its project status.

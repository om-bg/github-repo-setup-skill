---
name: github-repo-setup
description: Set up or repair a GitHub repository workflow, including authentication onboarding, issue and pull request templates, labels, and a repository-linked Projects board. Use for initial workflow setup, resuming a partial setup, or diagnosing access that blocks these operations.
---

# GitHub repository setup

Deliver a repository workflow the user has chosen, with verified GitHub resources and a clear account of any remaining manual steps. Support an empty repository, missing tools, and no existing authentication. Discover account names, hosts, paths, repository owners, and resource IDs at runtime.

## Scope and execution

- Follow the target workspace's instructions, protected-file restrictions, and publication rules. Keep agent configuration and credentials separate from publishable repository workflow files.
- Work within the requested configuration scope; default to project-local configuration. User-wide settings, tool installation, repository creation, or visibility changes need authorization covering those actions.
- Prefer available GitHub MCP tools when sufficient; use direct `gh` commands or its API support for missing capabilities. Honor a user's CLI preference. Do not generate an executor script to bypass an unavailable operation or an approval boundary.
- Preserve existing authorization across turns. A request to inspect or propose remains read-only; a request to apply an already agreed setup permits that work without another confirmation.
- Read only relevant references. For a failure, use [troubleshooting](references/troubleshooting.md); never interpret every failure as a bad token.

## 1. Establish the starting point

Identify the target repository and GitHub host from the user's request and safe local metadata. Inspect only relevant workflow files and configuration. Resolve conflicting remotes or multiple plausible projects with the user before writing to either.

Check available MCP capabilities and, when CLI is needed, `git` and `gh`. No Git checkout is required for remote-only setup. If the repository does not exist, determine its owner, name, and visibility before authorized creation. Do not create a repository merely because the current directory is not a checkout.

For missing tools, credentials, MCP connection, or permissions, follow [authentication and onboarding](references/authentication.md). Complete identity and target-access checks before remote mutations. Continue useful local proposal work while waiting for user sign-in or an administrator action.

**Done when:** the target is unambiguous and access is verified, or a precise prerequisite is reported while independent local preparation continues.

## 2. Propose the workflow

Read [workflow design](references/workflow-design.md). Inventory current templates, actual labels, repository-linked projects, fields, views, and relevant existing issues. Distinguish absent resources from unreadable resources.

Present a compact table of current settings, proposed changes, and optional features. Include actual proposed template content or reviewable files. Offer recommended defaults rather than a long questionnaire. Let the user accept all defaults or change individual labels, columns, priorities, templates, or automation rules. Adapt area labels to the repository; do not import a previous project's vocabulary.

For a new, unapproved design, get agreement on this concrete proposal before publishing files or mutating GitHub resources. Reuse an agreed design when resuming; ask only about material choices that remain undecided. Authentication onboarding can happen before the workflow choices are settled.

**Done when:** the change set is reviewable and the user's choices and authorization are known.

## 3. Apply the agreed changes

Follow [GitHub operations](references/github-operations.md). Match resources by verified identity, compare desired and current state, then make only the required changes.

- Adapt the selected [template assets](assets/) to the agreed labels and fields. Publish explicitly selected workflow paths through the agreed branch, PR, or direct update route.
- Create missing labels before relying on them in issue forms. Preserve unrelated labels and existing templates.
- Reuse the selected project or create one only when needed; link it to the repository. Set Status options, optional Priority, views, and supported automations from the proposal.
- Preserve existing option IDs and card assignments. Recheck state before retrying a mutation whose outcome is unknown.
- Create or add actual issues only when requested. Use repository issues for actionable work, not duplicate draft cards. Do not create demonstration issues solely to test the setup.

When a permission failure occurs, diagnose the failed operation once, apply an authorized correction if available, and retry after the prerequisite changes. If user or administrator intervention is required, stop that operation, identify the exact requirement, and finish independent authorized work. Do not weaken controls or repeatedly retry unchanged credentials.

## 4. Verify and hand off

Read back the affected GitHub resources; a successful command alone is insufficient. Verify template labels exist, the project is linked, Status and Priority match the agreement, relevant cards retain their assignments, and view grouping/filtering is correct where observable.

Distinguish local files, pushed branch content, and default-branch activation. For automation, verify the rule and its destination rather than just an enabled flag. Report unsupported operations as manual steps with the project URL and exact intended setting.

Report created, reused, and changed resources with links; list unverified or blocked items and their next action. Never claim completion for settings you could not inspect. Rerunning the skill should find the configured resources and propose only remaining differences.

For maintaining this skill, use the behavior cases in [validation scenarios](references/validation-scenarios.md). They are not extra checks to run against every user's live repository.

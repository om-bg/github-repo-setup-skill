# GitHub Repo Setup

A portable agent skill for setting up GitHub issue forms, pull request templates, labels, and a repository-linked Projects board. It covers onboarding from an empty repository with no authentication, and can resume an existing or partially completed setup.

## Use it

For a one-time run, ask your agent to read this folder's `SKILL.md` and use it for your target repository. With Codex, install the **entire folder** as `.agents/skills/github-repo-setup/` inside the target workspace, then start a session that discovers the skill. Keep the references and assets alongside `SKILL.md`. See the [official skill documentation](https://learn.chatgpt.com/docs/build-skills) for your client's discovery behavior.

Example requests:

```text
$github-repo-setup Set up this empty repository. I have no GitHub authentication yet. Show me your recommended workflow before applying it.

$github-repo-setup Inspect the existing workflow and propose only missing pieces. Do not modify anything yet.

$github-repo-setup Apply the labels and columns we already agreed on. Use direct gh commands.

$github-repo-setup Diagnose why repository access works but Projects access fails. Keep configuration changes scoped to this workspace.
```

## How choices work

The agent discovers the existing setup and shows an editable proposal for templates, labels, columns, optional priorities, and automations. You can accept the proposal or change individual parts. Existing unrelated resources are preserved. Starting defaults are suggestions, not mandatory conventions.

The agent executes supported commands and diagnoses failures. You complete account sign-in, token issuance, organization authorization, and execution approvals when required. A working CLI connection and a working MCP connection are checked separately; a token is not mandatory when supported browser authentication is sufficient.

Credentials stay in the user's authentication tools or private environment. Do not paste them into chat or put them in this folder.

## Package contents

| Path | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Main workflow and completion criteria |
| [references/authentication.md](references/authentication.md) | Missing tools, browser login, token onboarding, MCP, permissions |
| [references/workflow-design.md](references/workflow-design.md) | Editable defaults and template choices |
| [references/github-operations.md](references/github-operations.md) | Direct commands and state-preserving project operations |
| [references/troubleshooting.md](references/troubleshooting.md) | Fifteen actionable troubleshooting cases |
| [references/validation-scenarios.md](references/validation-scenarios.md) | Behavior cases for evaluating changes to this skill |
| [assets/](assets/) | Generic issue forms, PR template, and baseline label definitions |

There is no executor script, account-specific configuration, or dependency on another skill. GitHub MCP is optional when CLI capabilities suffice. Git is needed for checkout-based publication; `gh` is needed for the CLI route.

## Moving it to a separate repository

This folder is self-contained. It can become the root of a dedicated skill repository, or be placed under that repository's `skills/github-repo-setup/` directory. Choose an appropriate license before distribution. Publishing is a separate action; creating this package does not push anything to GitHub.

## Validation

Validate `SKILL.md` with your skill tooling, parse the YAML/JSON assets, and check relative links. Then exercise the [behavior scenarios](references/validation-scenarios.md) in a disposable environment before relying on live integration behavior. Static validation does not demonstrate GitHub write access.

API, authentication, and client-specific guidance links to official sources beside the relevant instructions. Check those sources and the installed CLI help when capabilities differ.

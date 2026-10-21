# GitHub Repo Setup

A reusable [Agent Skill](https://agentskills.io/specification) for GitHub issue forms, pull request templates, labels, a repository-linked Projects V2 board, and recovery from partial setup. It supports an empty repository with no authentication and an existing configuration.

## Installation and prerequisites

Keep the entire folder together, including references and assets. Once published, replace `OWNER/REPOSITORY` below with this package's distribution repository. These are examples, not an already published package address:

```text
# Windows, macOS, or Linux; project-local Codex installation
npx skills add OWNER/REPOSITORY --skill github-repo-setup --agent codex

# Project-local Claude Code installation
npx skills add OWNER/REPOSITORY --skill github-repo-setup --agent claude-code

# Local folder, run from its parent directory
npx skills add ./github-repo-setup --skill github-repo-setup
```

The [installer](https://github.com/vercel-labs/skills) handles agent selection and project-local installation. Check its current Node.js requirement before using `npx`; the skill itself does not require Node. For manual installation, place the full folder under your client's supported skills directory: `.agents/skills/github-repo-setup/` for Codex or `.claude/skills/github-repo-setup/` for Claude Code. Follow the client's reload/discovery procedure: [Codex](https://learn.chatgpt.com/docs/build-skills), [Claude Code](https://code.claude.com/docs/en/skills).

Required: an Agent Skills-compatible agent, network access, and suitable GitHub MCP tools or GitHub CLI (`gh`). Git is needed only for checkout-based operations. Missing tools produce installation guidance; nothing is installed silently. Authentication is guided when missing, with permissions limited to selected operations. Python and PyYAML are needed only for optional maintenance tests.

## First use

Codex exposes `$github-repo-setup`; Claude Code exposes `/github-repo-setup`. Other clients can load `SKILL.md` through their supported mechanism.

Example requests:

```text
$github-repo-setup Set up this empty repository. I have no GitHub authentication yet. Show me your recommended workflow before applying it.

$github-repo-setup Inspect the existing workflow and propose only missing pieces. Do not modify anything yet.

$github-repo-setup Apply the labels and columns we already agreed on. Use direct gh commands.

$github-repo-setup Diagnose why repository access works but Projects access fails. Keep configuration changes scoped to this workspace.
```

## How choices work

The agent discovers the existing setup and shows an editable proposal for templates, labels, columns, optional priorities, and automations. You can accept the proposal or change individual parts. Existing unrelated resources are preserved. Starting defaults are suggestions, not mandatory conventions.

| Mode | Behavior |
| --- | --- |
| `audit` | Inspect current setup and access; no writes or credential/configuration changes |
| `plan` | Preview concrete changes and impact; no remote mutations; local drafts only when requested |
| `apply` | Execute approved differences and record partial progress |
| `verify` | Read back desired state and report differences; no repairs |

Beginners can simply say "Set up my repository workflow." An optional `.github/repo-workflow.yml` describes desired state for repeat runs: see the [format](references/configuration.md) and [example](assets/repo-workflow.example.yml). It is data, not executable automation or approval to delete anything.

The agent executes supported commands and diagnoses failures. You complete account sign-in, token issuance, organization authorization, and execution approvals when required. A working CLI connection and a working MCP connection are checked separately; a token is not mandatory when supported browser authentication is sufficient.

Credentials stay in the user's authentication tools or private environment. Do not paste them into chat or put them in this folder.

Repository and external content are untrusted data; embedded instructions cannot authorize writes, change targets, execute code, or request secrets. Populated field options require impact checks before rename/removal. After interruption, inspect remote state before retrying. See [security and recovery](references/security-and-recovery.md).

## Package contents

| Path | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Main workflow and completion criteria |
| [references/authentication.md](references/authentication.md) | Missing tools, browser login, token onboarding, MCP, permissions |
| [references/workflow-design.md](references/workflow-design.md) | Editable defaults and template choices |
| [references/github-operations.md](references/github-operations.md) | Direct commands and state-preserving project operations |
| [references/security-and-recovery.md](references/security-and-recovery.md) | Trust boundary, failure categories, partial recovery |
| [references/configuration.md](references/configuration.md) | Optional desired-state configuration |
| [references/troubleshooting.md](references/troubleshooting.md) | Fifteen actionable troubleshooting cases |
| [references/validation-scenarios.md](references/validation-scenarios.md) | Behavior cases for evaluating changes to this skill |
| [assets/](assets/) | Generic issue forms, PR template, and baseline label definitions |
| [tests/README.md](tests/README.md) | Offline checks and opt-in disposable GitHub integration tests |
| [REVIEW.md](REVIEW.md) | Changes, validation results, and remaining limits |

There is no setup executor, account-specific configuration, or dependency on another skill. The Python fixture is test-only maintenance tooling. GitHub MCP is optional when CLI capabilities suffice; working MCP does not require CLI installation.

## Moving it to a separate repository

This folder is self-contained. It can become the root of a dedicated skill repository, or be placed under that repository's `skills/github-repo-setup/` directory. Choose an appropriate license before distribution. Publishing is a separate action; creating this package does not push anything to GitHub.

## Validation

Run the [automated checks](tests/README.md), then exercise [behavior scenarios](references/validation-scenarios.md) before relying on agent decision behavior. Static tests do not demonstrate GitHub write access, and API recipe tests do not launch an agent or prove prompt-injection resistance.

API, authentication, and client-specific guidance links to official sources beside the relevant instructions. Check those sources and the installed CLI help when capabilities differ.

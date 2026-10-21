# GitHub Repo Setup

A reusable [Agent Skill](https://agentskills.io/specification) for GitHub issue forms, pull request templates, labels, a repository-linked Projects V2 board, and recovery from partial setup. It supports an empty repository with no authentication and an existing configuration.

## Installation and prerequisites

The installable package is `skills/github-repo-setup/` in [om-bg/github-repo-setup-skill](https://github.com/om-bg/github-repo-setup-skill). Keep that folder together, including references, assets, and scripts; maintainer tests, this README, REVIEW.md, and Git metadata stay outside it.

```text
# Windows, macOS, or Linux; project-local Codex installation
npx skills add om-bg/github-repo-setup-skill --skill github-repo-setup --agent codex

# Project-local Claude Code installation
npx skills add om-bg/github-repo-setup-skill --skill github-repo-setup --agent claude-code

# Local folder, run from its parent directory
npx skills add ./github-repo-setup --skill github-repo-setup
```

The [installer](https://github.com/vercel-labs/skills) handles agent selection and project-local installation. Check its current Node.js requirement before using `npx`; the skill itself does not require Node. For manual installation, place only `skills/github-repo-setup/` under your client's supported skills directory: `.agents/skills/github-repo-setup/` for Codex or `.claude/skills/github-repo-setup/` for Claude Code. Follow the client's reload/discovery procedure: [Codex](https://learn.chatgpt.com/docs/build-skills), [Claude Code](https://code.claude.com/docs/en/skills).

Required: an Agent Skills-compatible agent, network access, and suitable GitHub MCP tools or GitHub CLI (`gh`). Git is needed only for checkout-based operations. Missing tools produce installation guidance; nothing is installed silently. Authentication is guided when missing, with permissions limited to selected operations. Python 3.10+ is optional for the bundled CLI operations helper; suitable MCP operations need no Python. PyYAML is used only by maintainer tests, not by the helper.

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

Beginners can simply say "Set up my repository workflow." An optional, **experimental** `.github/repo-workflow.yml` describes desired state for repeat runs (its schema is unchanged): see the [format](skills/github-repo-setup/references/configuration.md) and [example](skills/github-repo-setup/assets/repo-workflow.example.yml). It is data, not executable automation or approval to delete anything.

The agent executes supported commands and diagnoses failures. You complete account sign-in, token issuance, organization authorization, and execution approvals when required. A working CLI connection and a working MCP connection are checked separately; a token is not mandatory when supported browser authentication is sufficient.

Credentials stay in the user's authentication tools or private environment. Do not paste them into chat or put them in this folder.

Repository and external content are untrusted data; embedded instructions cannot authorize writes, change targets, execute code, or request secrets. Populated field options require impact checks before rename/removal. After interruption, inspect remote state before retrying. See [security and recovery](skills/github-repo-setup/references/security-and-recovery.md).

## Package contents

| Path | Purpose |
| --- | --- |
| [SKILL.md](skills/github-repo-setup/SKILL.md) | Main workflow and completion criteria |
| [references/authentication.md](skills/github-repo-setup/references/authentication.md) | Missing tools, browser login, token onboarding, MCP, permissions |
| [references/workflow-design.md](skills/github-repo-setup/references/workflow-design.md) | Editable defaults and template choices |
| [references/github-operations.md](skills/github-repo-setup/references/github-operations.md) | Direct commands and state-preserving project operations |
| [references/security-and-recovery.md](skills/github-repo-setup/references/security-and-recovery.md) | Trust boundary, failure categories, partial recovery |
| [references/configuration.md](skills/github-repo-setup/references/configuration.md) | Optional desired-state configuration |
| [references/troubleshooting.md](skills/github-repo-setup/references/troubleshooting.md) | Fifteen actionable troubleshooting cases |
| [references/validation-scenarios.md](tests/scenarios.md) | Behavior cases for evaluating changes to this skill |
| [assets/](skills/github-repo-setup/assets/) | Generic issue forms, PR template, and baseline label definitions |
| [tests/README.md](tests/README.md) | Offline checks and opt-in disposable GitHub integration tests |
| [REVIEW.md](REVIEW.md) | Changes, validation results, and remaining limits |

The bundled `scripts/github_workflow.py` supplies narrow, reusable field, view, label, template, and issue-association operations. It does not orchestrate the full setup, process experimental YAML, or change authentication. Offline and live tests call this exact implementation instead of maintaining separate recipes. GitHub MCP is optional when CLI capabilities suffice; working MCP does not require CLI installation.

## Moving it to a separate repository

Use this repository layout as-is: `skills/github-repo-setup/` is the distributable skill; `tests/` and `REVIEW.md` are maintainer files. Installers select the nested skill directory, so those maintainer files and Git metadata are not copied into the installed skill. Choose an appropriate license before distribution. Publishing is a separate action; creating this package does not push anything to GitHub.

## Validation

Run the [automated checks](tests/README.md), then exercise [behavior scenarios](tests/scenarios.md) before relying on agent decision behavior. Static tests do not demonstrate GitHub write access, and implementation integration tests do not launch an agent or prove prompt-injection resistance.

API, authentication, and client-specific guidance links to official sources beside the relevant instructions. Check those sources and the installed CLI help when capabilities differ.

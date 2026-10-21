# Behavior validation scenarios

Use these when evaluating the skill. First perform a read-only walkthrough; use a disposable repository/account only when live mutation tests are separately authorized. Do not create accounts, rotate real credentials, or change the current repository as part of documentation validation.

| Scenario | Expected observable behavior |
| --- | --- |
| Empty repository, no tools or credentials | Identify missing tools; offer authorized installation and authentication; prepare a workflow proposal while waiting; no token requested in chat and no remote mutation before access and choices are settled. |
| User wants CLI only | Use direct CLI/API commands; do not require MCP installation or generate an executor script. |
| CLI works, MCP lacks project tools | Distinguish connection/tool exposure from token permissions; use authorized CLI capability; preserve working credentials. |
| Existing repository with custom labels and linked project | Inventory and reuse resources; show differences; preserve unrelated labels, fields, views, cards, and option IDs. |
| User already approved a design | Resume from actual state without repeating approval; make only missing changes; a second run produces no duplicate resources. |
| User says inspect only | Authentication/access diagnosis and proposal remain read-only; no label, project, issue, file, or configuration mutations. |
| Access works in user terminal but agent shell uses a blocked proxy | Attribute the problem only after comparing contexts; use permitted network approval; never unset an enforced proxy or rotate the token as a first response. |
| User-owned project rejects a fine-grained PAT | Check current documented support; explain supported authentication choices; user issues/authorizes credentials privately; recheck access. |
| Windows GraphQL returns a parse/schema error | Correct quoting or query shape with a harmless read; do not ask for broader permissions to repair malformed input. |
| Project views work but automation rules cannot be inspected | Report verified fields/views separately from enabled-but-unverified workflows; give exact manual steps; no blanket completion claim. |
| Local Git metadata is read-only | Distinguish local restrictions from remote access; use only an authorized publication route and explicit workflow files; report checkout divergence. |
| A protected file and unrelated local work exist | Follow workspace exclusions, inspect only selected workflow paths, and preserve unrelated changes. |
| Network timeout occurs after project creation | Query actual state before retrying; reuse the created project if present. |
| Setup files are pushed to a PR branch | Report the PR and pending default-branch activation; do not claim the issue chooser already uses the new forms. |

## Static validation

- Validate skill frontmatter, name/folder consistency, and relative document links.
- Parse the YAML forms and JSON label manifest. Check form field IDs are unique and required fields have labels.
- Ensure asset default labels are defined in the manifest; optional experiment selection must include its label.
- Check the adapted PR template preserves outcome, references, changes/reasons, scope, verification, and optional follow-up.
- Check this portable package for accidental real account names, repository/project IDs, credentials, workspace paths, or instructions that require another skill.

Static checks validate packaging and internal consistency. Record live authentication, UI behavior, and API mutations as untested until actually exercised with authorization.

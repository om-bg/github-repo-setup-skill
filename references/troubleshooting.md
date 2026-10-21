# Troubleshooting: actionable cases

Consult the matching case after a concrete symptom appears. These are reusable remedies learned from setup work, not a claim that every cause occurred in one session. Confirm the stated condition before applying its remedy. Speculative causes without an established remedy are excluded.

Keep diagnosis scoped to the failed layer. Record the operation, sanitized error, execution context, and read-only checks. Avoid credential dumps, raw authenticated URLs, whole environment listings, or broad configuration reads.

## 1. Repository works but Projects rejects the token

**Confirm:** The same authenticated context can read the repository, but the target owner's project operation returns an access/scope error. Check token type, target ownership, project permissions, and current support.

**Fix:** Use a supported authentication method with the required project permission. For a user-owned Project unsupported by fine-grained PATs, a classic PAT with `project` scope resolved this class of failure; CLI browser authorization with the necessary scope is another supported route. Keep working credentials for unrelated services. Follow [authentication](authentication.md) rather than repeatedly adding repository permissions.

**Verify:** Read that owner's projects, then read back the next authorized real project change. **User action:** sign-in, token issuance, or permission authorization.

## 2. Required MCP tools are absent

**Confirm:** Inspect the actual exposed tool catalog, the selected server/toolsets, and client allow/deny settings. A configured server is not proof that its intended tools loaded.

**Fix:** Enable the necessary supported capability in the authorized configuration scope, then reconnect or restart. Unknown GitHub toolset names can be ignored by the server, so verify names rather than guessing. If the server does not implement the operation, use case 5.

**Verify:** The required tool appears and a target-specific read succeeds. **User action:** client restart or managed configuration change when the agent cannot perform it.

## 3. Reads work but MCP write tools are unavailable

**Confirm:** Check server read-only mode, a `/readonly` endpoint, and client tool restrictions separately from token scopes.

**Fix:** For an authorized write task, change only the relevant read-only restriction when policy and user authorization permit it. Retain intentional restrictions during read-only work. See [GitHub remote server configuration](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md).

**Verify:** The expected write capability is exposed and its next authorized mutation is read back. A broader token alone does not change the tool catalog.

## 4. A token variable exists but the client does not use it

**Confirm:** Compare the configured variable name and its Boolean presence in the actual client process. Distinguish CLI-recognized variable names from the MCP server's configured name.

**Fix:** Align the private environment mechanism with the client setting. Restart/reconnect if the running process inherited an earlier environment. Do not print or copy the token value through agent tools.

**Verify:** Identity and a target read succeed in the previously failing client. See [CLI variable precedence](https://cli.github.com/manual/gh_help_environment) and [MCP authentication](authentication.md#github-mcp-connection).

## 5. MCP cannot perform a required edit

**Confirm:** The operation is absent from the available tool schema; this is a capability gap rather than an authorization denial.

**Fix:** Use an authorized `gh` command or supported API operation. If the public API also lacks the edit, give the exact UI action. Recheck current capabilities instead of treating a past limitation as permanent.

**Verify:** Read back the edited resource, or report the edit as manual and incomplete. Do not claim that a script can supply a missing server/API capability.

## 6. Agent-shell requests fail through a blocked proxy or sandbox

**Confirm:** Compare execution contexts and inspect only relevant proxy settings, with userinfo/passwords redacted. A rejected loopback proxy connection plus working access outside that sandbox identifies an execution restriction; it is not evidence of a bad GitHub token.

**Fix:** Use the environment's approved network permission or sandbox escalation mechanism. If unavailable, report the restriction and request the exact user/admin action. Never clear enforced proxies, disable controls, or switch routes merely to evade a denied operation.

For Codex, the active execution policy matters more than a file edit. Where applicable, `[sandbox_workspace_write] network_access = true` enables workspace-write networking; it does not override managed policy or guarantee an already-running session changed. Edit only the authorized workspace configuration, preserve unrelated values, and verify in a fresh applicable execution context. See [official approvals and network guidance](https://learn.chatgpt.com/docs/agent-approvals-security).

**Verify:** Repeat the same harmless GitHub read in the approved context. **User action:** execution approval or administrator policy change when required.

## 7. Misleading authentication or owner errors follow a network failure

**Confirm:** Establish whether GitHub was reached before interpreting `invalid token` or `unknown owner type`. Compare the active account and a simple identity read in the same environment. Inactive accounts can also affect the aggregate auth-status result.

**Fix:** Resolve the confirmed connectivity restriction using case 6, then repeat identity and owner reads. Replace credentials only if access still fails with an actual authentication/permission response.

**Verify:** Identity and the target owner's repository/project reads succeed. Keep the original error and its context distinct from the final diagnosed cause.

## 8. Project exists but is missing from the repository's Projects section

**Confirm:** Identify its owner, linked repositories, visibility, and the viewer's access. A same-named project alone does not establish linkage.

**Fix:** Link the intended existing project to the repository when owner compatibility and access permit it. Do not create a second project to repair a missing link. See [project linking](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/adding-your-project-to-a-repository).

**Verify:** Repository linkage and the selected project's URL; verify viewer visibility separately if necessary.

## 9. Board still shows the default three columns

**Confirm:** Read the selected project's Status options and board grouping. Additional views are not additional Status choices.

**Fix:** Edit Status to the agreed options while preserving IDs, and group board columns by Status. Follow [field operations](github-operations.md#fields-and-columns).

**Verify:** Read all options and grouping, and confirm existing cards retained their values.

## 10. Labels exist in a manifest but not on GitHub

**Confirm:** List actual repository labels and compare them with form defaults and the agreed manifest.

**Fix:** Create missing labels through the label API or CLI, then adapt the forms to the chosen names. Writing `labels.json` alone does not apply anything.

**Verify:** Repository label names, colors, and descriptions match the agreement, and each default form label exists.

## 11. PowerShell corrupts quoted GraphQL arguments

**Confirm:** Syntax errors mention fragments of a quoted value, or the server receives malformed query text while scalar-variable queries work.

**Fix:** Use single-quoted GraphQL text and separate variables. For nested literal Windows arguments, use correctly escaped native arguments or a suitable structured tool. Consult the [quoting examples](github-operations.md#graphql-without-powershell-quoting-failures).

**Verify:** A read-only query using the same argument approach parses successfully before attempting the mutation.

## 12. GraphQL rejects a field shape or pagination

**Confirm:** Distinguish schema validation or `MISSING_PAGINATION_BOUNDARIES` from authorization errors.

**Fix:** Inspect the current field/type, use connection `nodes`/`edges`, supply `first` or `last`, and follow cursors for full inventories. Do not repeatedly retry an unchanged query or adjust token permissions for schema errors.

**Verify:** The corrected query returns the intended fields and complete relevant results. Use [current Projects schema](https://docs.github.com/en/graphql/reference/projects).

## 13. Status changes risk clearing existing card assignments

**Confirm:** Compare the proposed complete option list with original option IDs and current item values. Removing and recreating the same label can change identity.

**Fix:** Preserve IDs when renaming or reordering. Retain unrelated options unless their removal was agreed. If values were already cleared, restore them only from a reliable prior mapping; do not infer a card's old status from its title.

**Verify:** Option IDs and each affected card's assignment match the intended mapping. This is a preventive rule, not a reason to alter unaffected cards.

## 14. Git refuses a checkout with dubious ownership

**Confirm:** Check the reported path against the intended, user-trusted workspace. Do not mark an arbitrary repository safe.

**Fix:** For a confirmed trusted path, use a per-command exception such as `git -c safe.directory="D:/trusted-workspace" status --short`, adapted to the actual path. Avoid user-wide or wildcard exceptions.

**Verify:** The intended Git command succeeds. This exception does not change filesystem write permissions. See [Git safe.directory](https://git-scm.com/docs/git-config#Documentation/git-config.txt-safedirectory).

## 15. Local Git metadata prevents publication

**Confirm:** Distinguish a local filesystem denial from a remote GitHub write denial. Identify the exact selected workflow files and the publication authorization.

**Fix:** Request the permitted filesystem action, or use an already-authorized remote file API with explicitly selected workflow paths when the restriction is local-only. Preserve local changes and branch policy. If the intended action itself was denied, stop rather than routing around that denial.

**Verify:** Read remote branch content and the resulting commit/PR; explain any local/remote divergence. Never upload a directory wholesale to avoid a local Git problem.

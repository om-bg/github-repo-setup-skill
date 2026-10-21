# Authentication and onboarding

Read when tools, identity, permissions, or a GitHub MCP connection are missing. Treat CLI credentials, MCP credentials, repository permissions, project permissions, and command-network permissions as separate layers.

## Tools and target

Check availability without installation:

```powershell
Get-Command git, gh -ErrorAction SilentlyContinue
```

For POSIX shells on Linux/macOS:

```sh
command -v git
command -v gh
```

Check the agent's MCP tool catalog as well. Working MCP may cover the task without either executable. If a needed tool is absent, identify the OS and offer the official [GitHub CLI installation](https://github.com/cli/cli#installation) or [Git installation](https://git-scm.com/downloads) path. Execute installation only within the user's authorized scope; otherwise give the exact next step. Rediscover the executable after installation or a terminal restart. Do not install Node, Python, or another runtime merely because this package's optional maintenance tests use it.

With an existing checkout, inspect the requested remote or `gh repo view` metadata without printing credential-bearing URLs. Without a checkout, use an explicit repository identity; remote API work can proceed without cloning. For an absent repository, prepare owner/name/visibility and use `gh repo create --help` only after creation is authorized. An empty repository may have no default branch or template directory; this is an initial state, not an authentication error.

## Reuse existing authentication

Use the chosen host consistently. The examples below target GitHub.com; pass `--hostname` to `gh auth`/`gh api` for another host and use that host's repository identity. Check whether the installed `gh project` route supports that host before proceeding.

```powershell
gh auth status --hostname github.com
gh api user --jq .login
```

Do not use `--show-token`, `gh auth token`, verbose HTTP authorization logging, or read credential-store files. An inactive account can make an overall status command fail while the active account still works. Compare the active identity with the target owner rather than logging everyone out.

If a token environment variable overrides stored CLI credentials, check only its presence and configured name. For GitHub.com, `gh` recognizes `GH_TOKEN` and `GITHUB_TOKEN`; an arbitrary name such as `GITHUB_PAT` is not automatically a CLI credential. An MCP server can reference a differently named variable. See [CLI environment precedence](https://cli.github.com/manual/gh_help_environment).

## Starting without credentials

Offer the route matching the requested tools. Do not require a manually created PAT just to use CLI.

### CLI browser authentication

When authorized, start the interactive sign-in and let the user complete the browser/device step. For a scope that includes project writes:

```powershell
gh auth login --hostname github.com --web --scopes project
```

For an existing CLI OAuth login missing Projects permission:

```powershell
gh auth refresh --hostname github.com --scopes project
```

Request `read:project` instead for authorized diagnosis that needs only project reads; omit additional Projects scopes when no project operation is needed. `audit`, `plan`, and `verify` do not initiate login/refresh or alter credentials without a separate request for that onboarding action. CLI sign-in may update the host's stored credentials; explain that account-level effect before starting it. Do not select insecure storage. If the environment cannot host the interactive flow, provide the command for the user's terminal and resume with identity/access checks afterward. See [login](https://cli.github.com/manual/gh_auth_login) and [refresh](https://cli.github.com/manual/gh_auth_refresh).

### PAT onboarding when needed

Reuse a supported token if present. If MCP requires a PAT or another route cannot cover the required operations, guide the user through GitHub Settings > Developer settings > Personal access tokens. The user selects the token type, permissions, expiry, and completes issuance privately. Never operate on the token's displayed value or ask for it in chat.

Use a method supported by the target owner and operation. GitHub currently lists user-owned Projects among fine-grained PAT limitations; for that case, a classic PAT with the necessary `project` scope is a documented route. Organization Projects and organization policies may require different permissions or authentication. Verify current support rather than requiring classic PATs for every repository. See [token types, creation, and limitations](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

Permission requirements depend on the selected route:

| Operation | Access to verify |
| --- | --- |
| Publish templates | Repository Contents write, including the intended branch route |
| Create/update labels and issues | Appropriate repository Issues or Pull requests permission for the endpoint |
| Open a PR for setup files | Repository Pull requests write, when using that route |
| Read/update a project | Project read/write access for the owning user or organization |
| Link a project to a repository | Required access to both resources |

For classic PATs, choose the repository scope appropriate to public/private access plus `project` for project mutations. Let CLI's supported login flow handle its additional requirements when using CLI sign-in. Organization SSO or approval can be required separately. See [Projects API authentication](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects#authentication) and [label endpoint permissions](https://docs.github.com/en/rest/issues/labels#create-a-label).

The user supplies a token through a private credential/environment mechanism outside agent-visible input and logs. Record only the variable name and the fact that it is available. Do not create a plaintext token file, add a literal token to TOML, or retrieve a CLI token to copy it into MCP. If private credential entry is unavailable, stop that authentication branch and use another authorized supported route.

## GitHub MCP connection

If MCP was requested or provides useful missing capabilities, discover the actual client and supported server configuration. Prefer an existing authorized connection. Where the client/server supports a suitable OAuth flow, let the user complete it; do not assume every remote GitHub MCP deployment supports the same flow.

For Codex's HTTP transport, this is a credential-free example for **project-local** `.codex/config.toml`, to adapt and merge only when configuration changes are authorized:

```toml
[mcp_servers.github]
url = "https://api.githubcopilot.com/mcp/"
bearer_token_env_var = "GITHUB_PAT"
```

The user makes the named variable available to the process that launches the client, then reconnects/restarts as required. Verify presence as a Boolean, not its value. Preserve unrelated configuration. An allowlist, server read-only mode, or missing toolset can limit exposed tools independently of token permissions. Select only needed supported tools/toolsets; discover their current names rather than hardcoding them here. See [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) and the [GitHub remote server](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md).

A trusted project may load project-local configuration; client or managed policy can still limit it. Do not inspect or change user-level configuration merely because local setup failed. See [configuration scope](https://learn.chatgpt.com/docs/config-file/config-basic).

## Verify before continuing

After authentication, read the target repository and list the owner's projects using [operations](github-operations.md). A successful empty project list is valid for a new account. Read success alone does not prove write access: inspect reported permissions where available, then verify each authorized real mutation. Do not create disposable resources merely to probe writes.

If CLI succeeds while MCP fails, diagnose MCP. If the same CLI read works in the user's terminal but fails in the agent shell, diagnose the execution environment. Do not rotate a working token to repair a shell-network restriction.

# Tests

Tests validate the installable package and import its shared `scripts/github_workflow.py` implementation. Setup/cleanup code only manages disposable test fixtures; workflow behavior is not duplicated in the tests. They do not launch an agent or prove prompt-injection resistance. Use the [behavior scenarios](scenarios.md) for those evaluations.

## Offline checks

From this skill folder, use Python 3.10+ with PyYAML. Install test dependencies explicitly in your chosen virtual environment; the optional CLI helper needs Python but not PyYAML; MCP-only use needs neither.

```text
python -m pip install -r tests/requirements-dev.txt
python -m unittest discover -s tests -v
```

Without `--live`, integration tests are skipped before any subprocess/network call. Offline checks validate metadata, assets/config, links, subprocess data handling, and simulated error classification. Tests never install dependencies.

## Disposable integration tests

```text
python tests/test_github_integration.py --live --owner YOUR_ACCOUNT
```

Replace the account placeholder. `--host` optionally selects another host with compatible APIs. The live suite uses existing `gh` authentication and requires an explicitly selected personal account matching the active user. Passing `--live` authorizes creation, writes, and guarded deletion of **this run's** disposable resources: one uniquely named private empty repository and one private V2 project. The current checkout's remote is never used.

Before creating resources, this personal-account fixture requires reported classic/OAuth scopes `repo`, `project`, and `delete_repo`. Cleanup needs `delete_repo`; normal skill use does not. Missing scopes skip setup without changing credentials. Tokens without reported scopes are not assumed safe for cleanup and are skipped. Do not broaden a production credential just for these tests; prefer a dedicated test account/credential.

Offline stateful integration cases exercise the same implementation on fresh/existing/partial state, repeated execution, blocked networking, option-ID preservation, drift, pagination, filters, grouping, and associations. Separate shell tests execute the documented read-only examples in Windows PowerShell and a POSIX shell with captured native arguments. Live cases exercise this implementation on disposable GitHub resources, including actual Status and Priority updates, views, and issue associations.

The real missing-write-permission case is optional: privately supply `REPO_SETUP_READ_ONLY_TOKEN` to the process. It must read the newly created private repository but lack label write access. The test verifies the read, then expects write denial. Its value goes only through the child environment. Without it, that case is skipped; offline error classification still runs. An unexpectedly successful write fails the test and is removed with the disposable repository.

## Cleanup and limitations

Cleanup is registered before creation and checks exact IDs, owner, and this run's unique marker before deletion. It never deletes by prefix. Cleanup errors fail the run. The suite prints a credential-free journal path in the OS temporary directory and records returned IDs/URLs after each create.

Ordinary exceptions trigger cleanup; a killed process or lost create response can still leave resources behind. Inspect the journal and exact run name in the selected account, confirm identity, then remove only the matching resources through GitHub. Do not batch-delete by prefix. Inspect unknown outcomes before retrying creation.

Live failures surface sanitized categories, not raw response traces. MCP behavior, browser authentication, UI-only settings, actual agent behavior, and execution on operating systems not exercised remain unverified. These tests are maintenance tooling, not the skill's runtime implementation.

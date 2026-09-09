# GitHub Actions cheat sheet

Reference for `.github/workflows/docker-publish.yml` and the `gh` CLI.
Official: https://docs.github.com/en/actions.

## Anatomy

```
name: ...
on: [triggers]
env: {workflow-wide variables}
permissions: {GITHUB_TOKEN scopes}
jobs:
  job_id:
    runs-on: ubuntu-latest
    needs: [other_job]          # ordering
    if: ${{ <expression> }}     # run condition
    strategy:
      matrix: {k: [a, b]}       # run the job once per combination
    steps:
      - uses: actions/checkout@v6      # a reusable action
      - name: ...
        run: |                          # shell commands
          ...
```

- A **workflow** is a file. A **job** runs on its own fresh runner. Jobs run in
  parallel unless linked by `needs:`.
- A **step** is one action or one `run:` script. Steps in a job share the
  runner and its filesystem.
- The runner is a clean VM. Nothing persists between jobs except declared
  artifacts and job `outputs`.

## Triggers, `on:`

| Trigger | Fires when |
|---|---|
| `push: branches: [main]` | A commit is pushed to `main` |
| `push: tags: ["v*.*.*"]` | A matching tag is pushed |
| `pull_request: branches: [main]` | A PR targets `main` |
| `workflow_dispatch` | You click "Run workflow" in the Actions tab |
| `schedule: - cron: "..."` | On a cron schedule |

This repo triggers on push to `main` and `develop`, on `v*.*.*` tags, on PRs,
and manually.

## Permissions and GITHUB_TOKEN

Every run gets an automatic `GITHUB_TOKEN`. Its power is the smaller of:

- the repo default (Settings, Actions, General, Workflow permissions), and
- the `permissions:` block in the workflow file.

Check the repo default:

```
gh api repos/OWNER/REPO/actions/permissions/workflow
```

`"default_workflow_permissions": "read"` plus a Docker push to GHCR gives
`denied: permission_denied`. Fixes: set the default to "Read and write", or
avoid needing write. This repo took the second path and gates the image push to
version tags.

## Expressions and contexts

`${{ ... }}` evaluates an expression. Useful contexts:

| Context | Example value |
|---|---|
| `github.ref_type` | `branch` on a branch push, `tag` on a tag push |
| `github.ref_name` | `main`, or `v0.2.0` |
| `github.event_name` | `push`, `pull_request` |
| `github.sha` | the commit SHA |
| `matrix.<key>` | the current matrix value |

This repo uses `if: ${{ github.ref_type == 'tag' }}` on the `run_tests` job and
`push: ${{ github.ref_type == 'tag' }}` on the build step.

## This workflow's jobs

| Job | Does | Runs on |
|---|---|---|
| `update-lockfile` | `uv lock`, commit any change | every trigger |
| `plugin_unit_tests` | `nomad-plugin-tests`, matrix of 2 | every trigger |
| `build` | build image, matrix `app` and `jupyter`, push only on tags | every trigger |
| `run_tests` | pull images, health and entry-point tests | tags only |

`PLUGIN_TESTS_PLUGINS_TO_SKIP` in `env:` excludes a plugin from
`plugin_unit_tests`. `nomad_econversion_plugins` is skipped because it ships no
pytest suite.

## The `gh` CLI

| Command | What it does |
|---|---|
| `gh run list --limit 10` | Recent runs |
| `gh run list --json databaseId,status,conclusion,displayTitle --jq '.[]'` | Machine-readable |
| `gh run view RUN` | Job tree and the annotations summary at the bottom |
| `gh run view RUN --log-failed` | Only the failed steps' logs |
| `gh run view RUN --log-failed --job JOB` | One job's failed log |
| `gh run watch RUN --exit-status` | Block until done, non-zero exit if it failed |
| `gh run rerun RUN --failed` | Rerun only the failed jobs |
| `gh api repos/OWNER/REPO/actions/permissions/workflow` | Read the token default |
| `gh workflow run FILE` | Trigger a `workflow_dispatch` |

Start debugging with `gh run view RUN` and read the `ANNOTATIONS` block first.
Then drill in with `--log-failed`.

## Telling a code failure from a settings failure

| Log line | Kind | Fix |
|---|---|---|
| `No module named pytest` | code or config | skip the plugin, or add pytest to it |
| `denied: permission_denied: read_package` | settings | grant package write, or do not push |
| `ModuleNotFoundError: nomad_econversion_plugins` | code | the dependency is not installed, fix `pyproject.toml` |
| `error: pathspec ... did not match` | code | a script references a path that does not exist |
| `Resource not accessible by integration` | settings | `permissions:` block too narrow |

## Gotchas

- Every job is a fresh machine. Files a job writes are gone unless uploaded as
  an artifact or passed as an `output`.
- A `push:` to `main` triggers this workflow every time, including for a
  docs-only commit. Expect a run.
- The `permissions:` block can only narrow or set scopes, never exceed what the
  repo or org allows.
- `matrix` with `fail-fast: false` lets the other matrix legs finish even if
  one fails, which makes debugging easier.

# Lab 5: read, break, and fix the CI workflow

Reproduces the CI debugging recorded in the "CI fixes" note of
`docs/oasis-adoption-plan.md`.

By the end you will be able to read `.github/workflows/docker-publish.yml`, use
the `gh` CLI to inspect a failed run, tell a code failure from a settings
failure, and apply the two fixes the team used.

Modules exercised: 12 GitHub Actions.

Time: 2 to 3 hours. Prerequisite: Labs 0 to 3 done, so you know what the image
build and the plugin are.

## 1. Read the workflow

```
cd ~/labs/oasis-lab0
less .github/workflows/docker-publish.yml
```

Map it out:

- `on:` triggers: `push` to `main` and `develop`, `push` of tags `v*.*.*`,
  `pull_request`, and manual `workflow_dispatch`.
- `permissions:` at the top requests scopes for `GITHUB_TOKEN`, including
  `packages: write`.
- Jobs:
  - `update-lockfile`: runs `uv lock`, commits any change.
  - `plugin_unit_tests`: a matrix of 2 groups, runs `nomad-plugin-tests`.
  - `build`: a matrix of `app` and `jupyter`, builds the image and pushes to
    GHCR.
  - `run_tests`: `needs: build`, pulls the pushed images and runs health and
    entry-point tests.
- `env.PLUGIN_TESTS_PLUGINS_TO_SKIP`: a knob to exclude plugins from the test
  step.

## 2. Inspect past runs with `gh`

```
gh run list --limit 10
gh run list --limit 10 --json databaseId,status,conclusion,displayTitle \
  --jq '.[] | "\(.databaseId) \(.status) \(.conclusion) \(.displayTitle)"'
```

Pick a failed run id, call it `RUN`.

```
gh run view RUN
gh run view RUN --log-failed | tail -80
gh run view RUN --log-failed --job <failing-job-id> | tail -80
```

`gh run view RUN` shows the job tree and, at the bottom, the `ANNOTATIONS`
section with the short error lines. Start there.

## 3. The two failures the team hit

### Failure 1: plugin unit tests

Annotation and log:

```
Run plugin tests: Process completed with exit code 1
... /venv/bin/python: No module named pytest
Tests failed for packages: nomad_econversion_plugins
```

Cause: `nomad-plugin-tests` clones each installed plugin repo, builds a venv,
and runs `pytest` against it. `nomad-econversion-plugins` ships no pytest
dependency and no tests, so the step errors.

This is a **code or config** fix, not a settings fix. The team excluded the
plugin from the test step:

```yaml
  PLUGIN_TESTS_PLUGINS_TO_SKIP: "nomad_econversion_plugins"
```

### Failure 2: GHCR push denied

Annotation:

```
buildx failed with: ERROR: failed to push
ghcr.io/cates-tum/nomad-oasis-econversion:main: denied:
permission_denied: read_package
```

Cause: the repository's default workflow permission is read-only.

```
gh api repos/cates-tum/nomad-oasis-econversion/actions/permissions/workflow
```

You see `"default_workflow_permissions": "read"`. The Docker push needs package
write.

This has two possible resolutions:

- **Settings fix**: repo Settings, Actions, General, Workflow permissions, set
  to "Read and write". For an existing package that is still not linked to the
  repo, you also grant the repo write access on the package's own settings
  page.
- **Workflow fix, what the team chose**: build the image on every push to catch
  breakage, but only push it on version tags, so day-to-day CI needs no package
  write. In the `build` job:

  ```yaml
  push: ${{ github.ref_type == 'tag' }}
  ```

  And gate the job that pulls the pushed image:

  ```yaml
  run_tests:
    if: ${{ github.ref_type == 'tag' }}
  ```

Trade-off: the image boot and health test now runs only at tag time. Before the
first `vX.Y.Z` tag you must apply the settings fix so the tagged push succeeds.

## 4. Apply the fixes and watch a green run

If your fork is still red, make the two edits above, commit, push, and watch:

```
git add .github/workflows/docker-publish.yml
git commit -m "Skip the untested plugin and push images only on tags"
git push origin main
gh run watch $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
```

`--exit-status` makes `gh` exit non-zero if the run fails, so you can tell at a
glance.

## 5. Verification checklist

- [ ] You can name every job in the workflow and its trigger.
- [ ] From a failed run you found the failing step and read its log with `gh`.
- [ ] You can state which of the two failures is a settings issue and which is
  a workflow issue.
- [ ] Your fork has a green run on `main`.

## Challenge

1. On a scratch branch, remove `nomad_econversion_plugins` from
   `PLUGIN_TESTS_PLUGINS_TO_SKIP`, push the branch, and watch the plugin test
   job fail. Read the log and confirm it is the same `No module named pytest`.
   Restore the skip. Delete the branch.
2. Given only this line from a run, say whether the fix is code or settings and
   why: `denied: permission_denied: read_package`. Then do the same for:
   `ModuleNotFoundError: No module named 'nomad_econversion_plugins'`.
3. Explain what `github.ref_type` evaluates to for a push to `main` versus a
   push of the tag `v0.2.0`, and therefore which jobs run in each case after
   the team's fix.

## Troubleshooting

- **`gh` commands fail with 401 or 404.** `gh auth status`. You may need to log
  in again, or the token lacks a scope. Listing packages needs
  `read:packages`.
- **`gh run watch` says no runs.** The push did not trigger the workflow.
  Check `on:` matches your branch, and that you pushed to the fork, not
  upstream.
- **A run is queued for a long time.** GitHub-hosted runner capacity. Wait, or
  check the Actions tab for a usage or billing block.

## Where this maps in the record

- `oasis-adoption-plan.md`, the "CI fixes (2026-09-09)" note in the Phase 5
  section.
- Commits `4effeb8` (the workflow fix) and `a4934b7` (recording it).

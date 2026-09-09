# Temporal cheat sheet

Reference for the job orchestrator that runs NOMAD file processing. Working
proficiency level. Free course: https://learn.temporal.io/.

## What it is

Temporal runs long, failure-prone work as a **workflow**: a function whose
progress is persisted after every step, so it survives worker crashes and
restarts and resumes exactly where it stopped. NOMAD uses it for upload
processing: parse the mainfile, run normalizers, write to Mongo and
Elasticsearch.

Pieces in this stack:

| Piece | Role |
|---|---|
| `temporal` service | the server, gRPC on port 7233 |
| `postgresql` service | Temporal's own state store, not NOMAD's |
| `temporal-setup-db` | one-shot, creates the Temporal schema in Postgres |
| `temporal-create-namespace` | one-shot, creates the `default` namespace |
| `worker` service | runs `nomad.cli admin run action-internal-worker`, executes workflow activities |
| `app` service | registers a workflow when an upload needs processing |

## Core concepts

- **Workflow**: the durable orchestration. Deterministic: it may be replayed
  from history, so it must not do IO directly.
- **Activity**: a single unit of real work (parse a file, write a document).
  Called by the workflow. Retried on failure with backoff.
- **Namespace**: an isolation boundary. This stack uses `default`. If the
  `temporal-create-namespace` job did not run, every workflow fails with
  `Namespace default is not found` and NOMAD returns 500.
- **Task queue**: workers poll a queue for activities to run.
- **Retry policy**: a failed activity retries with growing backoff. A
  permanently broken activity retries forever unless the workflow is
  terminated.

## The CLI

The `temporal` binary lives only in the admin-tools image, which the
`temporal-create-namespace` service already uses. Run it through that service:

```
docker compose run --rm --no-deps --entrypoint temporal \
  temporal-create-namespace <command> --address temporal:7233 -n default <args>
```

| Command | Does |
|---|---|
| `workflow list` | Recent workflows and their status |
| `workflow describe --workflow-id ID` | One workflow's detail and pending activities |
| `workflow show --workflow-id ID` | Full event history |
| `workflow terminate --workflow-id ID --reason "text"` | Stop it now, no cleanup |
| `workflow cancel --workflow-id ID` | Request graceful cancellation |
| `operator namespace list` | Namespaces |

Older images ship `tctl` instead of `temporal`. If `temporal` is not found,
try `tctl --address temporal:7233 workflow list`.

## The scenario you will hit

A failed or deleted upload can leave a workflow retrying an activity forever.
The worker logs a traceback on every attempt, and later a
`KeyError: Upload with id ... does not exist` once the upload record is gone.

Fix:

```
# find it
docker compose run --rm --no-deps --entrypoint temporal \
  temporal-create-namespace workflow list --address temporal:7233 -n default

# stop it
docker compose run --rm --no-deps --entrypoint temporal \
  temporal-create-namespace workflow terminate \
  --address temporal:7233 -n default --workflow-id <id> --reason "orphaned upload"
```

## SQL is not the model here

Temporal state is an append-only event history in PostgreSQL, not tables you
query. Do not query the `temporal` Postgres database directly. Use the CLI or
the Web UI. In this minimal stack the Web UI is not exposed; the CLI is the
tool.

## Gotchas

- `Namespace default is not found`: the `temporal-create-namespace` one-shot
  did not run. It is in the `depends_on` of `app` and `worker`, so a normal
  `docker compose up -d app worker proxy` runs it. Otherwise
  `docker compose up -d temporal-create-namespace`. It is idempotent.
- A plain `docker run` of the admin-tools image is blocked by the sandbox on
  the reference VM. Going through the compose service works.
- Terminating a workflow is abrupt. It does not undo partial writes. For NOMAD
  processing that is usually fine because reprocessing is idempotent.
- `worker` shows `condition: service_started` not `service_healthy` in
  `depends_on`, so other services do not wait for it to be truly ready.

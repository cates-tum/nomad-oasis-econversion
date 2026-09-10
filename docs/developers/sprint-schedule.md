# Sprint schedule

A day-by-day run of `learning-plan.md` at about 4 hours a session, roughly 15
sessions. Built for a concentrated block rather than two-to-four weeks part
time.

## Rules

- One rule only: do not start the next session until you have passed the
  current session's checkpoint without notes. A failed checkpoint means repeat,
  even if it costs an extra day. The schedule has slack for exactly this.
- Each session is about 2 hours of concept reading and 2 hours of lab. If the
  reading runs long, cut it, not the lab. The lab is what makes it stick.
- Keep the matching cheat sheet open the whole session.
- "Read" entries are in `learning-plan.md` under each module. This file does
  not repeat the links.

## The sessions

| # | Modules | Lab | Gating checkpoint |
|---|---|---|---|
| 1 | 0 HTTP, 1 shell | Lab 0, sections 1 to 2 | Explain `curl -s localhost/nomad-oasis/alive` token by token. Write from memory the `curl` for a JSON POST with a bearer token. Say why `ls -la .volumes/fs` shows a non-you owner. |
| 2 | 2 YAML, 3 Docker (start) | Lab 0, image build step | Spot a tab and a should-be-quoted string in a 20-line YAML by eye. State what an image is versus a container. |
| 3 | 3 Docker (finish) | Lab 0, image build step | Describe what `--target final` does in this repo's `Dockerfile` and why the builder mounts only `pyproject.toml`, `uv.lock`, `.git`. |
| 4 | 4 Docker Compose | Lab 0, full | From `docker-compose.yaml` alone, list named-volume services, bind-mount services, and what `docker compose up -d app worker proxy` starts. |
| 5 | 5 NOMAD architecture | Lab 0, "walk the stack" | Draw the 7 services and the arrows from memory. Say which database is NOMAD's and which is Temporal's. |
| 6 | 6 data model, 7 datastores (Elasticsearch part) | Lab 1 | After an upload, name the three places the data now exists and the command to inspect each. |
| 7 | 7 datastores (Mongo, Temporal parts) | Lab 1 challenge | Write an Elasticsearch aggregation that counts entries by `entry_type`, the equivalent MongoDB aggregation, and the SQL for the same question. |
| 8 | 8 metainfo schemas | Lab 2 and its challenge | Write a five-quantity ELN schema from scratch with one enum and one number-with-unit, upload it, create an entry. |
| 9 | 9 packaging and uv | Lab 3 | Explain what an entry point is, where NOMAD reads it, and why the builder cannot use a local path. |
| 10 | 10 `ui.apps`, 11 nginx | Lab 4, both halves | Add a second app locked to a different schema, validate it against the model without restarting, apply it. Add a `curl`-tested redirect and say why `=` was the right match type. |
| 11 | 12 GitHub Actions | Lab 5 | Given a failed run URL, find the failing step, read its log, name the cause, say whether the fix is code or settings. |
| 12 | 13 API and auth (read) | Lab 6, sections 1 to 4 | Produce a `422` and read which field it names. Get a token and read its `sub` and `exp`. Say why the same query differs with and without the token. |
| 13 | 13 API and auth (finish) | Lab 6, sections 5 to 7, and challenge | From a cold stack, `curl` only: token, create upload, add file, poll, query by a custom quantity, fetch one archive section, delete. State `401` vs `403` vs `422`. |
| 14 | 14 async and the source | Lab 7, sections 1 to 5 | Name the file and function for parser matching, the file for the entries query route, and the Pydantic class that validates `ui.apps`. Say why a slow parser does not freeze the API. |
| 15 | 14 async and the source (finish) | Lab 7, sections 6 to 7, and challenge | Produce a written 5-hop trace from upload request to Elasticsearch document, each hop tied to a file and a log line. |
| slack | none | redo | Any checkpoint you passed only with notes. Both lab challenges you skipped. |

## If you have less time than 15 sessions

Cut from the end, not the middle. Sessions 1 to 5 (operate the stack) are load
bearing for everything after. Sessions 12 to 15 (the API and the source) are
the manual-control goal. If forced to choose, sessions 6 to 11 can compress:
do the labs, skim the deeper reading, come back to it.

## If a session runs short

Do the module's challenge, or read the linked "far more surface than we use"
material the cheat sheet points to (Elasticsearch and Temporal both have a lot
past what this stack touches).

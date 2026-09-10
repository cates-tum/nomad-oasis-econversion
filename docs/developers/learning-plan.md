# Self-study plan

Reproduce Phases 0 to 4 of `docs/oasis-adoption-plan.md` by hand, then go one
tier past them to full manual control of the API and the source. Fifteen
modules in five tiers (Tier 0 and Tier 4 were added for the manual-control
goal; Tiers 1 to 3 are the phase reproduction). Each module lists the
concepts, what to read, the lab that exercises it, and a checkpoint you should
be able to pass before moving on.

Rough budget: 55 to 60 hours, concept reading plus labs. At 4 hours a day that
is about 15 sessions. `sprint-schedule.md` lays those sessions out day by day
with the gating checkpoint for each. Tier 1 is the largest lift if containers
are new to you; Tier 4 is the second largest if reading an unfamiliar codebase
is new.

## Bridge from a data science background

If your infrastructure experience is Databricks, SQL, and pip, map the new
tools onto what you know:

| Familiar | Here |
|---|---|
| A managed cluster of coordinated machines | `docker-compose.yaml` declares 7 services; Docker Compose starts and connects them on your machine |
| `spark.read`, SQL over a catalog | The catalog is split three ways: MongoDB holds metadata, Elasticsearch holds the search index, disk holds the parsed archive. NOMAD's REST API is the query layer over all three |
| `pip install a-package` | You build a package with an entry point. NOMAD discovers plugins through Python's entry-points system |
| A fixed cluster library set | `uv.lock` is an exact, hash-verified `requirements.txt`. `uv` is the resolver that writes it |
| Spark's lazy DAG of stages | Temporal runs file processing as a durable workflow, a DAG of activities that survives restarts |
| Re-running a notebook cell | Config is a bind-mounted file. You re-apply it by recreating a container, not by re-running code |
| A workspace hides the cluster from you | Nothing is hidden. You are the operator. Every service, port, and volume is in files you edit |

## What each phase exercised

| Phase | New tools | Modules |
|---|---|---|
| 0 setup | shell, git, GitHub, Docker, Compose, nginx, YAML, `.env` | 1 to 5 |
| 1 data in | NOMAD data model, Elasticsearch, MongoDB, Temporal, `docker compose exec` | 6, 7 |
| 2 YAML schema | NOMAD metainfo and ELN annotations | 8 |
| 3 Python plugin | `pyproject.toml`, entry points, `uv` and lockfiles, git tags, dependency pinning | 9 |
| 4 custom app and branding | `ui.apps` config model, pydantic validation, nginx redirects, static overrides | 10, 11 |
| CI fixes | GitHub Actions, `gh` CLI, GHCR permissions | 12 |

Module 0 and Tier 4 are not tied to a phase. Module 0 is the one cross-cutting
concept every service uses. Tier 4 is the depth pass for full manual control:
driving the whole system through the API as an authenticated user, and reading
the app, worker, and parser source. The Phase 5 parser-matching write-up in
`oasis-adoption-plan.md` is the source-reading exercise for Module 14.

---

# Tier 0: how the parts talk

## Module 0: HTTP and the request lifecycle

Concepts: client and server; the request and response cycle; URL parts (scheme,
host, port, path, query string); HTTP methods and their meaning (`GET` read,
`POST` create or query, `PUT`/`PATCH` update, `DELETE` remove); status classes
and the specific codes you will see here (`200 201 204`, `301 302`, `400 401
403 404 409 422`, `500 502 503`); headers (`Host`, `Content-Type`, `Accept`,
`Authorization`, `Set-Cookie`); the request body and JSON payloads; `curl` in
depth (`-i -v -s`, `-X`, `-H`, `-d` / `--data-binary`, `-u`, `-L`, `-o`, `-w
'%{http_code}'`, `-G --data-urlencode`); what changes when a reverse proxy
sits in front (the client sees the proxy, the proxy sees the app); REST in one
line; OpenAPI as a machine-readable description of an API.

Why here: every service in this stack speaks HTTP. You talk to nginx, the NOMAD
app, Elasticsearch, and Temporal over it. `curl -s localhost/nomad-oasis/alive`
is HTTP. Modules 7, 11, and all of Tier 4 assume you read a response envelope
without thinking about it.

Read: MDN "An overview of HTTP" and "HTTP response status codes"
(https://developer.mozilla.org/en-US/docs/Web/HTTP). `man curl`.
`cheatsheets/http.md`.

Lab: folded into Lab 0 (the health check) and Lab 1 (first API calls). No
standalone lab.

Checkpoint: given a raw `curl -i` response, name the status class, say what the
`Content-Type` header tells you, and write from memory the `curl` command that
sends a JSON `POST` body with a bearer token.

---

# Tier 1: operate the stack

Goal: bring the stack up from nothing, read the compose file and know what each
line does, and debug a service that will not start.

## Module 1: Shell and filesystem fluency

Concepts: absolute vs relative paths; `cd ls cat less head tail`; `grep` and
pipes `|`; output redirection `>` and `>>`; exit codes and `$?`; environment
variables and `$PWD`; file permissions (`rwx`, `chmod`, `chown`); users,
groups, and numeric uid/gid; why a bind-mounted directory shows an unfamiliar
owner; `sudo`; `curl` basics and `curl -s -o /dev/null -w '%{http_code}'`.

Why here: every step is shell. `.volumes/fs` is owned by uid 1000 because the
container process runs as uid 1000 and writes through the bind mount to your
disk. When a container will not start, you read logs and check file ownership.

Read: MIT "The Missing Semester", lectures 1 and 2
(https://missing.csail.mit.edu/). `man` pages for `chmod` and `curl`.

Lab: folded into Lab 0.

Checkpoint: explain `curl -s localhost/nomad-oasis/alive` token by token, and
explain why `ls -la .volumes/fs` shows an owner that is not your username.

## Module 2: YAML and config as the source of truth

Concepts: YAML syntax (indentation, `key: value`, lists with `-`, nested maps,
strings and when to quote, `|` and `>` block scalars, comments, anchors);
common failure modes (tabs, inconsistent indent, unquoted strings that parse as
bool or number). The mental model: the running system is a function of a small
set of text files. You change a file, then re-apply it.

Why here: `configs/nomad.yaml`, `docker-compose.yaml`, and the GitHub Actions
workflow are all YAML. A misindented line is the most common self-inflicted
break.

Read: the "YAML" cheat sheet in `cheatsheets/yaml.md`. Learn X in Y minutes,
YAML (https://learnxinyminutes.com/docs/yaml/).

Lab: folded into Labs 0 and 2.

Checkpoint: given a 20-line YAML file with a tab and a value that should be a
quoted string, find both errors by eye.

## Module 3: Docker

Concepts: image vs container (a class vs an instance); layers and the build
cache; `Dockerfile` instructions (`FROM RUN COPY ARG ENV WORKDIR CMD`,
multi-stage builds and `--target`); `docker build -t name:tag .`;
`docker run`, `docker ps`, `docker logs`, `docker exec`; image registries and
tags; GHCR (`ghcr.io/owner/name:tag`); `docker image ls` and disk use;
`docker system prune`.

Why here: the NOMAD app and worker run from a prebuilt image. You build it once
by hand (`docker build --target final ...`). Understanding layers explains why
a rebuild after a small change is fast or slow.

Read: Docker "Get started", parts 1 to 4
(https://docs.docker.com/get-started/). The `Dockerfile` in this repo, line by
line, against the "Dockerfile reference"
(https://docs.docker.com/reference/dockerfile/).

Lab: Lab 0, the image build step.

Checkpoint: describe what `--target final` does in this repo's `Dockerfile` and
why the builder only mounts `pyproject.toml`, `uv.lock`, and `.git`.

## Module 4: Docker Compose

Concepts: a Compose file declares services, one container each; `services:`,
`image:`, `command:`, `environment:` and `env_file:`, `ports:` (`host:container`),
`volumes:`, `depends_on:` with conditions, `healthcheck:`, `profiles:`;
named volumes vs bind mounts and where each stores data; `docker compose up -d`,
`down`, `down -v`, `ps`, `logs -f`, `logs --since`, `exec`, `run --rm`,
`restart`, `up -d --force-recreate --no-deps`; project name and the default
network where services resolve each other by service name.

Why here: `docker-compose.yaml` is the whole stack. You will start subsets
(`up -d app worker proxy`), watch logs, exec into containers to inspect state,
and learn why `restart` sometimes does not pick up a changed bind-mounted file
while `--force-recreate` does.

Read: Compose "how Compose works" and the file reference
(https://docs.docker.com/compose/). The `cheatsheets/docker-compose.md` file.

Lab: Lab 0.

Checkpoint: from `docker-compose.yaml` alone, list which services store data in
named volumes, which use bind mounts, and what starts when you run
`docker compose up -d app worker proxy`.

## Module 5: The NOMAD architecture

Concepts: the 7 services and their jobs (`app` API and GUI, `worker`
processing, `proxy` nginx front door, `temporal` orchestrator, `postgresql`
Temporal's state store, `mongo` NOMAD metadata, `elastic` search index) and the
two one-shot Temporal init jobs; the request flow (browser to nginx to app);
the data flow (app registers a workflow, worker parses and writes to Mongo and
Elasticsearch, GUI reads back through app); what stays off (NORTH, logtransfer);
central Keycloak instead of a local identity service.

Why here: you cannot debug a stack you cannot draw. Every later lab touches one
or two of these services.

Read: `oasis-adoption-plan.md` sections "Oasis as a plant: the components" and
"The infrastructure stack in one sentence". `cheatsheets/nomad-concepts.md`.

Lab: Lab 0, the "walk the stack" section.

Checkpoint: draw the 7 services and the arrows between them from memory, and
say which database is NOMAD's and which belongs to Temporal.

---

# Tier 2: get data in and model it

Goal: upload data, follow it through processing, inspect it in every store, and
define a new data type as a schema.

## Module 6: The NOMAD data model

Concepts: upload, entry, raw files vs the parsed archive, processing status;
where raw files sit on disk (`.volumes/fs/staging/<upload_id>/raw/`); the
archive as a typed metainfo tree (msgpack on disk); "published" vs unpublished
and why the anonymous API shows nothing; an upload producing one entry or many.

Why here: Phase 1. You need to know what "processed" means before you can tell
whether a parser worked.

Read: `oasis-adoption-plan.md` "Phase 1 implementation notes" and the memory
note summarised in `cheatsheets/nomad-concepts.md`.

Lab: Lab 1.

Checkpoint: after an upload, name the three places the data now exists and the
command to inspect each.

## Module 7: Inspecting the datastores

You chose working proficiency here, so this module goes past inspect-and-debug.

Concepts, Elasticsearch: what an inverted index is; documents, fields,
mappings; the Query DSL (`match`, `term`, `terms`, `range`, `bool` with
`must` `should` `filter` `must_not`); aggregations (`terms`, `histogram`,
`stats`); `_search`, `_count`, `_mapping`, `GET /<index>/_doc/<id>`; how this
maps to SQL you know (`term` is `WHERE col = x`, `terms` aggregation is
`GROUP BY`). NOMAD's index is `nomad_oasis_entries_v1`.

Concepts, MongoDB: documents and collections; `mongosh`;
`db.collection.find(query, projection)`, `countDocuments`, `distinct`;
the aggregation pipeline (`$match $group $project $sort $limit $lookup`) and
how each stage maps to SQL; NOMAD's database is `nomad_oasis_v1`, collections
`upload` and `entry`.

Concepts, Temporal: workflows vs activities; durability and retries with
backoff; namespaces; why a failed upload can leave a workflow retrying
forever; the admin CLI to list and terminate a workflow, run through the
`temporal-create-namespace` service image.

Read: Elasticsearch "Query DSL" and "Aggregations"
(https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html).
MongoDB Shell docs and "Aggregation Pipeline"
(https://www.mongodb.com/docs/mongodb-shell/). Temporal "Temporal 101"
(https://learn.temporal.io/). The three cheat sheets
`cheatsheets/elasticsearch.md`, `mongodb.md`, `temporal.md`.

Lab: Lab 1 does the inspection; the challenge adds an aggregation query and a
workflow termination.

Checkpoint: write an Elasticsearch aggregation that counts entries by
`entry_type`, the equivalent MongoDB aggregation, and the SQL you would have
written for the same question.

## Module 8: Schemas, the NOMAD metainfo model

Concepts: sections and quantities; `base_sections` and inheritance;
quantity `type` (`str`, `np.float64`, `Datetime`, `MEnum`), `shape`, `unit`,
`description`; ELN annotations (`eln.component` widgets, `eln.hide`); the
single-file `.archive.yaml` with a `definitions:` block and a `data:` block;
why you iterate schemas as uploaded YAML (minutes, no rebuild) before promoting
them.

Why here: Phase 2. This is the core of NOMAD customization and the cheapest
rung of the ladder.

Read: `oasis-adoption-plan.md` "Phase 2" and its notes.
`cheatsheets/nomad-concepts.md` schema section.

Lab: Lab 2.

Checkpoint: write a five-quantity ELN schema from scratch with one enum and one
number-with-unit, upload it, and create an entry from it.

---

# Tier 3: extend and ship

Goal: turn a stable schema into a versioned Python plugin, give a data type its
own search app, and keep CI green.

## Module 9: Python plugin packaging and the build loop

Concepts: `pyproject.toml` (`[project]`, dependencies, optional-dependencies,
`[build-system]` with a backend like hatchling); the `src/` layout; entry
points, the `[project.entry-points.'nomad.plugin']` table, and how a host
program discovers them at runtime; `uv` (`uv lock`, `uv sync`, `uv run`),
`uv.lock` as an exact pinned set; running `uv` from a container when it is not
on the host; git tags (`git tag vX.Y.Z`, `git push --tags`) and semantic
versioning; pinning a dependency by
`git+https://host/repo.git@vX.Y.Z`; the full loop: edit plugin, tag, bump the
ref in this repo, `uv lock`, rebuild the image, `up -d`.

Why here: Phase 3. This is the step that made the schema versioned and shared,
and it is the slowest loop, so you want to do it deliberately.

Read: Python Packaging "Packaging Python projects"
(https://packaging.python.org/en/latest/tutorials/packaging-projects/) and the
"Entry points specification"
(https://packaging.python.org/en/latest/specifications/entry-points/). `uv`
docs (https://docs.astral.sh/uv/). `cheatsheets/uv-packaging.md`.

Lab: Lab 3.

Checkpoint: explain what an entry point is, where NOMAD reads it, and why the
distribution builder can only use installable packages and not a local path.

## Module 10: UI config, the `ui.apps` model

Concepts: `nomad.yaml` `ui.theme` and `ui.apps.options`; an app as a locked
query plus columns plus a filter menu plus a dashboard; `filters_locked` on
`section_defs.definition_qualified_name`; dynamic search quantities addressed as
`data.<name>#<section-qualified-name>`; validating a config against the pydantic
model in a scratch copy before applying it, so a bad file does not stop the
container from restarting; applying with
`docker compose up -d --no-deps --force-recreate app worker`.

Why here: Phase 4. Also teaches a habit: validate config out of band, then
recreate.

Read: `oasis-adoption-plan.md` "Phase 4" and its notes.
`cheatsheets/nomad-concepts.md` app section.

Lab: Lab 4, first half.

Checkpoint: add a second app that locks to a different schema, validate it
against the model without restarting the stack, then apply it.

## Module 11: nginx as a reverse proxy

Concepts: what a reverse proxy does; `server` and `location` blocks;
`location` match types (prefix, `=` exact, `~` regex) and their priority;
`proxy_pass`; `return 302` and `rewrite`; serving and overriding static files;
how this repo splits config into `nginx_http.conf` and an included
`nginx_base_conf`; why a broken `proxy_pass` to an unresolvable host makes nginx
fail at startup.

Why here: Phase 4 branding added an exact-match redirect and the NORTH block is
disabled here. You need to read and edit these blocks safely.

Read: nginx "Beginner's Guide"
(https://nginx.org/en/docs/beginners_guide.html) and the `location` docs.
`cheatsheets/nginx.md`.

Lab: Lab 4, second half.

Checkpoint: add a redirect from a made-up path to the app, test it with `curl`
without opening a browser, and explain why an `=` location was the right match
type.

## Module 12: CI/CD with GitHub Actions

Concepts: a workflow file, `on:` triggers (`push`, `pull_request`, `tags`,
`workflow_dispatch`), jobs, steps, `runs-on`, `needs`, `strategy.matrix`,
`env`, `if:` conditions and context (`github.ref_type`); the `GITHUB_TOKEN`,
`permissions:`, and the repo-level default workflow permission; publishing to
GHCR and why a push can be denied; the `gh` CLI (`gh run list`, `gh run view
--log-failed`, `gh run watch`, `gh run rerun --failed`).

Why here: the workflow was red for real reasons (a plugin with no tests, a
package-write permission). You fixed it by skipping the untested plugin and
gating the image push to version tags. You should be able to read that
workflow and the fix.

Read: GitHub "Understanding GitHub Actions"
(https://docs.github.com/en/actions). `cheatsheets/github-actions.md`. This
repo's `.github/workflows/docker-publish.yml` end to end.

Lab: Lab 5.

Checkpoint: given a failed run URL, find the failing step, read its log, name
the cause, and say whether the fix is a code change or a settings change.

---

# Tier 4: control the API and read the source

Goal: drive the whole system from `curl` as an authenticated user, and read the
app, worker, and parser code well enough to predict behavior and debug it
without adding print statements first.

## Module 13: The NOMAD API and Keycloak auth by hand

Concepts, FastAPI as NOMAD uses it: a path operation (one function bound to a
method and path); path vs query vs body parameters; Pydantic models as the
request and response schema, and the `422` you get when a body fails
validation; `Depends` for shared logic like auth; routers and path prefixes;
the interactive docs page and the raw `openapi.json` the server publishes.

Concepts, the NOMAD API surface: `GET /api/v1/info` (versions, plugins, and the
Keycloak `server_url`, `realm_name`, `client_id`); `POST /api/v1/entries/query`
with the NOMAD query language in the JSON body (`and` `or` `not`, ranges with
`gte`/`lte`, `owner` one of `public` `user` `all`, `pagination`, `required` to
pull only part of the archive); `GET /api/v1/entries/{entry_id}/archive`; the
`/api/v1/uploads` group (create, `PUT` a file, get processing status, publish,
delete); how the API sits over Mongo and Elasticsearch (Module 7).

Concepts, auth: OAuth2 and OIDC in one paragraph (resource owner, client,
authorization server, resource server); why this Oasis uses central
`nomad-lab.eu` Keycloak and needs no local identity service; the token
endpoint; getting an access token with `curl` (direct-access-grant password
flow if the client allows it, otherwise the browser code flow and lifting the
token from the GUI network tab); the `Authorization: Bearer <token>` header;
token expiry, the refresh token; decoding a JWT payload with base64url to read
`sub`, `preferred_username`, `exp`; how the same query returns nothing
anonymously and your unpublished entries once the token is attached with
`owner: user`.

Why here: Phase 5 and the hosting move need you to check system state without a
browser, and "full manual control" means the API is yours end to end. This is
also where FastAPI and Pydantic stop being words on a page.

Read: FastAPI tutorial, "First Steps" through "Request Body"
(https://fastapi.tiangolo.com/tutorial/). NOMAD docs, "Using the API"
(https://nomad-lab.eu/prod/v1/docs/), and the live `openapi.json` and docs page
on your own Oasis. Keycloak "Server Administration, OIDC" overview
(https://www.keycloak.org/documentation). `cheatsheets/nomad-api.md` and
`cheatsheets/keycloak-auth.md`.

Lab: Lab 6.

Checkpoint: from a cold stack, using only `curl`, get a bearer token, create an
upload, add a file, wait for it to process, query the entry by a custom
quantity, and fetch one section of its archive. Say what a `401`, a `403`, and
a `422` from the API each mean.

## Module 14: Async Python and reading the NOMAD source

Concepts, async: the event loop; `async def`, `await`, a coroutine;
concurrency vs parallelism; async helps IO-bound work and does nothing for
CPU-bound work; blocking the loop is a bug; how FastAPI runs a sync path
operation in a threadpool so it does not block; why parsing runs in the
`worker` (a Temporal activity), not in the `app` event loop.

Concepts, reading a codebase you did not write: find the installed package
inside the container
(`docker compose exec app python -c "import nomad, os;
print(os.path.dirname(nomad.__file__))"`); navigate with `grep -rn` and an
editor; follow imports inward from an entry point; the shape of the NOMAD tree,
`nomad/app/` (the FastAPI app and routers), `nomad/processing/` (the
processing workflow and activities), `nomad/parsing/parsers.py` (`match_parser`
and `MatchingParser`), `nomad/metainfo/` (the section and quantity machinery),
`nomad/config/` (the Pydantic settings models that `configs/nomad.yaml`
populates).

Concepts, the parser path: read `match_parser` against the "How NOMAD matches a
file to a parser" write-up in `oasis-adoption-plan.md` (the byte-header read,
libmagic MIME detection, the ordered `is_mainfile` checks, `level`,
`strict=True`); what a parser plugin must provide (`is_mainfile`,
`parse(mainfile, archive, logger)`, a `nomad.parser` entry point); read one
small real parser plugin top to bottom.

Why here: the next phase reads and may write parser code. You cannot honor "a
parser plugin only when a file format forces it" without being able to read
what one does.

Read: Real Python "Async IO in Python" (https://realpython.com/async-io-python/).
FastAPI "Concurrency and async / await" (https://fastapi.tiangolo.com/async/).
The NOMAD source paths above, in the running container. `cheatsheets/nomad-concepts.md`
parser section.

Lab: Lab 7.

Checkpoint: name the file and function where an uploaded file is matched to a
parser, the file where the entries query route is defined, and the Pydantic
model class that `configs/nomad.yaml`'s `ui.apps` block is validated against.
Explain why a slow parser does not freeze the API.

---

## Glossary

- **image**: a built, immutable filesystem plus metadata. A container is a
  running instance of one.
- **bind mount**: a host file or directory mapped into a container. Edits on
  the host are visible in the container, with an inode caveat covered in Lab 4.
- **named volume**: Docker-managed storage that outlives a container and is not
  a path in your project.
- **entry point (Python)**: a named object a package advertises in its
  metadata so other code can discover it without importing the package first.
- **mainfile**: the file in an upload that a parser claims. It becomes an
  entry.
- **archive (NOMAD)**: the typed, parsed representation of an entry, distinct
  from the raw uploaded files.
- **workflow (Temporal)**: a durable orchestration function. Its steps are
  activities. It survives worker restarts and retries failures.
- **lockfile**: a file pinning every dependency to an exact version and hash so
  a build is reproducible.
- **path operation (FastAPI)**: one Python function bound to an HTTP method and
  URL path. The unit a FastAPI app is built from.
- **bearer token**: a string in the `Authorization: Bearer ...` header that
  proves who you are. Whoever holds it can use it, so it is short-lived.
- **JWT**: a bearer token that is three base64url parts joined by dots. The
  middle part is a readable JSON payload with fields like `sub` and `exp`.
- **event loop**: the single thread that runs async code, switching between
  coroutines whenever one is waiting on IO.
- **coroutine**: a function defined with `async def`. It runs on the event loop
  and yields control at each `await`.

## Reading list, one link per tool

- HTTP: MDN HTTP guide, https://developer.mozilla.org/en-US/docs/Web/HTTP
- Shell and git: MIT Missing Semester, https://missing.csail.mit.edu/
- git in depth: Pro Git, https://git-scm.com/book
- Docker: https://docs.docker.com/get-started/
- Compose: https://docs.docker.com/compose/
- nginx: https://nginx.org/en/docs/beginners_guide.html
- GitHub Actions: https://docs.github.com/en/actions
- Python packaging: https://packaging.python.org/en/latest/tutorials/packaging-projects/
- uv: https://docs.astral.sh/uv/
- Elasticsearch: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html
- MongoDB shell: https://www.mongodb.com/docs/mongodb-shell/
- Temporal: https://learn.temporal.io/
- FastAPI: https://fastapi.tiangolo.com/tutorial/
- Async Python: https://realpython.com/async-io-python/
- Keycloak / OIDC: https://www.keycloak.org/documentation
- NOMAD: https://nomad-lab.eu/prod/v1/docs/

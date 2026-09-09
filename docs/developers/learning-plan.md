# Self-study plan

Reproduce Phases 0 to 4 of `docs/oasis-adoption-plan.md` by hand. Twelve
modules in three tiers. Each module lists the concepts, what to read, the lab
that exercises it, and a checkpoint you should be able to pass before moving
on.

Rough budget: 30 to 35 hours, concept reading plus labs, spread over two to
four weeks part time. Tier 1 is the largest lift if containers are new to you.

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

## Reading list, one link per tool

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
- NOMAD: https://nomad-lab.eu/prod/v1/docs/

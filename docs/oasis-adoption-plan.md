# NOMAD Oasis adoption plan

Working brief for moving from the Nexus demo to a real NOMAD Oasis for the RDM
cluster. Nexus stays as the five-minute conceptual on-ramp for the keynote; the
Oasis distribution is the production target. Copy this file into the new
distribution repo as its starting brief, alongside `nomad-oasis-mapping.md`.

## Goal

A NOMAD Oasis "distribution": a private git repo, created from
`nomad-distro-template`, that pins the base image, the installed plugins, the
config, and the compose files. All customization happens here as plugins and
`nomad.yaml`. NOMAD core is never forked or edited. Prefer YAML schemas,
configuration, and the built-in tabular parser over Python, until a real file
format forces a Python parser.

## Oasis as a plant: the components

Seven long-running containers in the minimal compose stack, plus two one-shot
Temporal init jobs. This was corrected after Phase 0: the current
`nomad-distro-template` uses Temporal (not RabbitMQ/Celery) for task
orchestration, and adds PostgreSQL as Temporal's backing store. See the Phase 0
implementation notes below.

| Service | Role | Talks to | How |
|---|---|---|---|
| app | control room: API, serves the GUI, auth | mongo, elastic, temporal | HTTP in, DB and Temporal out |
| worker | the reactors: parses uploads, runs normalizers | temporal (pulls activities), mongo, elastic (writes results) | Temporal RPC, DB |
| proxy (nginx) | front gate and piping manifold (port 80/443), TLS, large uploads | app | HTTP, WebSocket |
| temporal | job orchestrator: schedules and tracks processing workflows | postgresql, app enqueues, worker executes | gRPC 7233 |
| postgresql | Temporal's own state store (not NOMAD's metadata) | temporal | port 5432 |
| mongo | batch records: users, uploads, entry metadata, processing state | app, worker | port 27017 |
| elasticsearch | search index and instrument panel behind the Explore UI | app, worker | HTTP 9200 |
| temporal-setup-db, temporal-create-namespace | one-shot: create the Temporal DB schema and default namespace, then exit 0 | postgresql, temporal | run once at up |
| north (optional, off) | side lab: JupyterHub, launches tool containers | docker socket | Unix socket |
| logtransfer (optional, off) | ships logs out; behind the `with_logtransfer` profile | elastic, mongo | - |

No self-hosted Keycloak. Login goes through the public NOMAD Keycloak at
`nomad-lab.eu` via `oasis.uses_central_user_management: true`.

Data at rest: raw uploaded files and processed archive files both live in
`./.volumes/fs` (mounted at `/app/.volumes/fs` in the containers). Named Docker
volumes hold Mongo, Elasticsearch, and PostgreSQL state. `nomad.yaml` is the
single config file: hostname and base path, database and index names, active
plugins, the `ui:` section, and auth settings.

Flow: browser to nginx to app. app registers a processing workflow with
temporal; worker executes the workflow activities, parses the file, writes
structured results to mongo and elastic; the GUI reads them back through app.

Minimal deployment to start with: `docker compose up -d app worker proxy`.
Compose pulls in temporal, postgresql, mongo, elastic and the two temporal-*
init jobs through `depends_on`. north and logtransfer stay down.

## The infrastructure stack in one sentence

NOMAD is a FastAPI app with a React front end, that stores metadata in MongoDB,
indexes it in Elasticsearch for search, hands slow file processing to workers
orchestrated by Temporal (with PostgreSQL as Temporal's state store), keeps raw
and processed files on a disk volume, optionally authenticates through Keycloak
and runs analysis tools through JupyterHub, all wired together by Docker Compose
behind nginx.

## The modular seams: extension points

NOMAD is extended by adding plugins and editing `nomad.yaml`, never by editing
NOMAD source. Plugin entry-point types, in rough order of effort:

| Type | What it does | Effort |
|---|---|---|
| YAML schema uploaded as data | define the fields for a data type, get an ELN form | none, no rebuild |
| tabular parser (YAML annotations) | turn a CSV or Excel file into entries; column mode enriches one entry, row mode creates many | none |
| app entry point, or `ui.apps` in `nomad.yaml` | a focused search page: preset query, columns, trimmed filter menu, dashboard | low, config |
| schema package (Python plugin) | the same schema, versioned, tested, shared across labs | medium |
| parser plugin (Python) | read a lab's native or binary instrument format | high |
| normalizer, dashboard, NORTH tool, API | derived data, embedded mini-apps, in-browser tools, extra endpoints | varies |

Compatibility is protected by staying on this ladder: YAML schema and tabular
parser and app config before any Python; Python plugins live in the
distribution repo; the base image tag is bumped to upgrade and the plugins ride
along.

## How far UI customization goes

- Supported and easy: the `ui:` block in `nomad.yaml` plus app entry points. A
  custom app is a search page with a fixed query (for example, only one lab's
  schema), a chosen column set, a reduced filter menu, and a dashboard of
  widgets. One app can be the default landing view. Menu items can be hidden or
  reordered. This covers giving a lab a simple view of only its data.
- Medium: a dashboard plugin is a small web app of your own, rendered in an
  iframe inside NOMAD, inheriting its theme through CSS variables. Good for a
  bespoke report or chart page.
- Hard: changing the entry page layout, the upload flow, or the overall shell.
  That is the React and Material-UI single-page app. It would mean forking the
  GUI or building a separate frontend against the API. Not in scope for the
  conference timeline.

"Simplify the Oasis UI" means a custom default app plus `ui:` config, not a
blank-slate rewrite.

## What to keep for the cluster

Keep: the five core services, schema-driven entries, the search UI narrowed by
per-domain apps, YAML ELN forms for the spreadsheet and paper labs, the tabular
parser for CSV-export labs, central user management.

Defer: NORTH, self-hosted Keycloak, publishing to the central repository,
custom binary-format parsers (only when a specific lab needs one).

## Onboarding a new lab: schema first, instrument last

1. Model the data with the lab. Write one YAML ELN schema: `base_sections` from
   `nomad.datamodel.metainfo.eln`, quantities with types and units,
   `eln.component` widgets, `hide` for inherited fields that are not needed.
   Upload it as data so iteration takes minutes with no rebuild.
2. Cheap ingest. If the lab exports CSV or Excel, add `tabular_parser`
   annotations to a `data_file` quantity (column mode, or row mode for many
   entries). If the lab hand-enters, the ELN form is already the ingest path.
   No code either way.
3. Give the lab a view. Add an app with a preset filter to its schema, sensible
   columns, and a small dashboard. Make it the landing page.
4. Write a parser plugin only if forced, for a native or binary format. This is
   the instrument-integration step and the most work. Defer until one or two
   labs actually hit the wall.
5. Promote the stable YAML schema to a schema-package plugin in the
   distribution repo once it is shared, so it is versioned and tested.

eLab integration is a parallel track, not step 1. If a lab already lives in
elabFTW, NOMAD imports elabFTW exports (shown under "ElabFTW Project Import" on
the entry page). Use that where an ELN already exists. For paper and spreadsheet
labs, NOMAD's own ELN form is the faster win.

Short answer to "instruments or eLab first": neither. Start with the schema and
a cheap ingest path for one pilot lab. Parsers come when a format demands it.
eLab integration is per-lab, only where an ELN is already in use.

## Local first, and where data lives

Run the whole thing locally on the development machine for the prototyping
phase.

- Fastest iteration: no SSH, no network config, edit and `docker compose up` in
  one place.
- NOMAD stores raw and processed files in the bind-mounted `./.volumes/fs`
  directory in the distribution repo, plus named Docker volumes for Mongo,
  Elasticsearch, and PostgreSQL. All local.
- The existing EU-cloud VM is serving the live keynote demo. Adding
  Elasticsearch, MongoDB, and the NOMAD app and worker to it risks running that
  demo out of memory before the conference.
- "Closer to the real case" is a dedicated persistent server, which the demo VM
  is not. When persistence is wanted, deploy the same distribution repo to a
  separate cloud VM, not the demo one.

Resource note: give the VirtualBox VM at least 8 GB RAM. Elasticsearch is the
hungry one.

## Phase 0 implementation notes (2026-09-08)

What the plan assumed vs. what the current `nomad-distro-template` actually
ships. Recorded here so later phases start from reality.

1. **Task orchestration is Temporal, not RabbitMQ/Celery.** No `rabbitmq`
   service exists. The worker runs
   `python -m nomad.cli admin run action-internal-worker`; services talk to
   `temporal` over gRPC 7233.
2. **PostgreSQL is required** as Temporal's state store. Two one-shot jobs
   (`temporal-setup-db`, `temporal-create-namespace`) create its schema and
   namespace, then exit 0. This is separate from NOMAD's own metadata store,
   which is still MongoDB.
3. **Minimal set is seven containers**, not five:
   `elastic mongo postgresql temporal worker app proxy`. Start with
   `docker compose up -d app worker proxy`; the rest come in through
   `depends_on`. `north` and `logtransfer` stay down because nothing we start
   depends on them.
4. **`.env` is generated, not committed.** `bash scripts/generate-env.sh`
   writes `.env` and `.env.north` (both gitignored). Run before first up.
5. **The image is built, not `docker compose build`.** The template has no
   `build:` key; `app`/`worker` use a prebuilt `image:` that CI publishes to
   GHCR. For local-only, build it directly and tag it as compose expects:
   `docker build --target final --build-arg UV_VERSION=0.9 -t
   ghcr.io/cates-tum/nomad-oasis-econversion:main .`
6. **`initialize.yml` runs after repo creation.** Cloning immediately gets you
   the pre-render commit (`{{ repository }}` placeholders, upstream image
   names). Wait for the "Repository initialization" commit and pull it, or you
   pull the wrong reference image. Dependabot also opens ~7 PRs on day one with
   failing CI until the first image is published.
7. **mongo 8.0 will not start on this VM.** Kernel is `7.0.0`; MongoDB 8.0
   aborts on kernels 6.19 through 7.0.13 (SERVER-121912). Pinned `mongo:7.0`.
   Revert to 8.0 once the VM kernel reaches >= 7.0.14.
8. **Keeping the nginx proxy needs two edits, because proxy hard-depends on
   NORTH.** Removed `north` from `proxy.depends_on`, and commented out the
   `location /nomad-oasis/north/` block in `configs/nginx_base_conf` (a static
   `proxy_pass` to an unresolvable host makes nginx fail at startup).
9. **`nomad.yaml` is baked into the image at build.** The compose bind-mount
   for live edits was commented out; it is now uncommented on `app` and
   `worker`, so config changes need only `docker compose restart`, not a
   rebuild.
10. **Resources after bring-up:** ~5.7 GiB RAM in use on a 10 GiB VM (fits, but
    tight under processing load); build + images cost ~16 GiB disk, leaving
    ~12 GiB free. Watch both in Phase 1.
11. **Version running:** NOMAD 1.4.3, `oasis: true`. Shipped parsers include
    `tabular`; three example uploads are available (Tabular Data, Tailored RDM,
    Data Management Framework Tutorial).
12. **`temporal-create-namespace` was not in the dependency chain** (found at
    the start of Phase 1, 2026-09-09). `docker compose up -d app worker proxy`
    started `temporal` and `temporal-setup-db` but never the namespace job, so
    the `default` Temporal namespace did not exist. The GUI and login worked,
    but any Temporal workflow (upload processing, upload delete) failed with
    `Namespace default is not found` and a 500. Fix: added
    `temporal-create-namespace: condition: service_completed_successfully` to
    the `depends_on` of both `app` and `worker`, so any `up` that starts them
    also runs the namespace job first. The job is idempotent across `down`/`up`.

Config trims applied in `configs/nomad.yaml`: `north.enabled: false`, removed
the NORTH-jupyter plugin entry point, set `meta.deployment_url` /
`meta.maintainer_email` to local values. Kept
`oasis.uses_central_user_management: true` and `temporal.enabled: true`.

## Phase 1 implementation notes (2026-09-09)

1. **Shipped example uploads do not work in this image.** The entry points are
   registered (they show under `plugin_entry_points` in `/api/v1/info`) but
   their resource files are not bundled, so processing fails with
   `AssertionError: Upload resource path "tabular/*" ... could not be found`.
   We build our own instead, under `examples/` in this repo.
2. **A failed or deleted upload can leave a Temporal workflow retrying** with
   backoff, forever, logging a traceback each time (later `KeyError: Upload
   with id ... does not exist` once the upload is gone). Terminate it:
   `docker compose run --rm --no-deps --entrypoint temporal
   temporal-create-namespace workflow terminate --address temporal:7233
   -n default --workflow-id <id> --reason <text>`. The `temporal` CLI is only
   in the `temporalio/admin-tools` image, which the `temporal-create-namespace`
   service already uses. A plain `docker run` of that image is blocked by the
   sandbox; going through the compose service works.
3. **Tabular column mode: `Datetime` array columns fail** with `ValueError:
   Shape mismatch`. Use `type: str` for date columns parsed from a table.
   The other seven columns (str and `np.float64` with units) parsed fine.
4. **Single-file schema plus data works well.** One `.archive.yaml` with a
   `definitions:` block and a `data:` block (`m_def: <LocalSectionName>`,
   `data_file: <csv>`), uploaded together with the CSV, auto-creates one entry
   and runs the tabular parser. No "create entry from schema" click needed.
   Base sections: `nomad.datamodel.data.EntryData` and
   `nomad.parsing.tabular.TableData`.
5. **Column mode result:** `mapping_mode: column`, `file_mode: current_entry`,
   `sections: ['#root']` produced one entry of type `GrillSessions` with each
   CSV column as a length-12 array quantity. Confirmed in the processed
   archive and in the `nomad_oasis_entries_v1` Elasticsearch index
   (`published: false`).
6. **To investigate:** the ES entries index held 17 docs while MongoDB had 1
   entry. Likely orphaned search docs from the deleted failed uploads. Check
   whether upload delete fully cleans Elasticsearch.

## Phased task list

### Phase 0: setup  [done 2026-09-08]
- [x] Confirm Docker and Compose; VM has 10 GB RAM, ~28 GB free disk before build
- [x] Create the repo from `nomad-distro-template`; push to a new private GitHub repo
- [x] Reduce to the seven-container minimal set (Temporal + Postgres, no
  RabbitMQ); central user management; no NORTH
- [x] `docker compose up`; reach the GUI at `http://localhost/nomad-oasis/gui/`;
  logged in with a central NOMAD account
- [x] Commit the working baseline (`15a439b`, not pushed)

### Phase 1: data in via shipped parsers  [done 2026-09-09]
- [x] Shipped example uploads do not work here (data files not bundled). Built
  our own: `examples/grill-sessions/` (CSV + single-file schema/data
  archive.yaml), tabular parser, column mode.
- [x] Uploaded through the GUI; watched the worker process it into one entry
  of type `GrillSessions`.
- [x] Inspected the entry: raw files (the .yaml and .csv) vs archive (the
  metainfo tree with 8 filled array quantities); confirmed indexed in
  `nomad_oasis_entries_v1` (`published: false`).
- [x] Explore lists the entry; filter chips map to indexed fields.
- [x] Findings recorded above and in memory.

### Phase 2: a custom type as a YAML ELN schema  [done 2026-09-09]
- [x] Pilot type: the Nexus grill attempt, collapsed from `grill_red_meat` /
  `grill_poultry` / `grill_fish` + `base_recipe_attempt` into one section.
- [x] `examples/grill-attempt/grill_attempt.archive.yaml`: section
  `GrillAttempt` on `nomad.datamodel.metainfo.eln.ELNMeasurement` +
  `EntryData`, 13 quantities with `eln` component widgets, `eln.hide` for
  inherited `lab_id` / `location` / `method` / `tags` and the `steps` /
  `samples` / `instruments` / `measurement_identifiers` sub-sections.
- [x] Uploaded the schema; created an entry with **Create from schema** (the
  GUI button is not "Create entry"); generated form renders, enums as
  dropdowns, hidden fields gone. Verified the saved archive.
- [x] Column mode already covered in Phase 1 (`grill-sessions`, arrays on one
  entry). Row mode: `examples/grill-attempt/grill_attempt_table.archive.yaml`
  (`GrillAttemptRow`, `mapping_mode: row`, `file_mode: multiple_new_entries`)
  plus the CSV -> 12 entries, scalars, named by `session_id`.
- [x] Iterated: `date` stays `str` (Phase 1 finding), schemas load clean.

Phase 2 notes:
- `eln.hide` at section level hides both inherited quantities and inherited
  sub-sections.
- Enum quantity syntax: `type: {type_kind: Enum, type_data: [...]}`.
  `EnumEditQuantity` renders as a dropdown; `RadioEnumEditQuantity` also
  rendered as a dropdown in 1.4.3.
- Uploaded schemas are visible across all uploads, so the Create-from-schema
  picker lists every section you have ever uploaded. Easy to pick the wrong
  one; check the source file name.
- Row mode: the **first CSV row fills the trigger entry itself**; rows 2..N
  become new entries (`<label>_<idx>.<Section>.archive.yaml`). N rows -> N
  entries total.

### Phase 3: promote the type to a schema-package plugin
- Scaffold a plugin package: `src/<pkg>/schema_packages/`, `pyproject.toml` with
  the `nomad.plugin` entry point
- Move the stable schema from YAML into Python `SchemaPackage` and `Section`
  classes
- Register the plugin in the distribution; rebuild the custom image
- Recreate the entry from the packaged schema; confirm it matches the YAML
  version
- Commit; tag a version

### Phase 4: a custom app for the new type
- Add an app entry point, or `ui.apps` in `nomad.yaml`: preset query filtered to
  the new schema, chosen columns, a trimmed filter menu, one dashboard widget
- Make it a menu item; consider it as the landing view
- Check it against a handful of entries
- Commit

### Phase 5: capture what you learned
- `CLAUDE.md` for the repo: how the distribution is laid out, how to add a
  plugin, how to rebuild the image
- Memory notes: the plugin entry-point mechanism, YAML schema versus schema
  package tradeoffs, how NOMAD matches a file to a parser, where data physically
  sits locally
- Update this plan with what actually happened versus what was planned
- Note the eventual hosting move (same distribution repo, separate cloud VM),
  not done now

## How the Nexus concepts carry over

| Nexus | NOMAD Oasis |
|---|---|
| `schemas/*.yaml` | YAML ELN schemas, then schema-package plugins |
| the `extends:` key | `base_sections` |
| `GET /schemas` plus generic `render.py` | the schema-driven GUI plus apps |
| e-kitchen pushing entries via `POST /entries` | a parser, or an external uploader hitting the API |
| the filter chips derived from fields | Elasticsearch facets configured in an app |
| the `/analysis` inline-SVG charts | dashboard widgets, or a dashboard plugin |

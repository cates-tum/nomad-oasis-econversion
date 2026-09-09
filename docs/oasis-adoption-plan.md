# NOMAD Oasis adoption plan

Living record of moving from the Nexus demo to a real NOMAD Oasis for the RDM
cluster. Nexus stays as the five-minute conceptual on-ramp for the keynote; the
Oasis distribution is the production target. This file lives in the distribution
repo (`docs/`) alongside `nomad-oasis-mapping.md` and is updated per phase with
what actually happened. `docs/developers/` turns this record into a self-study
path: a learning plan, hands-on labs per phase, and per-tool cheat sheets.

## Goal

A NOMAD Oasis "distribution": a private git repo, created from
`FAIRmat-NFDI/nomad-distro-template`, that pins the base image, the installed
plugins, the config, and the compose files. All customization happens through
plugins and `nomad.yaml`. NOMAD core is never forked or edited.

Schema strategy: prototype every schema as YAML (uploaded as data, no rebuild),
and promote it to a Python schema-package plugin once it is stable and shared,
for versioning and reuse. Write a Python *parser* plugin only when a real file
format forces it. Prefer `nomad.yaml` config and the built-in tabular parser
over Python everywhere else.

## Decisions made

| Decision | Choice | Rationale |
|---|---|---|
| Task orchestration | Temporal + PostgreSQL (as shipped by the template) | Not a choice, the template moved off RabbitMQ/Celery. See Phase 0 notes. |
| User management | Central NOMAD Keycloak (`uses_central_user_management: true`) | No working self-hosted Keycloak in the template; central works offline-local. |
| MongoDB version | Pinned `mongo:7.0` | 8.0 aborts on this VM kernel 7.0.0 (SERVER-121912). Revert at kernel >= 7.0.14. |
| Minimal service set | `elastic mongo postgresql temporal worker app proxy` + 2 temporal init jobs | NORTH and logtransfer off; nothing we run depends on them. |
| Custom image | Built locally with `docker build --target final`, tagged as the compose `image:` | Template has no `build:` key; CI publishes to GHCR, local build avoids a PAT. |
| Plugin repo structure | **One shared plugin repo** `cates-tum/nomad-econversion-plugins` (public), one `nomad.plugin` entry point per schema/parser | Split a plugin out only when it needs an external maintainer, a divergent release cadence, or has grown large. Extraction later is a `git filter-repo`, not a rewrite. FAIRmat splits by domain/team, not by section. |
| Plugin pinning | `git+https://...@vX.Y.Z` tag in the distro `pyproject.toml`, `uv lock` to pin the commit | Reproducible; public repo needs no build credentials. |
| Config edits | `configs/nomad.yaml` bind-mounted into `app`/`worker` for `docker compose restart` iteration | Baked into the image at build otherwise. |

## Current state (end of Phase 4, 2026-09-09)

- Distro repo `cates-tum/nomad-oasis-econversion` (private), at tag `v0.1.0`.
  Local image `ghcr.io/cates-tum/nomad-oasis-econversion:main` built with the
  plugin. Stack runs locally; GUI at `http://localhost/nomad-oasis/gui/`,
  central login working.
- Plugin repo `cates-tum/nomad-econversion-plugins` (public), tag `v0.1.0`
  (`dcb6e210`). One entry point: `grill_attempt` -> `GrillAttempt` schema.
- `examples/` holds the YAML prototypes: `grill-sessions/` (tabular column
  mode) and `grill-attempt/` (ELN form + row-mode tabular, plus `app-test/`
  four data-only archives of the packaged schema, the Phase 4 fixture).
- Phase 4 done: custom app `grill_attempts` in `configs/nomad.yaml`
  (`ui.apps.options`), config only, no rebuild. Locked to the packaged schema,
  seven columns, four filter-menu items, one dashboard widget. Verified in the
  GUI against five entries.
- Phases 0-4 done. Phase 5 (capture) is the running record; parser-matching
  and hosting-move write-ups now in the Phase 5 section, hosting not executed.
- Resolved: the ES-vs-Mongo count mismatch (Phase 1 open item). Both now hold
  16 docs. No orphaned search docs found; upload delete cleaned up as expected.

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
parser and app config before any Python. Python plugins live in the shared
plugin repo (`nomad-econversion-plugins`), not in NOMAD core and not inline in
the distribution; the distribution pins each by git tag in `pyproject.toml`.
The base image tag is bumped to upgrade and the plugins ride along.

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

Keep: the seven core services (`elastic mongo postgresql temporal worker app
proxy`), schema-driven entries, the search UI narrowed by per-domain apps, YAML
ELN forms for the spreadsheet and paper labs, the tabular parser for CSV-export
labs, central user management.

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
5. Promote the stable YAML schema to a Python schema-package plugin in the
   shared plugin repo (`nomad-econversion-plugins`) once it is shared, so it is
   versioned and tested. Pin it in the distribution `pyproject.toml` by tag and
   rebuild the image. See Phase 3 notes for the loop.

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

Resource note (measured in Phase 0): 10 GiB VM RAM is the practical floor, not
8. The stack uses ~5.7 GiB idle on this VM and is tight under processing load.
Build plus images cost ~16 GiB disk. Elasticsearch is the hungry one; its heap
is already capped at 512 MiB in `docker-compose.yaml`.

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

### Phase 3: promote the type to a schema-package plugin  [done 2026-09-09]
- [x] One shared plugin repo `cates-tum/nomad-econversion-plugins` (public),
  hand-written, ~6 files. `src/nomad_econversion_plugins/schema_packages/`
  with `grill.py` (`m_package` + `GrillAttempt` class) and `__init__.py`
  (`SchemaPackageEntryPoint`). `pyproject.toml`
  `[project.entry-points.'nomad.plugin'] grill_attempt = ...`. Tagged `v0.1.0`.
- [x] Ported all 13 quantities from `grill_attempt.archive.yaml` to Python:
  `class GrillAttempt(ELNMeasurement, EntryData)`,
  `m_def = Section(a_eln=ELNAnnotation(hide=[...]))`, `Quantity(type=MEnum(...),
  a_eln=ELNAnnotation(component=ELNComponentEnum...))`, `unit=` /
  `defaultDisplayUnit=`. `m_package.__init_metainfo__()` at the end.
- [x] Distro `pyproject.toml` plugins extra:
  `nomad-econversion-plugins @ git+https://github.com/cates-tum/nomad-econversion-plugins.git@v0.1.0`.
  `uv lock` (via `ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim`, uv is not
  on the host) pinned it at commit `dcb6e210`. Rebuilt the image.
- [x] `docker compose up -d`. `api/v1/info` shows `plugin_packages`
  `nomad_econversion_plugins 0.1.0` and a `schema_package` entry point.
- [x] Created an entry from the packaged schema in the GUI. Its `data` block
  matches the Phase 2 YAML entry field-for-field; only `m_def` differs:
  `nomad_econversion_plugins.schema_packages.grill.GrillAttempt` (stable
  package ref) instead of a per-upload file path.

Phase 3 notes:
- The distro Dockerfile builder runs `uv sync --extra plugins` with only
  `pyproject.toml` / `uv.lock` / `.git` mounted (Dockerfile:83-87). A plugin
  must be an installable package (PyPI or git URL), never a local path, unless
  the Dockerfile is changed. Public `git+https@tag` needs no build credentials.
- `uv.lock` must be regenerated locally before a local build; `uv sync` fails
  on a stale lock. The CI `update-lockfile` job also does this on push.
- Iteration loop is slower than YAML: edit `grill.py` -> tag `v0.1.N` in the
  plugin repo -> bump the `@v0.1.N` ref in the distro -> `uv lock` -> rebuild
  -> `up`. So prototype a schema in YAML, promote to the package when stable.
- Repo policy: one shared plugin repo, one entry point per schema/parser.
  Split a plugin into its own repo only when it needs an external maintainer,
  a divergent release cadence, or has grown large.

### Phase 4: a custom app for the new type  [done 2026-09-09]
- [x] `ui.apps.options.grill_attempts` in `configs/nomad.yaml` (config only, no
  rebuild). `filters_locked` on
  `section_defs.definition_qualified_name = nomad_econversion_plugins.schema_packages.grill.GrillAttempt`.
  Seven result columns (entry_name plus six `data.*#...` schema quantities),
  a four-item filter menu (protein_class / heat_source / outcome terms plus a
  grill_temp histogram), one dashboard terms widget on `outcome`.
- [x] Appears in the explore menu under category "Use Cases" next to the stock
  apps. `ui.apps` has no default-app key in 1.4.3, so it is made the landing
  view with an nginx redirect instead (see the branding note below).
- [x] Fixture: `examples/grill-attempt/app-test/`, four data-only
  `.archive.yaml` entries of the packaged schema, uploaded through the GUI, all
  `SUCCESS`. Checked the app against those four plus the Phase 3 packaged entry
  (five total).
- [x] Commit.

Phase 4 notes:
- **Custom schema quantities are searchable with no `a_elasticsearch`
  annotation.** NOMAD 1.4.3 indexes them as dynamic `search_quantities` with id
  `data.<name>#<section-qualified-name>`. App columns, menu items and widgets
  reference that full id string. For a promoted schema the qualifier is the
  stable class path; for a per-upload YAML schema it is
  `entry_id:<id>.<Section>`, so only promoted schemas get stable app config.
  This is the concrete payoff of Phase 3.
- **`filters_locked` on `section_defs.definition_qualified_name`** scopes the
  app to the packaged schema exactly. It matched the five packaged entries and
  excluded the Phase 2 YAML `GrillAttempt` entry, as intended.
- **`ui.apps.options` is additive.** The stock apps (Entries, Calculations,
  ELN) are `AppEntryPoint` plugin entry points served by
  `GET /api/v1/apps/entry-points`; the GUI merges them with `ui.apps.options`
  from `env.js`. `config.ui.apps.options` only ever holds the yaml-defined
  apps, so nothing stock is lost by defining one.
- **Menu histogram item uses `x: <search_quantity>`**, not `search_quantity:`
  (that key is rejected on `MenuItemHistogram`). Terms menu items and dashboard
  widgets use `search_quantity:`. A dashboard widget needs a `layout:` block
  with an entry per breakpoint (`sm md lg xl xxl`), each `{h, w, x, y}`.
- **Single-file bind mount goes stale on edit.** `configs/nomad.yaml` is
  bind-mounted at `/app/nomad.yaml`. An editor save (VS Code, or a tool) writes
  a new file and renames it over the old one, so the inode changes; Docker
  keeps the container pointed at the old inode. `docker compose restart app
  worker` restarts the process in the same container and still reads the old
  file. Reliable form:
  `docker compose up -d --no-deps --force-recreate app worker` (~30 s API
  downtime). Validate the yaml first, e.g.
  `docker compose cp configs/nomad.yaml app:/tmp/new.yaml` then a
  `nomad.config.models.ui.UI(**yaml.safe_load(...)['ui'])` check, so a bad
  config does not stop the container from coming back. CLAUDE.md updated.
- Grill temp / internal temp columns display in celsius as entered (180-260
  range), no unit misread.

Phase 4 branding (2026-09-09), GUI identity as "eConversion Nexus":
- **Only three things are config-adjustable.** `ui.theme.title` (browser tab
  name) is the single branding string in the 1.4.3 config model. The landing
  page is hardcoded to the About page; skipped with an nginx `location = ...`
  exact-match 302 from `/nomad-oasis/gui/` to
  `/nomad-oasis/gui/search/grill-attempts` (exact match, so deeper routes and
  assets fall through). The About page body text is compiled into hashed JS
  chunks, not changed without forking the GUI, out of scope.
- **Logos are plain files, swappable without a rebuild.** `nomad-text.png`
  (loading screen), `nomad-oasis.png` (About page), `nomad.png` (nav bar),
  `favicon.png` / `favicon-hres.png` / `favicon.ico`. On `app` start,
  `nomad.cli admin run app --with-gui` does `rmtree` + `copytree` of
  `.../site-packages/nomad/app/static/gui` into `run/gui_configured` and only
  string-substitutes the base path. So bind mounts must sit on the **source**
  path (`.../static/gui/<file>`), not the served copy; they then survive every
  restart. Six `:ro` mounts added to the `app` service.
  `scripts/make-branding.py` regenerates the placeholder text marks into
  `configs/branding/`.
- **The GUI service worker caches assets hard.** After a logo or favicon
  change, a normal reload keeps the old image. Unregister the service worker
  (Firefox: `about:debugging` > This Firefox > Service Workers) and clear the
  site data, or just use a private window.

CI fixes (2026-09-09), `.github/workflows/docker-publish.yml` was red since the
Phase 3 pushes:
- **Plugin unit tests failed with `No module named pytest`.** The
  `nomad-plugin-tests` step clones each installed plugin repo, builds a venv,
  and runs `pytest` on it. `nomad-econversion-plugins` ships no pytest suite
  and no tests, so it errored. Fix: added `nomad_econversion_plugins` to
  `PLUGIN_TESTS_PLUGINS_TO_SKIP`. Remove it once the plugin repo has real
  tests.
- **Docker push to GHCR failed with `permission_denied: read_package`.** The
  repo's `default_workflow_permissions` is `read`, so `GITHUB_TOKEN` cannot
  write packages. Fix (chosen): build the image on every branch push but
  `push: ${{ github.ref_type == 'tag' }}`, and gate the `run_tests` job (which
  pulls the pushed image) on `github.ref_type == 'tag'`. CI no longer needs
  package write for day-to-day work; the image is built locally by hand during
  prototyping anyway. Before the first `vX.Y.Z` tag for a hosting move, grant
  CI package write: repo Settings > Actions > General > Workflow permissions >
  Read and write. The image boot / health test now runs only at tag time.

### Phase 5: capture what you learned
- [x] `CLAUDE.md` for the repo: layout, how to add a plugin, how to rebuild the
  image. Written in Phase 0, current.
- [x] Memory notes: `oasis-adoption-project`, `what-processed-means`,
  `plugin-mechanism`. Cover the plugin entry-point mechanism, YAML vs
  schema-package tradeoffs, where data sits locally.
- [~] Update this plan per phase with what actually happened. Ongoing; this
  consolidation pass done 2026-09-09.
- [x] How NOMAD matches a file to a parser: written up below.
- [x] Hosting move: written up below. Not executed, this is the plan for it.

#### How NOMAD matches a file to a parser

On upload, NOMAD walks every file and calls `match_parser(path)`
(`nomad/parsing/parsers.py`) on each. A file that matches becomes a *mainfile*
and produces one entry (or several child entries); a file that matches nothing
stays a raw file with no entry.

`match_parser`:
1. Skip names starting with `.` or `~`.
2. Read the first 3 bytes for gzip/bz2/xz detection, then read the first
   `config.process.parser_matching_size` bytes (12000 here) of the
   decompressed head into a buffer.
3. Detect the MIME type of that buffer with libmagic. Try to decode it as
   UTF-8 for regex checks; if binary, guess the encoding.
4. Try each enabled parser in list order, return the first whose
   `is_mainfile(...)` passes.

A `MatchingParser` passes when every configured check passes (unset checks are
skipped):
- `mainfile_binary_header` / `_re`: literal bytes or a byte regex present in
  the head.
- `mainfile_contents_re`: regex found in the decoded text head.
- `mainfile_mime_re`: matches the detected MIME type (default `text/.*`).
- `supported_compressions`: a compressed file matches only if the parser lists
  its scheme.
- `mainfile_name_re`: fullmatch on the filename (default `.*`).
  `mainfile_alternative: true` lets a file match through a sibling with the
  same basename.
- `mainfile_contents_dict`: structural match into JSON / HDF5 / CSV / Excel /
  NetCDF content (`__has_key`, `__has_all_keys`, `__has_only_keys`, or value
  equality).

`level` orders parsers, lower first (`parsers/archive` is `level -1`). Normal
processing runs `strict=True`, which skips the artificial empty / missing
parsers.

This image installs `nomad-lab` core, one schema-package plugin, and no parser
plugins, so only three parsers are active:

| Parser | `level` | Filename regex | MIME |
|---|---|---|---|
| `parsers/tabular` | 0 | `.*\.archive\.(csv\|xlsx?)$` | `text/.*` or `application/.*` |
| `parsers/archive` | -1 | `.*(archive\|metainfo)\.(json\|yaml\|yml)$` | `.*` |
| `parsers/broken` | 0 | catch-all | fallback when a file raises during matching |

So in Phases 1 to 4 every entry came from `parsers/archive` matching the
`*.archive.yaml` mainfile by name. The `tabular_parser` annotations inside
those archives are executed by the archive parser, not by `parsers/tabular`
(that one is for a bare `*.archive.csv` uploaded on its own). A real instrument
format (`.out`, `.h5`, a vendor binary) yields no entry until a parser plugin
that matches it is pinned in `pyproject.toml` and the image is rebuilt. That is
the "parser plugin only if forced" path in "Onboarding a new lab".

#### Hosting move

Target: run the same distribution repo on a dedicated persistent VM, not the EU
cloud VM that serves the live keynote demo. Adding Elasticsearch, MongoDB, app,
and worker to the demo VM risks running that demo out of memory.

Carries over unchanged:
- The repo is the deployment. `git pull` on the server, then
  `docker compose up -d app worker proxy`. No per-host code.
- Central Keycloak (`uses_central_user_management: true`) already needs no
  local identity service, so there is no auth setup on the new host.
- All customization stays in `configs/nomad.yaml`, `configs/nginx_base_conf`,
  `configs/branding/`, and the pinned plugin tags, all bind-mounted.
  `docker compose up -d --no-deps --force-recreate app worker` applies a config
  change with no rebuild.

Changes for a real host:
- Image source. Either keep building locally or let CI publish. CI push to GHCR
  is gated to `vX.Y.Z` tags and needs package write granted once (repo
  Settings > Actions > General > Workflow permissions > Read and write, see the
  CI note above). The server then does `docker compose pull` instead of a local
  build.
- `services.api_host` and `services.api_base_path` in `nomad.yaml`, and
  `server_name` in `configs/nginx_http.conf`, move from `localhost` to the real
  hostname.
- TLS. The template ships `configs/nginx_https.conf` and commented cert mounts
  in `docker-compose.yaml`. Point the proxy at the HTTPS conf and mount real
  certs (Let's Encrypt or the cluster CA).
- `mongo` is pinned to `7.0` only for this VM's kernel (SERVER-121912). A host
  on kernel >= 7.0.14 can move back to `mongo:8.0`.
- Data is in `./.volumes/fs` (bind mount, uid 1000) plus named Docker volumes
  for Mongo, Elasticsearch, PostgreSQL. Back these up; on a server put
  `.volumes/fs` on a real data mount, not the repo checkout.
- Resources: the stack idles near 5.7 GiB RAM and is tight under load on
  10 GiB. Size the host above that and raise the Elasticsearch heap (capped at
  512 MiB in `docker-compose.yaml`) if there is room.
- NORTH and logtransfer stay off. Turn NORTH on only if a lab needs in-browser
  tools: uncomment the NORTH block in `configs/nginx_base_conf` and set
  `north.enabled: true`.

## How the Nexus concepts carry over

| Nexus | NOMAD Oasis |
|---|---|
| `schemas/*.yaml` | YAML ELN schemas, then schema-package plugins |
| the `extends:` key | `base_sections` |
| `GET /schemas` plus generic `render.py` | the schema-driven GUI plus apps |
| e-kitchen pushing entries via `POST /entries` | a parser, or an external uploader hitting the API |
| the filter chips derived from fields | Elasticsearch facets configured in an app |
| the `/analysis` inline-SVG charts | dashboard widgets, or a dashboard plugin |

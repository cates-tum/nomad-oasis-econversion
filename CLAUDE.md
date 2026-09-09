# nomad-oasis-econversion

A NOMAD Oasis **distribution** (from `FAIRmat-NFDI/nomad-distro-template`) for
the RDM cluster, run locally via Docker Compose during the prototyping phase.
NOMAD core is never forked. Prototype schemas as YAML (`configs/nomad.yaml` +
uploaded `.archive.yaml`, no rebuild), promote stable ones to Python
schema-package plugins in the shared plugin repo. Python *parser* plugins only
when a file format forces it.

Companion repo: `cates-tum/nomad-econversion-plugins` (public) holds the Python
schema/parser plugins, one `nomad.plugin` entry point each. This distro pins
each by git tag in `pyproject.toml`.

## Layout

- `configs/nomad.yaml` single config file: hostname, base path, DB and index
  names, active plugins, `ui:`, auth. Baked into the image at build; also
  bind-mounted in compose (`app` and `worker`) so edits apply with
  `docker compose up -d --no-deps --force-recreate app worker`, no rebuild. A
  plain `restart` is not enough: an editor save swaps the file inode and the
  container keeps the old one (Phase 4 note).
- `configs/nginx_base_conf` shared nginx location blocks. The
  `/nomad-oasis/north/` block is commented out (NORTH is off).
- `docker-compose.yaml` the stack. Long-running services we run locally:
  `elastic mongo postgresql temporal worker app proxy`, plus one-shot
  `temporal-setup-db` and `temporal-create-namespace`. `north` and
  `logtransfer` exist but stay down.
- `Dockerfile` builds `ghcr.io/cates-tum/nomad-oasis-econversion:main` from
  `python:3.12-slim` + `uv sync --extra plugins` (installs `nomad-lab` and the
  plugins listed in `pyproject.toml`), plus a built copy of the NOMAD docs. The
  builder mounts only `pyproject.toml`, `uv.lock`, `.git`, so plugins must be
  installable packages (PyPI or `git+https`), never local paths.
- `pyproject.toml` `[project.optional-dependencies].plugins` is the plugin
  list. `uv.lock` pins their exact commits; regenerate with
  `docker run --rm -v "$PWD":/w -w /w ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim uv lock`.
- `docs/` the adoption plan (living record) and the Nexus concept mapping.
- `examples/` YAML schema prototypes: `grill-sessions/` (tabular column mode),
  `grill-attempt/` (ELN form + row-mode tabular). Prototype here before
  promoting to the plugin repo.
- `.volumes/fs` raw and processed files at rest (bind mount, owned by uid
  1000). Mongo, Elasticsearch, PostgreSQL keep named Docker volumes.
- `scripts/generate-env.sh` writes `.env` and `.env.north` (both gitignored).
- `.github/workflows/docker-publish.yml` CI builds and pushes the image to
  GHCR on push to `main`.

## Task orchestration

Temporal, not RabbitMQ/Celery. PostgreSQL is Temporal's own state store, not
NOMAD's metadata store (that is MongoDB). Search index is Elasticsearch. The
worker runs `nomad.cli admin run action-internal-worker` and executes Temporal
workflow activities.

## Run locally

```
bash scripts/generate-env.sh                 # once, creates .env and .env.north

# build the image (CI does this on push; for local-only do it by hand)
docker build --target final \
  --build-arg UV_VERSION=0.9 \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg NOMAD_DOCS_REPO=https://github.com/FAIRmat-NFDI/nomad-docs.git \
  --build-arg JUPYTER_VERSION=2025-04-14 \
  -t ghcr.io/cates-tum/nomad-oasis-econversion:main .

docker compose up -d app worker proxy        # deps start via depends_on
docker compose ps
docker compose logs -f app
```

GUI: `http://localhost/nomad-oasis/gui/`. Health: `curl localhost/nomad-oasis/alive`.
Login goes through the central `nomad-lab.eu` Keycloak
(`oasis.uses_central_user_management: true`), no local Keycloak.

Apply a `configs/nomad.yaml` change:
`docker compose up -d --no-deps --force-recreate app worker` (a plain `restart`
can keep the pre-edit file; see the Layout note).
Stop: `docker compose down` (add `-v` to also wipe the named volumes).

## Environment quirks (this VM)

- `mongo` is pinned to `7.0`. MongoDB 8.0 aborts on Linux kernels 6.19 through
  7.0.13 (SERVER-121912); this VM runs 7.0.0. Move back to 8.0 after the VM
  kernel reaches >= 7.0.14.
- After creating the repo from the template, an `initialize.yml` workflow
  pushes a "Repository initialization" commit that renders `{{ repository }}`
  placeholders and sets the image name. Pull it before working.
- ~10 GiB VM RAM, ~5.7 GiB used by the stack. Fits, tight under load.

## Add a schema, cheapest first

1. YAML ELN schema uploaded as data, no rebuild. Prototype in `examples/`.
2. `tabular_parser` annotations for CSV or Excel, no rebuild.
3. App entry point or `ui.apps` in `nomad.yaml`, config only, no rebuild.
4. Promote a stable YAML schema to a Python schema-package plugin:
   - In `nomad-econversion-plugins`: add a section class under
     `src/nomad_econversion_plugins/schema_packages/`, an entry point in
     `schema_packages/__init__.py` and `pyproject.toml`, commit, `git tag vX.Y.Z`.
   - Here: bump the `@vX.Y.Z` ref in `pyproject.toml` plugins, `uv lock`,
     rebuild the image, `docker compose up -d app worker proxy`.
   - Verify: `curl localhost/nomad-oasis/api/v1/info` shows the package and
     entry point.

## Conventions

- One phase at a time; within a phase, one step at a time. Run a command, show
  the output, explain, then the next step. No chained untested steps.
- Before a multi-file or structural change, outline the approach first.
- Ask before deleting files, force-pushing, or overwriting work.
- Real findings go back into `docs/oasis-adoption-plan.md`, not just fixed.
- Commit messages: one plain-English sentence, no prefix format.
- No em dash in files that get saved or exported. Write "it is", not "it's".

## Session efficiency

- Do not re-read a file already read this session. Use what is in context.
- Do not paste full file contents or full command output into replies. Quote the
  few relevant lines and summarize.
- Prefer `grep` / `head` / `docker compose logs --since` filters over dumping
  whole files or logs.
- Default to 2-3 sentence explanations. Expand only when asked.
- One phase per session where practical. At a phase boundary, suggest `/clear`
  and rely on `docs/oasis-adoption-plan.md` plus memory as the handoff.
- Do not restate a plan already in `docs/`. Link to it.

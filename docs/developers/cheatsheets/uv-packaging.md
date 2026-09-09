# uv and Python packaging cheat sheet

Reference for building the plugin package and running the lockfile step.
Official: https://docs.astral.sh/uv/ and
https://packaging.python.org/en/latest/tutorials/packaging-projects/.

## Why a package at all

NOMAD discovers plugins through Python **entry points**. To have an entry
point, your code must be an installed package with metadata. A loose `.py` file
is not enough. Building the package is Phase 3.

## `pyproject.toml` anatomy

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nomad-econversion-plugins"
version = "0.1.0"
dependencies = ["nomad-lab"]

[project.optional-dependencies]
tests = ["pytest"]

[project.entry-points.'nomad.plugin']
grill_attempt = "nomad_econversion_plugins.schema_packages:grill_attempt"
```

- `[build-system]` names the tool that turns the source into an installable
  wheel. `hatchling` is one common backend, `setuptools` is another.
- `[project]` is the standard metadata: name, version, dependencies.
- `[project.optional-dependencies]` are extras, installed on request with
  `package[extra]`. This distro's plugin list is the `plugins` extra.
- `[project.entry-points.'<group>']` is the discovery mechanism. `<group>` is
  a name other code agrees to look up. NOMAD looks up `nomad.plugin`. The value
  is `module.path:object_name`.

## Entry points, concretely

```
docker compose exec -T app python3 -c "
from importlib.metadata import entry_points
for ep in entry_points(group='nomad.plugin'):
    print(ep.name, '->', ep.value)
"
```

NOMAD calls this at startup, loads each object, and registers the schema or
parser it describes. Nothing imports your package by name; the metadata is the
contract.

## uv commands

| Command | What it does |
|---|---|
| `uv lock` | Resolve dependencies, write `uv.lock` with exact versions and hashes |
| `uv sync` | Install exactly what `uv.lock` says into the environment |
| `uv sync --extra plugins` | Also install the `plugins` optional-dependency group |
| `uv run CMD` | Run a command in the project environment |
| `uv export --frozen -o requirements.txt` | Emit a pinned `requirements.txt` |

`uv.lock` is a lockfile: every transitive dependency pinned to one version and
hash, so the build is identical on any machine. `uv sync` fails if `uv.lock` is
stale relative to `pyproject.toml`.

## Running uv without installing it

`uv` is not on the reference VM. Run it in a container, mounting the repo:

```
docker run --rm -v "$PWD":/w -w /w \
  ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim uv lock
```

- `-v "$PWD":/w` mounts the current directory as `/w` in the container.
- `-w /w` sets the working directory.
- The image entrypoint is `uv`, then `lock` is the argument.

## Pinning a dependency to a git tag

In the distribution `pyproject.toml`, the plugin is a dependency by URL and
tag:

```
nomad-econversion-plugins @ git+https://github.com/cates-tum/nomad-econversion-plugins.git@v0.1.0
```

`@v0.1.0` is a git ref. `uv lock` resolves it to the exact commit hash and
records that in `uv.lock`. To move to a new plugin version: change the tag,
run `uv lock`, rebuild the image.

The distribution builder mounts only `pyproject.toml`, `uv.lock`, and `.git`,
so a plugin given as a local path (`file:///...`) is invisible to the build.
It must be a PyPI package or a `git+https` URL.

## The full plugin loop (Phase 3)

1. Edit the plugin, in the plugin repo.
2. `git commit`, `git tag vX.Y.Z`, `git push --tags`.
3. In this repo, bump the `@vX.Y.Z` in `pyproject.toml`.
4. `uv lock` (via the container command above).
5. Rebuild the image (`docker build --target final ...`).
6. `docker compose up -d app worker proxy`.
7. Verify: `curl localhost/nomad-oasis/api/v1/info` shows the package version
   and a `schema_package` entry point.

This loop is slow. Prototype schemas as YAML first, promote to a package only
when stable.

## Gotchas

- Forgetting `uv lock` after changing `pyproject.toml` makes the image build
  fail on a stale-lock error.
- The `src/` layout means the import name (`nomad_econversion_plugins`) has
  underscores while the distribution name (`nomad-econversion-plugins`) has
  hyphens. Both appear, in different places.
- An entry point value is `module:object`. A wrong module path fails silently
  at NOMAD startup, the plugin just does not appear in `/api/v1/info`.
- A tag that is committed but not pushed makes the `git+https` clone in CI or
  in the build fail.

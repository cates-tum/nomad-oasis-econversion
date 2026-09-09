# Lab 3: promote the schema to a Python plugin

Reproduces Phase 3 of `docs/oasis-adoption-plan.md`.

By the end you will have built an installable Python package that registers a
NOMAD schema through an entry point, pinned it by git tag, regenerated the
lockfile, rebuilt the image, and verified the plugin loaded.

Modules exercised: 9 packaging and the build loop.

Time: 3 to 5 hours, most of it the image rebuild. Prerequisite: Lab 2 done, and
you understand why the YAML `m_def` was a per-upload reference.

## Why do this

A YAML schema is fast to iterate but its section reference is per upload. A
Python schema-package plugin gives the same schema a stable, versioned,
importable identity that apps and other labs can rely on. The cost is a slow
loop: edit, tag, pin, lock, rebuild.

## 1. Understand the entry point mechanism

A Python package can advertise named objects in its metadata. Other programs
read that metadata and load the objects without importing the package first.
NOMAD looks for the group `nomad.plugin`.

```
docker compose exec -T app python3 -c "
from importlib.metadata import entry_points
for ep in entry_points(group='nomad.plugin'):
    print(ep.name, '->', ep.value)
"
```

You will see the plugins already installed in the image. By the end of this lab
you will add one.

## 2. Get the plugin repo

The team keeps one shared plugin repo. Clone it next to your lab checkout.

```
cd ~/labs
git clone git@github.com:cates-tum/nomad-econversion-plugins.git
cd nomad-econversion-plugins
tree -L 3 src 2>/dev/null || find src -maxdepth 3
```

Layout:

```
src/nomad_econversion_plugins/schema_packages/
  __init__.py    # SchemaPackageEntryPoint subclass and an instance
  grill.py       # m_package = SchemaPackage(); class GrillAttempt(...); m_package.__init_metainfo__()
pyproject.toml   # build backend, dependencies, the nomad.plugin entry point
```

Read `pyproject.toml`. The key line is under
`[project.entry-points.'nomad.plugin']`, mapping a name to
`nomad_econversion_plugins.schema_packages:grill_attempt`, the module path and
the object.

Read `src/nomad_econversion_plugins/schema_packages/grill.py`. It is the Phase
2 YAML schema in Python:

- section-level hide: `m_def = Section(a_eln=ELNAnnotation(hide=[...]))`
- enum: `Quantity(type=MEnum('a','b'), a_eln=ELNAnnotation(component=ELNComponentEnum.EnumEditQuantity))`
- units: `unit='celsius'` plus `defaultDisplayUnit='celsius'`
- the file ends with `m_package.__init_metainfo__()`

## 3. Make a change and tag it

Add one quantity to `GrillAttempt`, for example:

```python
    marinade = Quantity(
        type=str,
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
```

Commit and tag. Semantic version, patch bump.

```
git add -A
git commit -m "Add marinade quantity to GrillAttempt"
git tag v0.1.1
git push origin main --tags
```

A tag is a fixed name for a commit. Pinning a dependency to a tag makes the
build reproducible.

## 4. Pin the new tag in this distribution

```
cd ~/labs/oasis-lab0
grep -n nomad-econversion-plugins pyproject.toml
```

Change the ref to your tag:

```
nomad-econversion-plugins @ git+https://github.com/cates-tum/nomad-econversion-plugins.git@v0.1.1
```

## 5. Regenerate the lockfile

`uv.lock` pins every dependency to an exact version and hash. The image build
runs `uv sync`, which fails on a stale lock. `uv` is not on the host, so run it
in a container.

```
docker run --rm -v "$PWD":/w -w /w \
  ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim uv lock
git diff uv.lock | head -30
```

The diff should show the plugin's commit hash changing to the `v0.1.1` commit.

## 6. Rebuild the image

Same command as Lab 0. The `uv sync --extra plugins` layer reruns because
`pyproject.toml` and `uv.lock` changed.

```
docker build --target final \
  --build-arg UV_VERSION=0.9 \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg NOMAD_DOCS_REPO=https://github.com/FAIRmat-NFDI/nomad-docs.git \
  --build-arg JUPYTER_VERSION=2025-04-14 \
  -t ghcr.io/cates-tum/nomad-oasis-econversion:main .
```

## 7. Restart and verify

```
docker compose up -d app worker proxy
```

```
curl -s "localhost/nomad-oasis/api/v1/info" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('packages:', [(p['name'], p.get('version')) for p in d.get('plugin_packages', [])])
print('schema entry points:', [e['name'] for e in d.get('plugin_entry_points', []) if e.get('entry_point_type') == 'schema_package'])
"
```

Then in the GUI, Create from schema, pick the packaged `GrillAttempt`, and
confirm `marinade` is on the form. Read the archive back: `m_def` is now
`nomad_econversion_plugins.schema_packages.grill.GrillAttempt`, a stable
reference, not a per-upload path.

## 8. Verification checklist

- [ ] `entry_points(group='nomad.plugin')` inside the container lists your
  entry point.
- [ ] `/api/v1/info` shows `nomad_econversion_plugins` and its version.
- [ ] A new entry from the packaged schema has the stable `m_def`.
- [ ] `marinade` appears on the generated form.

## Challenge

1. Time this loop. From "decide to add a field" to "field visible in a new
   entry", how many minutes? Compare with the same change in Lab 2 step 3.
2. The distribution builder mounts only `pyproject.toml`, `uv.lock`, and
   `.git`. Explain in two sentences why a plugin given as a local path
   (`file:///...`) would fail the build, and why `git+https@tag` works.
3. Deliberately skip step 5. Change the pin to a new tag but do not run
   `uv lock`, then rebuild. Read the error. This is why the lockfile step is
   not optional.

## Troubleshooting

- **Build fails: lock is not up to date.** You skipped `uv lock` after
  changing `pyproject.toml`. Run it, rebuild.
- **`/api/v1/info` still shows the old version.** The image did not rebuild, or
  Compose is still running the old one. Rebuild with the exact tag, then
  `docker compose up -d --force-recreate app worker`.
- **`git+https` clone fails in the build.** The tag was not pushed. Run
  `git push --tags` in the plugin repo and check on GitHub.

## Where this maps in the record

- `oasis-adoption-plan.md`, "Phase 3" and "Phase 3 notes".
- The plugin mechanism summary is in `../cheatsheets/uv-packaging.md` and
  `../cheatsheets/nomad-concepts.md`.

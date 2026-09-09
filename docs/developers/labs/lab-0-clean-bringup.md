# Lab 0: bring the stack up from nothing

Reproduces Phase 0 of `docs/oasis-adoption-plan.md`.

By the end you will have built the image by hand and started the full stack in
a fresh working copy, and you will have looked inside every service.

Modules exercised: 1 shell, 2 YAML, 3 Docker, 4 Compose, 5 architecture.

Time: 1 to 2 hours of work, plus 20 to 40 minutes of image build the first
time. Disk: about 16 GiB for the image and its layers.

## Two tracks

- **Track A**, do this first: clone this repo into a scratch directory, build,
  bring it up. You learn the build and Compose model without re-deriving
  decisions the team already made.
- **Track B**, optional and deeper: fork the upstream template
  `FAIRmat-NFDI/nomad-distro-template` and apply the Phase 0 changes yourself,
  using "Phase 0 implementation notes" in the adoption plan as the checklist.
  This shows you what the template ships versus what the team changed. Track B
  is several hours. Do it once, later, when Track A feels easy.

Everything below is Track A.

## 0. Check prerequisites

```
docker compose version        # expect v2.x
git --version                 # expect 2.30 or newer
gh auth status                # expect logged in
df -h .                       # expect 30 GiB or more free
free -m                       # expect about 10 GiB total
```

If `docker compose version` fails, install the Compose plugin
(https://docs.docker.com/compose/install/linux/). Every other lab needs it.

## 1. Get a clean working copy

Work in a scratch directory so your main checkout is untouched.

```
mkdir -p ~/labs && cd ~/labs
git clone git@github.com:cates-tum/nomad-oasis-econversion.git oasis-lab0
cd oasis-lab0
```

`git clone` copies the full history and checks out the default branch. The
directory name `oasis-lab0` is the last argument, so your clone does not
collide with the real checkout.

```
git log --oneline -5      # recent commits
git status                # clean working tree
ls -la                    # top-level layout
```

## 2. Read the repo before you run anything

Open these and match each to Module 5.

```
less docker-compose.yaml
less Dockerfile
less configs/nomad.yaml
less configs/nginx_http.conf
less configs/nginx_base_conf
```

Answer for yourself, on paper:

1. Which services have a `healthcheck`? Which one does `proxy` wait for?
2. Which services mount a **named volume** (a bare name under top-level
   `volumes:`), and which mount a **bind mount** (a path starting with `./`)?
3. `configs/nomad.yaml` is mounted into `app` at what path? Look for the line
   `- ./configs/nomad.yaml:/app/nomad.yaml`.
4. In `Dockerfile`, what does `--target final` select, and what three paths
   does the builder stage mount? The adoption plan "Layout" section has the
   answer if you get stuck.

## 3. Generate the environment files

```
bash scripts/generate-env.sh
ls -la .env .env.north
```

`.env` holds values Compose substitutes into `docker-compose.yaml` at parse
time (`$PWD`, user ids, image tag). It is generated, not committed, and it is
in `.gitignore`. Never put a real secret in a file that is committed. This
project uses central Keycloak, so there is no client secret to manage here.

Confirm `.env` is ignored:

```
git check-ignore .env && echo "ignored, good"
```

## 4. Build the image by hand

CI normally builds and publishes this image. For local work you build it once
and tag it exactly as `docker-compose.yaml` expects.

```
docker build --target final \
  --build-arg UV_VERSION=0.9 \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg NOMAD_DOCS_REPO=https://github.com/FAIRmat-NFDI/nomad-docs.git \
  --build-arg JUPYTER_VERSION=2025-04-14 \
  -t ghcr.io/cates-tum/nomad-oasis-econversion:main .
```

What each part does:

- `--target final` builds only up to the stage named `final` in the
  multi-stage `Dockerfile`, not the `jupyter` stage.
- `--build-arg NAME=value` passes a value to a matching `ARG` in the
  `Dockerfile`. These pin tool versions so the build is repeatable.
- `-t ghcr.io/cates-tum/nomad-oasis-econversion:main` is the tag. Compose
  refers to the image by this exact string, so the tag must match.
- `.` is the build context, the directory sent to the builder.

Watch the output. Each `Step` or layer is cached. The slow layer is
`uv sync --extra plugins`, which resolves and installs `nomad-lab` and the
plugins from `pyproject.toml`. A later rebuild that changes only a doc reuses
this layer and finishes in seconds.

When it finishes:

```
docker image ls | grep nomad-oasis-econversion
```

## 5. Start a subset, let Compose pull the rest

```
docker compose up -d app worker proxy
```

`-d` is detached. You named three services; Compose starts everything they
`depends_on` as well: `elastic mongo postgresql temporal` and the two one-shot
Temporal init jobs `temporal-setup-db` and `temporal-create-namespace`. The
one-shot jobs run, exit 0, and stay in `Exited` state. That is expected.

```
docker compose ps
```

Read the `STATUS` column. `app` and `worker` show `health: starting` for up to
a minute, then `healthy`. `proxy` has no healthcheck so it shows only `Up`.

Follow the app coming online:

```
docker compose logs -f app
```

Press Ctrl+C to stop following. The logs keep flowing to the container either
way.

Check health from outside:

```
curl -s localhost/nomad-oasis/alive
```

Expect `"I am, alive!"`. This request goes browser-style through nginx on port
80 to `app`.

## 6. Walk the stack

One service at a time. This is Module 5 made concrete.

```
# app: the API and GUI server
docker compose exec app bash -lc 'ps aux | head; echo; curl -s localhost:8000/nomad-oasis/alive'

# worker: pulls and runs Temporal activities
docker compose logs --since 5m worker | tail -20

# mongo: NOMAD's metadata store
docker compose exec mongo mongosh nomad_oasis_v1 --quiet --eval 'db.getCollectionNames()'

# elastic: the search index
docker compose exec elastic curl -s localhost:9200/_cat/indices?v

# postgresql: Temporal's state store, not NOMAD's
docker compose exec postgresql psql -U temporal -c '\l'

# temporal: the orchestrator
docker compose exec temporal tctl --address temporal:7233 namespace list 2>/dev/null | head
```

For each, write one sentence: what is this service for, and who talks to it.
Check your sentences against the "components" table in the adoption plan.

## 7. Log in through the GUI

Open `http://localhost/nomad-oasis/gui/`.

Login goes to the central `nomad-lab.eu` Keycloak because
`configs/nomad.yaml` sets `oasis.uses_central_user_management: true`. There is
no local identity service. Use a NOMAD account, or register one on
`nomad-lab.eu` first.

After login you land on the About page. Explore, Publish, and Analyze are in
the top navigation.

## 8. Verification checklist

- [ ] `docker compose ps` shows `app` and `worker` `healthy`, `elastic mongo
  postgresql temporal` up, the two `temporal-*` jobs `Exited (0)`.
- [ ] `curl -s localhost/nomad-oasis/alive` returns the alive string.
- [ ] `curl -s localhost/nomad-oasis/api/v1/info | head -c 200` returns JSON.
- [ ] You can log in to the GUI with a central account.
- [ ] You can state, without looking, which database is NOMAD's and which is
  Temporal's.

## 9. Stop

```
docker compose down          # stop and remove containers, keep volumes
# docker compose down -v      # also delete the named volumes (all data)
```

Use `down` between lab sessions. Use `down -v` only when you want a clean slate.

## Challenge

No walkthrough. Do these and write your answers in a scratch file.

1. Bring the stack down, then start **only** `mongo`. Which other services, if
   any, start with it, and why? Now start `app` and record which services
   Compose adds.
2. `app` and `worker` bind-mount `configs/nomad.yaml`. Change one harmless
   value (for example add a comment line), then run `docker compose restart
   app`. Does the file inside the container update? Check with
   `docker compose exec app tail -5 /app/nomad.yaml`. Then try
   `docker compose up -d --no-deps --force-recreate app` and check again.
   Explain the difference. This is the inode caveat from Module 4 and Lab 4.
3. Break `configs/nginx_base_conf` on purpose: add a line `proxy_pass
   http://does-not-exist:9000;` inside a new `location /break/ { }` block.
   Recreate `proxy`. What happens, and what does `docker compose logs proxy`
   say? Revert.
4. From `docker-compose.yaml`, find the Elasticsearch JVM heap setting and its
   value. Why is it capped, given the note in the adoption plan about this VM?

## Troubleshooting

- **`mongo` container exits immediately.** On a Linux kernel between 6.19 and
  7.0.13, MongoDB 8.0 aborts (SERVER-121912). This repo pins `mongo:7.0` for
  that reason. Confirm with `uname -r`.
- **GUI loads but any processing returns 500 with "Namespace default is not
  found".** The `temporal-create-namespace` one-shot job did not run. It is in
  the `depends_on` of `app` and `worker` in this repo, so a plain
  `docker compose up -d app worker proxy` runs it. If you started services in
  an unusual order, run `docker compose up -d temporal-create-namespace`.
- **`proxy` will not start.** A `location` block with a static `proxy_pass` to
  a host Docker cannot resolve makes nginx fail at startup. The NORTH block in
  `configs/nginx_base_conf` is commented out for this reason.
- **Build fails on `uv sync` with a lock error.** `uv.lock` is out of date
  relative to `pyproject.toml`. Regenerate it with the container command in the
  adoption plan "Layout" section, then rebuild.

## Where this maps in the record

- `oasis-adoption-plan.md`, "Phase 0: setup" and "Phase 0 implementation
  notes".
- The seven-service decision is in the "Decisions made" table.

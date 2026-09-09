# Docker Compose cheat sheet

Reference for working the stack in this repo. Compose v2 (`docker compose`, two
words). Not a tutorial, see Module 4 in `../learning-plan.md`.

Official: https://docs.docker.com/compose/

## Mental model

One `docker-compose.yaml` describes a set of **services**. Each service runs as
one **container** from an **image**. Compose creates a private network named
after the project; on it, services reach each other by service name
(`mongo`, `elastic`, `temporal`). You bring services up and down as a group or
by name.

State lives in two kinds of storage:

- **named volume**: a bare name listed under the top-level `volumes:` key.
  Docker manages it. It survives `down` and is removed by `down -v`.
- **bind mount**: `./path/on/host:/path/in/container`. The host path is the
  truth. Good for config and code you edit.

## Everyday commands

| Command | What it does |
|---|---|
| `docker compose up -d` | Start all services, detached |
| `docker compose up -d app worker proxy` | Start these plus everything they `depends_on` |
| `docker compose ps` | List this project's containers and status |
| `docker compose ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'` | Compact status |
| `docker compose logs -f app` | Follow one service's logs, Ctrl+C to stop following |
| `docker compose logs --since 10m worker` | Last 10 minutes only |
| `docker compose exec app bash` | Shell in the running `app` container |
| `docker compose exec -T app <cmd>` | Run `<cmd>`, no TTY, good for scripts and pipes |
| `docker compose run --rm --no-deps --entrypoint sh app -c '<cmd>'` | One-off container, removed after, no dependencies started |
| `docker compose restart app worker` | Restart the process in the existing container |
| `docker compose up -d --no-deps --force-recreate app worker` | Recreate these containers from the compose spec, do not touch dependencies |
| `docker compose down` | Stop and remove containers and the network, keep named volumes |
| `docker compose down -v` | Also delete named volumes, all data gone |
| `docker compose config` | Print the fully resolved config, fails on a syntax error |
| `docker compose config --quiet` | Validate only, no output on success |
| `docker compose cp configs/nomad.yaml app:/tmp/x.yaml` | Copy a file into a running container |
| `docker compose pull` | Pull newer images for services with an `image:` |

## restart vs force-recreate, the inode caveat

`docker compose restart app` restarts the process inside the **same**
container. The container keeps the exact file handles it started with.

A single-file bind mount (`./configs/nomad.yaml:/app/nomad.yaml`) is bound to
the file's inode at container start. Most editors, and many tools, save by
writing a new file and renaming it over the old one, which changes the inode.
After that, the running container still points at the old, now-unlinked inode
and shows stale content. `restart` does not fix this.

`docker compose up -d --no-deps --force-recreate app worker` destroys and
recreates the containers, which re-resolves the bind mount to the current file.
Use this to apply a `configs/nomad.yaml` change. Expect about 30 seconds of API
downtime while `app` restarts.

Before you recreate, validate the new config out of band so a bad file does not
leave the container crash-looping:

```
docker compose cp configs/nomad.yaml app:/tmp/new_nomad.yaml
docker compose exec -T app python3 -c "
import yaml
from nomad.config.models.ui import UI
UI(**yaml.safe_load(open('/tmp/new_nomad.yaml'))['ui'])
print('config OK')
"
```

## Reading `docker-compose.yaml` in this repo

Keys you will see and what they mean:

| Key | Meaning |
|---|---|
| `image:` | The image to run. `app` and `worker` use `ghcr.io/cates-tum/nomad-oasis-econversion:main`, built locally in Lab 0 |
| `command:` | Overrides the image's default command. `app` runs `nomad.cli admin run app --with-gui ...` |
| `environment:` / `env_file:` | Variables in the container. `env_file: ./.env` reads the generated file |
| `ports: ["80:80"]` | Publish container port 80 as host port 80. Only `proxy` publishes ports |
| `volumes:` | Bind mounts (`./...`) and named volumes (bare names) |
| `depends_on:` with `condition:` | Ordering. `service_healthy`, `service_started`, `service_completed_successfully` |
| `healthcheck:` | A command Docker runs to decide `healthy` vs `starting` |
| `profiles:` | A service only starts if its profile is selected. `logtransfer` is behind `with_logtransfer` |

## This stack

Long-running: `elastic mongo postgresql temporal worker app proxy`.
One-shot, run then `Exited (0)`: `temporal-setup-db`,
`temporal-create-namespace`.
Present but off: `north`, `logtransfer`.

Data:

| Store | Kind | Where |
|---|---|---|
| Raw and processed files | bind mount | `./.volumes/fs` |
| MongoDB | named volume | Docker-managed |
| Elasticsearch | named volume | Docker-managed |
| PostgreSQL | named volume | Docker-managed |

`temporal-create-namespace` is in the `depends_on` of `app` and `worker`, so
any `up` that starts them creates the Temporal `default` namespace first. It is
idempotent across `down` and `up`.

## Common tasks

Apply a config change:

```
# edit configs/nomad.yaml, then
docker compose up -d --no-deps --force-recreate app worker
```

Full reset, keep the image:

```
docker compose down -v
docker compose up -d app worker proxy
```

Inspect what a container actually mounted:

```
docker inspect $(docker compose ps -q app) \
  --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

Terminate a stuck Temporal workflow (see `temporal.md` for detail):

```
docker compose run --rm --no-deps --entrypoint temporal \
  temporal-create-namespace workflow terminate \
  --address temporal:7233 -n default --workflow-id <id> --reason "stuck"
```

## Gotchas

- `docker compose` (v2 plugin) not `docker-compose` (v1, deprecated). This repo
  needs v2.
- `up -d` without service names starts everything, including services you may
  want off. Name the services.
- `down` without `-v` keeps volumes, so old data persists into your next `up`.
  Use `-v` for a true clean slate.
- `restart` does not reload a changed bind-mounted file. Use
  `--force-recreate`.
- `exec` needs the container running. For a stopped or one-shot service use
  `run --rm`.
- A service that fails its `healthcheck` blocks anything that waits on
  `condition: service_healthy`.

# Docker cheat sheet

Reference for images and containers. For the multi-service stack see
`docker-compose.md`. Official: https://docs.docker.com/get-started/.

## Mental model

- **Image**: a built, immutable stack of filesystem layers plus metadata
  (default command, env, exposed ports). Think of it as a class.
- **Container**: a running instance of an image, with a writable top layer.
  Think of it as an object. Deleting a container without a volume loses its
  writable layer.
- **Registry**: where images are stored and pulled from. Docker Hub by
  default. This project uses GitHub Container Registry, `ghcr.io`.
- **Tag**: a human name for an image version, `name:tag`. `latest` is just a
  conventional default tag, not special.

## Layers and the build cache

A `Dockerfile` is a list of instructions. Each `RUN`, `COPY`, `ADD` makes a
layer. On rebuild, Docker reuses a cached layer if that instruction and its
inputs are unchanged, and rebuilds every layer after the first change. So order
matters: put rarely-changing steps early, frequently-changing steps late.

In this repo the slow layer is `uv sync --extra plugins`. It reruns only when
`pyproject.toml` or `uv.lock` changes. A docs-only change reuses it.

## Everyday commands

| Command | What it does |
|---|---|
| `docker build -t name:tag .` | Build from `./Dockerfile`, tag it |
| `docker build --target STAGE ...` | Build only up to a named stage |
| `docker build --build-arg K=V ...` | Set an `ARG` |
| `docker image ls` | List local images and sizes |
| `docker ps` | Running containers |
| `docker ps -a` | All containers, including stopped |
| `docker logs -f NAME` | Follow a container's logs |
| `docker exec -it NAME bash` | Shell into a running container |
| `docker run --rm -it IMAGE bash` | New throwaway container, shell in it |
| `docker inspect NAME` | Full JSON: mounts, env, network, state |
| `docker stop NAME` / `docker rm NAME` | Stop, remove a container |
| `docker rmi IMAGE` | Remove an image |
| `docker system df` | Disk used by images, containers, volumes, cache |
| `docker system prune` | Remove stopped containers, unused networks, dangling images |
| `docker system prune -a --volumes` | Also remove unused images and volumes. Careful |

## This repo's build command, dissected

```
docker build --target final \
  --build-arg UV_VERSION=0.9 \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg NOMAD_DOCS_REPO=https://github.com/FAIRmat-NFDI/nomad-docs.git \
  --build-arg JUPYTER_VERSION=2025-04-14 \
  -t ghcr.io/cates-tum/nomad-oasis-econversion:main .
```

- `--target final`: the `Dockerfile` has multiple stages. `final` is the app
  image. `jupyter` is a separate stage for the optional NORTH tool image.
- `--build-arg`: pins tool versions so the build is repeatable across machines.
- `-t ghcr.io/cates-tum/nomad-oasis-econversion:main`: Compose refers to the
  image by this exact string. If the tag does not match, `docker compose up`
  tries to pull from GHCR and fails.
- `.`: the build context. The builder stage in this `Dockerfile` mounts only
  `pyproject.toml`, `uv.lock`, and `.git`, so plugins must be installable
  packages, never local paths.

## Registries and GHCR

| Command | What it does |
|---|---|
| `docker pull ghcr.io/owner/name:tag` | Pull an image |
| `docker push ghcr.io/owner/name:tag` | Push (needs auth and package write) |
| `echo $TOKEN \| docker login ghcr.io -u USER --password-stdin` | Authenticate |

CI builds and pushes this image. Locally you build by hand to avoid managing a
token. CI push to GHCR is gated to version tags, see `github-actions.md`.

## Disk hygiene on a small VM

The NOMAD image plus its build cache is large. When space runs low:

```
docker system df                    # see what is using space
docker builder prune                # drop the build cache
docker image prune                  # drop dangling images
docker system prune -a              # drop all unused images. Rebuild needed after
```

Do not prune volumes unless you mean to lose the databases. Use
`docker volume ls` first.

## Gotchas

- A stopped container still exists and holds its writable layer until
  `docker rm`. `docker ps -a` shows it.
- `docker exec` needs the container running. Use `docker run` for a stopped
  image.
- `latest` is not automatic. If you build `:main`, nothing else updates.
- `docker build` with no cache hit on an early layer rebuilds everything after
  it. Reorder the `Dockerfile` if a cheap change forces the expensive layer.
- Bind-mounted single files have an inode caveat that affects Compose, see
  `docker-compose.md`.

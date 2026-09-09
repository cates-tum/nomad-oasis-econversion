# nginx cheat sheet

Reference for the reverse proxy in front of NOMAD. Official beginner's guide:
https://nginx.org/en/docs/beginners_guide.html.

## What it does here

The browser talks to nginx on port 80. nginx forwards requests to the `app`
container on port 8000. This is a **reverse proxy**: one public entry point in
front of a private backend. It also handles large upload bodies, gzip, and
would terminate TLS in a real deployment.

## Config structure

nginx config is a tree of **blocks**. In this repo:

- `configs/nginx_http.conf` is mounted as the main site config. It defines the
  `upstream` (the backend address) and one `server { listen 80; ... }` block.
- Inside that `server` block, `include conf.d/nginx_base_conf;` pulls in
  `configs/nginx_base_conf`, which holds all the `location` blocks. Shared so
  the HTTP and HTTPS configs can reuse them.

```
http {
  upstream nomad-app-backend { server app:8000; }
  server {
    listen 80;
    server_name localhost;
    include conf.d/nginx_base_conf;   # the location blocks
  }
}
```

## location blocks and match priority

A `location` picks which block handles a request path. Match types, in the
order nginx picks them:

| Syntax | Meaning | Priority |
|---|---|---|
| `location = /path` | Exact match, path must equal `/path` | Highest, wins immediately |
| `location ^~ /path/` | Prefix match, stop searching regexes if it matches | High |
| `location ~ regex` | Case-sensitive regex | Checked in file order |
| `location ~* regex` | Case-insensitive regex | Checked in file order |
| `location /path/` | Plain prefix match | Lowest, used if nothing better matched |

Rule of thumb: exact `=` for a single URL, plain prefix for a subtree, regex
only when you must.

## Directives you will see

| Directive | What it does |
|---|---|
| `proxy_pass http://name;` | Forward the request to an upstream or URL |
| `return 302 /new/path;` | Send a redirect, no backend call |
| `rewrite ^ /new break;` | Rewrite the path, `break` stops rewrite processing |
| `error_page 404 = @name;` | On 404, internally jump to a named location |
| `client_max_body_size 35g;` | Allow large request bodies, used for uploads |
| `proxy_set_header Host $host;` | Pass headers through to the backend |

## This repo's key blocks

- `location = /nomad-oasis/gui/ { return 302 /nomad-oasis/gui/search/grill-attempts; }`
  Exact match, added in Phase 4 so the GUI opens on the custom app instead of
  the About page. Deeper GUI routes and assets fall through to the prefix
  block below it.
- `location /nomad-oasis/gui/ { ... error_page 404 = @redirect_to_index; ... }`
  Serves the single-page app. A 404 on a client-side route is rewritten to
  `index.html` so the app can handle routing.
- The `location /nomad-oasis/north/` block is commented out. A static
  `proxy_pass` to a host nginx cannot resolve makes nginx fail at startup, and
  NORTH is off in this stack.

## Apply a config change

The config files are bind-mounted read-only into the `proxy` container. Same
inode caveat as `nomad.yaml`: recreate, do not just reload.

```
docker compose up -d --no-deps --force-recreate proxy
```

To test the config syntax without touching the running stack:

```
docker run --rm \
  -v "$PWD/configs/nginx_base_conf":/etc/nginx/conf.d/nginx_base_conf:ro \
  -v "$PWD/configs/nginx_http.conf":/etc/nginx/conf.d/default.conf:ro \
  docker.io/nginx:1.31.1-alpine nginx -t
```

`nginx: configuration file ... test is successful` means the syntax is valid.
It does not check that upstreams resolve.

## Test a route without a browser

```
curl -s -o /dev/null -D - "http://localhost/nomad-oasis/gui/" | grep -i '^location:'
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost/nomad-oasis/api/v1/info"
```

## Gotchas

- A `location` added **after** a matching prefix block may never be reached.
  Order and match type both matter. Put `=` blocks first.
- `proxy_pass` with a trailing slash versus without changes how the path is
  passed. Match the existing blocks in this file.
- nginx fails to **start** if any `proxy_pass` names a host it cannot resolve
  at load time. That is why NORTH is commented out here.
- Changes need a container recreate, not just `nginx -s reload`, because of the
  bind-mount inode behaviour.

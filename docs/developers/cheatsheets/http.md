# HTTP cheat sheet

Reference for the protocol every service in this stack speaks. Working
proficiency level. Full guide: https://developer.mozilla.org/en-US/docs/Web/HTTP.

## What it is

A client sends a **request**, a server sends back one **response**, the
connection is done. No state is kept between requests unless something (a
cookie, a token) carries it. Everything you do to this stack from the shell is
one of these round trips.

Request:

```
POST /nomad-oasis/api/v1/entries/query HTTP/1.1
Host: localhost
Content-Type: application/json
Authorization: Bearer eyJhbGc...

{"query": {"owner": "user"}, "pagination": {"page_size": 5}}
```

Response:

```
HTTP/1.1 200 OK
Content-Type: application/json

{"data": [ ... ], "pagination": { ... }}
```

## URL parts

```
http://localhost:80/nomad-oasis/api/v1/info?foo=bar
\__/   \_______/ \/ \______________________/ \_____/
scheme  host    port  path                   query string
```

## Methods

| Method | Means | Body | In this stack |
|---|---|---|---|
| `GET` | read, no side effect | no | `GET /api/v1/info`, `GET .../archive` |
| `POST` | create, or run a query too big for a URL | yes | `POST /api/v1/entries/query`, create an upload |
| `PUT` | put a resource at a known place | yes | `PUT` a file into an upload |
| `PATCH` | change part of a resource | yes | rare here |
| `DELETE` | remove | usually no | delete an upload |

NOMAD queries are `POST` because the query JSON does not fit sanely in a query
string, not because they change anything.

## Status codes

| Code | Class | Meaning here |
|---|---|---|
| `200` | success | OK, body has the answer |
| `201` | success | created (a new upload) |
| `204` | success | done, no body |
| `301` `302` | redirect | go to another URL. The GUI root `302`s to the grill-attempts app |
| `400` | your fault | malformed request |
| `401` | your fault | no token, or an expired one. Authenticate |
| `403` | your fault | valid token, but not allowed to see this |
| `404` | your fault | no such path or resource |
| `409` | your fault | conflict, e.g. publishing something already published |
| `422` | your fault | body parsed but failed schema validation. FastAPI returns the exact field |
| `500` | server fault | unhandled error in the app. Check `docker compose logs app` |
| `502` `503` | server fault | proxy could not reach the app, or the app is not ready yet |

`401` vs `403`: `401` is "I do not know who you are", `403` is "I know, and no".

## Headers you will touch

| Header | Does |
|---|---|
| `Host` | which site. nginx routes on it |
| `Content-Type` | format of the body you send. `application/json` for the API |
| `Accept` | format you want back |
| `Authorization` | `Bearer <token>` for the API. See `keycloak-auth.md` |
| `Content-Length` | set by `curl` for you |

## curl

| Flag | Does |
|---|---|
| `-i` | print response headers plus body |
| `-v` | print the request too, and the TLS handshake |
| `-s` | silent, no progress meter (use in scripts) |
| `-S` | with `-s`, still show errors |
| `-X POST` | set the method (curl infers `POST` when you pass `-d`) |
| `-H 'K: V'` | add a request header |
| `-d '{"a":1}'` | send this as the body, sets `Content-Type: application/x-www-form-urlencoded` unless you override |
| `--data-binary @file` | send a file's bytes as the body, unmodified |
| `-u user:pass` | HTTP basic auth |
| `-L` | follow redirects |
| `-o file` | write body to a file |
| `-w '%{http_code}\n'` | print a chosen variable after the transfer |
| `-G --data-urlencode k=v` | build a `GET` query string safely |

The health check, token by token:

```
curl -s localhost/nomad-oasis/alive
#    -s  no meter
#        host localhost, port 80, path /nomad-oasis/alive
#        nginx sees Host: localhost, matches the /nomad-oasis/ block,
#        proxies to the app, which returns 200 and the word "gunicorn"
```

A JSON POST with a token, the shape to memorize:

```
curl -s -X POST localhost/nomad-oasis/api/v1/entries/query \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": {"owner": "user"}, "pagination": {"page_size": 5}}'
```

## The reverse proxy changes the picture

Your `curl` talks to nginx on port 80, not to the app. nginx forwards to the
`app` container on the compose network and passes the answer back. So:

- A `502` means nginx is up but could not reach `app`. A connection refused
  means nginx itself is down.
- The app sees `Host` and path as nginx rewrote them. That is why paths in the
  API are under `/nomad-oasis/`.
- `curl localhost:8000` from inside the `app` container hits the app directly,
  bypassing nginx. Useful to split "is it the app or the proxy".

## For a SQL and requests background

- A response is not a cursor. You get the whole body at once, or you paginate
  with explicit `page` / `page_size` in the request.
- `GET` with a query string is `SELECT ... WHERE` with the filter in the URL.
  When the filter gets structured (nested `and`/`or`), it moves into a `POST`
  body as JSON. Same intent, different transport.
- There are no transactions across requests. Each request stands alone.

## Gotchas

- `curl -d` without `-H 'Content-Type: application/json'` sends form encoding
  and the API rejects it. Always set the header for JSON.
- Single vs double quotes in the shell: `'{"a":1}'` keeps the JSON literal,
  `"...$TOKEN..."` lets the variable expand. You often need one of each on
  different `-H` lines, as above.
- A trailing slash can matter. `/api/v1/uploads` and `/api/v1/uploads/` may
  differ. Match what the docs show.
- `-v` prints the token. Do not paste `-v` output into a chat or an issue
  without cutting the `Authorization` line.

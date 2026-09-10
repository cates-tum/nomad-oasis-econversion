# NOMAD API cheat sheet

Reference for driving this Oasis from `curl`. The API is a FastAPI app served
by the `app` container behind nginx. Official docs: the "Using the API" section
of https://nomad-lab.eu/prod/v1/docs/ and the live docs page on your own
instance.

Base URL on this stack: `http://localhost/nomad-oasis/api/v1`. Set it once:

```
API=http://localhost/nomad-oasis/api/v1
```

## Discover the API from the API

Do not trust a cheat sheet over the running server. The server publishes its
own contract:

```
curl -s $API/../../api/v1/openapi.json | python3 -m json.tool | less   # every path and schema
curl -s $API/info | python3 -m json.tool                               # versions, plugins, auth config
```

The interactive docs page (Swagger UI) is linked from `openapi.json` and from
the GUI. Open it in a browser to try calls with a form. `GET $API/info` also
returns the Keycloak `server_url`, `realm_name`, and `client_id` you need for a
token (see `keycloak-auth.md`).

## FastAPI, the parts you see as a caller

- A **path operation** is one function bound to a method and path. `openapi.json`
  lists them all.
- **Path parameters** are in the URL (`/entries/{entry_id}/archive`). **Query
  parameters** are the `?k=v` string. The **body** is JSON you send with `-d`.
- Request and response shapes are **Pydantic models**. Send a body that does not
  match and you get `422` with a JSON list of exactly which fields are wrong
  and why. Read that list, it is precise.
- Auth is a **dependency**: the same check runs on every protected route. No
  token gets you `401` on those routes and an empty result on the public ones.

## Core endpoints

Confirm paths against `openapi.json`; NOMAD versions move things occasionally.

| Call | Does |
|---|---|
| `GET $API/info` | server version, active plugins and entry points, auth config |
| `POST $API/entries/query` | search entries. Query language in the body |
| `GET $API/entries/{entry_id}` | one entry's metadata |
| `GET $API/entries/{entry_id}/archive` | the parsed archive for one entry |
| `POST $API/entries/archive/query` | search and pull archive parts in one call |
| `POST $API/uploads` | create an upload (optionally with the file in the same call) |
| `GET $API/uploads` | your uploads and their processing state |
| `PUT $API/uploads/{upload_id}/raw/{path}` | add or replace a file in an upload |
| `POST $API/uploads/{upload_id}/action/publish` | publish |
| `DELETE $API/uploads/{upload_id}` | delete |
| `GET $API/metainfo` | the schema definitions the server knows |

## The query language

The body of `entries/query` is `{"query": {...}, "pagination": {...}, "required": {...}}`.

Query:

```json
{
  "query": {
    "and": [
      {"entry_type": "GrillAttempt"},
      {"data.temperature#nomad_econversion_plugins.schema_packages...": {"gte": 400}},
      {"not": {"upload_name": "scratch"}}
    ],
    "owner": "user"
  },
  "pagination": {"page_size": 10, "page": 1, "order_by": "upload_create_time", "order": "desc"},
  "required": {"metadata": "*", "data": {"temperature": "*", "name": "*"}}
}
```

- `owner`: `public` (published, anyone), `user` (yours, needs a token), `all`
  (both, needs a token). Anonymous plus `owner: user` returns nothing, not an
  error.
- Custom schema quantities are addressed as
  `data.<name>#<section-qualified-name>`. The qualified name is in `GET
  $API/info` under the plugin's entry points, or in the schema YAML.
- `required` trims the response. `{"metadata": "*"}` returns metadata only, no
  archive. Ask for the whole archive only when you need it, it is large.
- Ranges: `{"gte": x, "lte": y}`. Membership: `{"any": [a, b]}`.

## A full cycle over the API only

```
# 1. token (see keycloak-auth.md)
TOKEN=...

# 2. create an upload with a file in one multipart call
curl -s -X POST "$API/uploads?upload_name=lab6" \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@my.archive.yaml

# 3. poll until process_status is SUCCESS
curl -s "$API/uploads" -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json; [print(u["upload_id"], u["process_status"]) for u in json.load(sys.stdin)["data"]]'

# 4. find the entry
curl -s -X POST "$API/entries/query" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"query": {"owner": "user", "upload_name": "lab6"}}'

# 5. one section of its archive
curl -s "$API/entries/$ENTRY_ID/archive" -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool | less

# 6. clean up
curl -s -X DELETE "$API/uploads/$UPLOAD_ID" -H "Authorization: Bearer $TOKEN"
```

## Maps to the datastores

`entries/query` reads Elasticsearch (`nomad_oasis_entries_v1`) for the search
and match, then pulls metadata from MongoDB (`nomad_oasis_v1`, `entry` and
`upload` collections) and, if you asked with `required`, the archive from disk
(`.volumes/fs`). See `elasticsearch.md` and `mongodb.md` for querying those
stores directly when you want to check what the API returned.

## Gotchas

- `422` is not a bug in your token, it is a bad body. Read the field list.
- The archive can be tens of MB. Always pass `required` unless you truly want
  all of it.
- Processing is async. After an upload, `process_status` goes `WAITING` then
  `RUNNING` then `SUCCESS` or `FAILURE`. Poll, do not assume.
- A `500` on a query usually means Elasticsearch or Mongo is down, or a
  Temporal namespace is missing. Check `docker compose ps` and the `app` logs.
- Paths under `/nomad-oasis/` because of the proxy. A bare `/api/v1/...` from
  the host `404`s at nginx.

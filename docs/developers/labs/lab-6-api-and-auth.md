# Lab 6: drive the stack from the API, authenticated

New in Tier 4, not a replay of a recorded phase. It exercises the API surface
the earlier phases used through the GUI.

By the end you will be able to get a Keycloak bearer token by hand, run the
full upload-to-archive cycle with `curl` only, read a `422` validation error,
and tell `401` from `403` from `422`.

Modules exercised: 0 HTTP, 13 NOMAD API and auth. Uses Module 7 (the
datastores) for cross-checking.

Time: 4 to 6 hours. Prerequisite: Labs 0 to 2 done, so the stack runs and you
have at least one `.archive.yaml` that processes cleanly. Keep `http.md`,
`nomad-api.md`, and `keycloak-auth.md` open.

## 1. Map the API from the API

```
API=http://localhost/nomad-oasis/api/v1
curl -s "$API/info" | python3 -m json.tool | less
curl -s "http://localhost/nomad-oasis/api/v1/openapi.json" | python3 -m json.tool | less
```

Answer for yourself, in writing:

- Which paths are `GET`, which are `POST`, and why are the search calls `POST`?
- Which paths have a lock icon in the Swagger UI (open the docs page in a
  browser)? Those run the auth dependency.
- What does `info` report for the Keycloak `server_url`, `realm_name`, and
  `client_id`?

## 2. Call the API anonymously first

```
curl -si "$API/info" | head -20
curl -si -X POST "$API/entries/query" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"owner": "user"}}'
```

The second call: note the status code and the body. `owner: user` with no
token is not an error, it just has nothing to show you. Now break it on
purpose:

```
curl -si -X POST "$API/entries/query" -H 'Content-Type: application/json' \
  -d '{"query": {"owner": "banana"}}'
curl -si -X POST "$API/entries/query" -H 'Content-Type: application/json' \
  -d 'not json'
```

Record which gives `422` and which gives `400`, and copy the `422` body. Read
the `loc` / `msg` fields. This is FastAPI telling you the exact path into your
JSON that failed the Pydantic model.

## 3. Get a token

Follow `keycloak-auth.md`. Pull the three values from `$API/info`, build
`TOKEN_URL`, run the password flow:

```
read -rsp 'NOMAD password: ' PW; echo
TOKEN=$(curl -s "$TOKEN_URL" -d grant_type=password -d client_id="$CLIENT" \
  -d username='YOU' -d password="$PW" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
```

If that returns `invalid_grant`, use the browser-network-tab fallback in the
cheat sheet. Then decode the payload:

```
echo "$TOKEN" | cut -d. -f2 | tr '_-' '/+' | base64 -d 2>/dev/null | python3 -m json.tool
```

Write down your `sub`, `preferred_username`, and `exp` as a human date
(`date -d @<exp>`).

## 4. Re-run the query with the token

```
curl -s -X POST "$API/entries/query" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"query": {"owner": "user"}, "pagination": {"page_size": 5}}' \
  | python3 -m json.tool
```

Same call as step 2, different result. That difference is the whole point of
the token.

## 5. Full cycle, curl only

Use the block in `nomad-api.md` "A full cycle over the API only". Do every
step from the shell, no GUI:

1. Create an upload named `lab6` with a known-good `.archive.yaml` attached.
2. Poll `GET $API/uploads` until `process_status` is `SUCCESS`. Note it passes
   through `WAITING` and `RUNNING` first.
3. Query for the entry with `owner: user` and `upload_name: lab6`.
4. Fetch one section of its archive with a `required` that names just the
   fields you want. Compare the response size to fetching the whole archive.
5. Delete the upload.

## 6. Cross-check against the datastores

While the `lab6` upload exists, confirm the API answer against the raw stores
(Module 7):

```
docker compose exec elastic curl -s 'localhost:9200/nomad_oasis_entries_v1/_count'
docker compose exec mongo mongosh nomad_oasis_v1 --quiet \
  --eval 'db.upload.find({name: "lab6"}, {upload_id: 1, process_status: 1})'
```

The counts and ids should line up with what `curl` told you.

## 7. Verification checklist

- [ ] You can explain why `entries/query` is a `POST`.
- [ ] You produced a `422` and read which field it names.
- [ ] You have a token and can read its `sub` and `exp`.
- [ ] The same query returns different results with and without the token, and
      you can say why.
- [ ] You ran create, add file, poll, query, fetch archive, delete with no GUI.
- [ ] You can state in one line each what `401`, `403`, and `422` mean.

## Challenge

1. Without looking at the cheat sheet, write the `curl` that queries all
   entries of one `entry_type` with a numeric custom quantity above a
   threshold, returning metadata only.
2. Let your token expire (wait past `expires_in`), call the API, and confirm
   the status code. Then refresh it with the refresh-token grant and succeed.
3. Find a call that returns `403` for you (try fetching another user's
   unpublished entry id, if you can get one). Explain why it is `403` and not
   `404` or `401`.
4. From `openapi.json` alone, pick one endpoint this lab did not use, work out
   its parameters, and call it successfully.

## Troubleshooting

- **`invalid_grant` on the token call.** Wrong username or password, or the
  client has direct access grants disabled. Use the browser fallback.
- **`401` right after getting a token.** It expired (300 s), or `$API/info`
  points at a different realm than the one you got the token from. Re-fetch
  both.
- **Upload stuck in `RUNNING` forever.** A retrying Temporal workflow. See
  `temporal.md`, "The scenario you will hit".
- **`500` on any query.** `docker compose ps`, then `docker compose logs --since
  5m app`. Usually Elasticsearch, Mongo, or the Temporal namespace.

## Where this maps in the record

- No single commit. The GUI equivalents of this cycle are Phases 1 to 4 of
  `oasis-adoption-plan.md`. This lab does them through the layer underneath.
- Draft status: the step outline is complete; flesh out the exact response
  snippets on your first run and commit them back here.

# Phase 1 runbook: data in via shipped parsers

Resume point after Phase 0. Goal: upload a shipped example dataset, watch NOMAD
process it into entries, and learn what "processed" means (raw vs archive, the
metainfo tree, the search index). No custom code.

## Start of session: bring the stack back

The stack was stopped, not removed. Containers and volumes are intact.

```
cd ~/Workspace/nomad-oasis-econversion
docker compose start                      # restarts the same containers
docker compose ps                         # wait until app, worker, elastic, mongo, temporal are healthy
curl -s localhost/nomad-oasis/alive       # expect: "I am, alive!"
```

If `docker compose start` complains that containers are gone, recreate them:
`docker compose up -d app worker proxy` (uses the existing local image and
volumes, no rebuild).

Open `http://localhost/nomad-oasis/gui/` and log in with the central NOMAD
account.

## Phase 1 steps (one at a time)

### 1. Pick the example upload

Use **"Tabular Data"** (`example_uploads/1_basic_examples/1_tables`, category
"Basic examples"). It is an xlsx file plus a custom schema, so it exercises the
tabular parser, which is the ingest path Phase 2 builds on. The other two
(`rdm_tutorial`, `cow_tutorial`) are Jupyter notebook tutorials and need NORTH,
which is off. Skip them.

### 2. Create the upload from the example

GUI: **Publish > Uploads** (or `/nomad-oasis/gui/user/uploads`) > **Add example
uploads** > choose "Tabular Data" > **Add**. NOMAD copies the example files
into a new upload and starts processing.

### 3. Watch it process

- On the upload page, the processing status moves from `WAITING` to `RUNNING`
  to `SUCCESS`. On this VM expect it to be slow.
- Cross-check from the worker side:
  `docker compose logs -f worker` while it runs.
- When done, the upload shows one or more **entries**.

### 4. Inspect one entry

Open an entry. Note for the memory doc:
- **Overview tab**: core metadata, data cards.
- **Files tab**: the raw files, organised as the author uploaded them (the
  xlsx and the schema file). This is "raw", stored under
  `.volumes/fs/staging/<upload_id>` (or `.../public` once published).
- **Data tab**: the parsed archive, a hierarchical metainfo tree. This is the
  "NOMAD Archive", organised per entry, machine-readable. Expand the tree and
  see how the xlsx columns became typed quantities under the schema's section.

### 5. Confirm it reached the search index

- GUI: **Explore** (or a default app). The new entry should be findable, with
  filter chips for its fields.
- API: `curl -s -X POST localhost/nomad-oasis/api/v1/entries/query
  -H 'Content-Type: application/json' -d '{"query":{},"pagination":{"page_size":5}}'`
  and confirm the entry ids come back.

### 6. Try the default apps

Open the app menu. Note which apps ship by default (Entries, and the
discipline apps) and what each one presets: query, columns, filter menu.
This is the pattern Phase 4 copies for a custom app.

### 7. Write it down

In the memory doc, record what "processed" actually looks like on this
install: the raw/archive split, where the files sit on disk, what the metainfo
tree looked like for a tabular entry, and how long processing took. Then update
`docs/oasis-adoption-plan.md` Phase 1 checklist.

## End of session

```
docker compose stop
```

Commit anything changed with one plain-English sentence. Push if asked.

## Where physical data sits (verify during step 4)

- `./.volumes/fs/staging/<upload_id>/raw/` uploaded files, pre-publish
- `./.volumes/fs/staging/<upload_id>/archive/` processed archive (msgpack)
- `./.volumes/fs/public/...` after an upload is published
- Mongo: upload and entry metadata, processing state
- Elasticsearch: the search document per entry

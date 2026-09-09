# Lab 1: first upload, then follow the data

Reproduces Phase 1 of `docs/oasis-adoption-plan.md`.

By the end you will have uploaded a CSV with a schema, watched it process, and
found the resulting entry in all three stores: raw files on disk, the parsed
archive, and the Elasticsearch index. You will also run real queries against
Elasticsearch and MongoDB and unstick a Temporal workflow.

Modules exercised: 6 data model, 7 datastores.

Time: 2 to 3 hours. Prerequisite: Lab 0 done, stack up, logged in.

## 1. Look at what you will upload

```
cd ~/labs/oasis-lab0
ls examples/grill-sessions/
less examples/grill-sessions/grill_sessions.archive.yaml
less examples/grill-sessions/grill_sessions.csv
```

The `.archive.yaml` file has two blocks:

- `definitions:` declares a section `GrillSessions` with quantities, one per
  CSV column, each an array (`shape: ['*']`) with a type and a unit.
- `data:` sets `m_def` to that local section and points `data_file` at the CSV.
  The `tabular_parser` annotation on `data_file` tells NOMAD to fill the
  arrays from the CSV columns. This is **column mode**: one entry, each column
  becomes one array quantity.

Note the date column is `type: str`, not `Datetime`. A `Datetime` array parsed
from a table fails with `ValueError: Shape mismatch` in this version. This is a
Phase 1 finding.

## 2. Upload through the GUI

1. `http://localhost/nomad-oasis/gui/`, log in.
2. Publish, then Uploads, then "Create a new upload".
3. Drag both files from `examples/grill-sessions/` into the drop zone, or zip
   them first and drop the zip.
4. Watch the upload card. Processing runs, then the card shows 1 entry of type
   `GrillSessions` with state `SUCCESS`.

If processing fails, open the entry and read the error. The most common cause
is editing the YAML and breaking the indentation.

## 3. Find the upload id

```
docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '
db.upload.find({}, {_id:1, process_status:1}).forEach(u => printjson(u))'
```

Copy the `_id` of your upload. Call it `UP` below.

```
docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '
db.entry.find({upload_id:"UP"}, {_id:1, entry_type:1, parser_name:1}).forEach(e => printjson(e))'
```

Copy the entry `_id`. Call it `EN`.

## 4. Store 1: raw files on disk

Raw files are the upload exactly as you sent it, on the host bind mount.

```
ls -la .volumes/fs/staging/UP/raw/
```

You see the `.archive.yaml` and the `.csv`. That is all "raw" means.

## 5. Store 2: the parsed archive

The archive is the typed tree NOMAD built from the mainfile. It is msgpack on
disk, so you read it through NOMAD.

```
docker compose exec -T app python3 -c "
from nomad.files import StagingUploadFiles
with StagingUploadFiles('UP').read_archive('EN') as arch:
    d = arch['EN'].to_dict()
print('top-level keys:', list(d.keys()))
data = d['data']
print('quantities:', [k for k in data if not k.startswith('m_')])
print('grill_temp_c sample:', data.get('grill_temp_c', [])[:3])
"
```

Column mode put each CSV column into an array quantity on the single
`GrillSessions` entry.

## 6. Store 3: the Elasticsearch index

Every entry is also written to `nomad_oasis_entries_v1`, which is what the
Explore UI reads.

```
docker compose exec -T elastic curl -s \
  "localhost:9200/nomad_oasis_entries_v1/_doc/EN" | python3 -m json.tool | head -40
```

Look for `entry_type`, `published: false`, and `upload_id`. Unpublished entries
are visible only to the owner, which is why the anonymous API returns nothing:

```
curl -s "localhost/nomad-oasis/api/v1/entries?page_size=5" | python3 -m json.tool | head
```

`pagination.total` is 0 without a login token, even though the entry exists.

## 7. Elasticsearch query practice

`_search` with a JSON body. Contrast each with the SQL you would write.

Count entries by type, like `GROUP BY entry_type`:

```
docker compose exec -T elastic curl -s "localhost:9200/nomad_oasis_entries_v1/_search" \
  -H 'Content-Type: application/json' -d '{
    "size": 0,
    "aggs": { "by_type": { "terms": { "field": "entry_type" } } }
  }' | python3 -m json.tool
```

Filter, like `WHERE entry_type = 'GrillSessions'`:

```
docker compose exec -T elastic curl -s "localhost:9200/nomad_oasis_entries_v1/_search" \
  -H 'Content-Type: application/json' -d '{
    "query": { "term": { "entry_type": "GrillSessions" } },
    "_source": ["entry_name", "entry_type", "upload_id"]
  }' | python3 -m json.tool
```

`bool` combines clauses: `must` is AND scoring, `filter` is AND no scoring,
`should` is OR, `must_not` is NOT. See `../cheatsheets/elasticsearch.md`.

## 8. MongoDB query practice

```
docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '
db.entry.countDocuments({})'

docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '
db.entry.aggregate([
  { $group: { _id: "$entry_type", n: { $sum: 1 } } },
  { $sort: { n: -1 } }
])'
```

The aggregation pipeline is a list of stages. `$match` is `WHERE`, `$group` is
`GROUP BY`, `$project` is `SELECT`, `$sort` and `$limit` are what they sound
like. See `../cheatsheets/mongodb.md`.

## 9. Temporal, and a stuck workflow

Processing ran as a Temporal workflow. List recent workflows:

```
docker compose run --rm --no-deps --entrypoint temporal \
  temporal-create-namespace workflow list --address temporal:7233 -n default | head
```

A failed or deleted upload can leave a workflow retrying with backoff forever,
logging a traceback each time. Terminate one by id:

```
docker compose run --rm --no-deps --entrypoint temporal \
  temporal-create-namespace workflow terminate \
  --address temporal:7233 -n default --workflow-id <id> --reason "cleanup"
```

The `temporal` CLI only exists in the admin-tools image, which the
`temporal-create-namespace` service already uses, so you run it through that
service.

## 10. Verification checklist

- [ ] The upload shows 1 entry of type `GrillSessions`, state `SUCCESS`.
- [ ] You found the raw files under `.volumes/fs/staging/<id>/raw/`.
- [ ] You read at least one array quantity out of the archive.
- [ ] You fetched the entry from `nomad_oasis_entries_v1` by id.
- [ ] Your Elasticsearch and MongoDB "count by type" queries agree.

## Challenge

1. Write one Elasticsearch aggregation that returns, for each `entry_type`, the
   count and the earliest `upload_create_time`. Write the MongoDB aggregation
   that answers the same question. Write the SQL you would have used. Put all
   three in a scratch file with a sentence on how the three engines express
   `GROUP BY`.
2. Break the schema on purpose: change the date column in
   `grill_sessions.archive.yaml` from `type: str` to `type: Datetime`, upload
   again, and confirm the failure message. Then revert. This is the Phase 1
   `Shape mismatch` finding.
3. After challenge 2, find the workflow left behind by the failed upload and
   terminate it. Confirm with `workflow list` that it is gone.

## Troubleshooting

- **Upload stuck in `WAITING` or `RUNNING` forever.** Check the worker:
  `docker compose logs --since 10m worker`. A `Namespace default is not found`
  error means the namespace job did not run, see Lab 0 troubleshooting.
- **`read_archive` raises `KeyError`.** You passed the wrong entry id, or the
  upload id. Re-list both from Mongo.
- **`_doc/<id>` returns `"found": false`.** The entry id in Elasticsearch is
  the same as in Mongo. Copy it exactly, it contains characters like `-` and
  `_`.

## Where this maps in the record

- `oasis-adoption-plan.md`, "Phase 1" in the task list and "Phase 1
  implementation notes".
- The "what processed means" summary is in `../cheatsheets/nomad-concepts.md`.

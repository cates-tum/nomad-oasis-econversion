# MongoDB cheat sheet

Reference for NOMAD's metadata store. Working proficiency level. Official:
https://www.mongodb.com/docs/mongodb-shell/ and the Aggregation Pipeline docs.

## What it is

A document database. A **collection** holds **documents**, each a JSON-like
record (BSON on disk). No fixed schema per collection. NOMAD keeps its metadata
here: users, uploads, entries, processing state. This is separate from
PostgreSQL, which belongs to Temporal.

Database: `nomad_oasis_v1`. Collections you will use: `upload`, `entry`.

## The shell

```
docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '<js>'
```

`mongosh` runs JavaScript. `db` is the current database. Quote the whole `--eval`
in single quotes and use double quotes inside for JS strings.

Interactive session:

```
docker compose exec -it mongo mongosh nomad_oasis_v1
```

## Reads, with SQL alongside

| Goal | MongoDB | SQL |
|---|---|---|
| all rows | `db.entry.find()` | `SELECT * FROM entry` |
| pick columns | `db.entry.find({}, {entry_type: 1, _id: 0})` | `SELECT entry_type FROM entry` |
| filter | `db.entry.find({entry_type: "GrillAttempt"})` | `WHERE entry_type = 'GrillAttempt'` |
| comparison | `db.entry.find({process_status: {$ne: "SUCCESS"}})` | `WHERE process_status <> 'SUCCESS'` |
| in list | `db.entry.find({entry_type: {$in: ["A", "B"]}})` | `WHERE entry_type IN ('A','B')` |
| count | `db.entry.countDocuments({upload_id: "X"})` | `SELECT count(*) ... WHERE ...` |
| distinct | `db.entry.distinct("entry_type")` | `SELECT DISTINCT entry_type` |
| sort, limit | `db.entry.find().sort({_id: -1}).limit(5)` | `ORDER BY _id DESC LIMIT 5` |
| one document | `db.upload.findOne({_id: "X"})` | `... LIMIT 1` |

Query operators: `$eq $ne $gt $gte $lt $lte $in $nin $exists $regex`.

## Aggregation pipeline, with SQL alongside

A list of stages, each transforms the stream.

| Stage | Does | SQL |
|---|---|---|
| `$match` | filter | `WHERE` |
| `$group` | group and aggregate | `GROUP BY` |
| `$project` | reshape, compute fields | `SELECT expr AS ...` |
| `$sort` | order | `ORDER BY` |
| `$limit`, `$skip` | paginate | `LIMIT`, `OFFSET` |
| `$lookup` | join another collection | `JOIN` |
| `$unwind` | one row per array element | `CROSS JOIN UNNEST` |

Count entries by type, newest-first:

```
docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '
db.entry.aggregate([
  { $group: { _id: "$entry_type", n: { $sum: 1 } } },
  { $sort: { n: -1 } }
])'
```

Entries per upload, with the upload name, a join:

```
docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '
db.entry.aggregate([
  { $group: { _id: "$upload_id", entries: { $sum: 1 } } },
  { $lookup: { from: "upload", localField: "_id", foreignField: "_id", as: "u" } },
  { $project: { entries: 1, name: { $arrayElemAt: ["$u.name", 0] } } }
])'
```

`$group` accumulators: `$sum $avg $min $max $first $last $push $addToSet`.

## NOMAD documents

`upload`:

| Field | Meaning |
|---|---|
| `_id` | the upload id, also the raw-files directory name |
| `process_status` | `SUCCESS`, `READY`, `WAITING`, ... |
| `published`, `main_author` | ownership and visibility |

`entry`:

| Field | Meaning |
|---|---|
| `_id` | the entry id, matches the Elasticsearch `_id` |
| `upload_id` | parent upload |
| `entry_type` | the section name |
| `parser_name` | `parsers/archive` for our `.archive.yaml` entries |
| `process_status`, `errors`, `warnings` | processing outcome |

## Gotchas

- `find()` in `--eval` prints a cursor summary. Wrap with `.forEach(printjson)`
  or `.toArray()` to see documents.
- Single vs double quotes: single around the whole `--eval`, double for JS
  strings inside.
- `countDocuments({})` is accurate. `count()` is deprecated and can be an
  estimate.
- `_id` here is a string, not an ObjectId. Match it as a plain string.
- MongoDB holds metadata only. The parsed archive is msgpack files on disk,
  read through NOMAD, not from Mongo. See `nomad-concepts.md`.
- This project pins `mongo:7.0` because MongoDB 8.0 aborts on the VM kernel
  (SERVER-121912).

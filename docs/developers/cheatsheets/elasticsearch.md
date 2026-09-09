# Elasticsearch cheat sheet

Reference for the NOMAD search index. You asked for working proficiency, so
this goes past inspect-and-debug. Official Query DSL:
https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html.

## What it is

A document store with an **inverted index**: for each term it keeps the list of
documents containing it, so text and keyword lookups are fast. NOMAD writes one
document per entry into the index `nomad_oasis_entries_v1`. The Explore UI and
its filter chips are Elasticsearch queries and aggregations.

## Documents, fields, mappings

- A **document** is JSON. Its `_id` in this index equals the NOMAD entry id.
- A **field** has a type set by the **mapping**. The two that matter:
  - `keyword`: stored verbatim, use for exact match, sorting, aggregations.
  - `text`: analyzed into tokens, use for full-text `match`, not for exact
    match or aggregations.
- NOMAD also indexes custom schema quantities dynamically under
  `search_quantities`, addressed as
  `data.<name>#<section-qualified-name>`.

Inspect the mapping:

```
docker compose exec -T elastic curl -s \
  "localhost:9200/nomad_oasis_entries_v1/_mapping" | python3 -m json.tool | less
```

## Talking to it

All queries in this stack go through the container:

```
docker compose exec -T elastic curl -s "localhost:9200/<path>" \
  -H 'Content-Type: application/json' -d '<json body>'
```

| Path | Purpose |
|---|---|
| `/_cat/indices?v` | List indices, doc counts, size |
| `/<index>/_count` | Count, optional query body |
| `/<index>/_doc/<id>` | Fetch one document by id |
| `/<index>/_search` | Query and aggregate |
| `/<index>/_mapping` | Field types |

## Query DSL, with SQL alongside

Body shape: `{ "query": {...}, "aggs": {...}, "size": N, "_source": [...] }`.
`size: 0` returns no hits, use it for pure aggregations.

| Goal | Elasticsearch | SQL |
|---|---|---|
| exact match | `{"term": {"entry_type": "GrillAttempt"}}` | `WHERE entry_type = 'GrillAttempt'` |
| one of many | `{"terms": {"entry_type": ["A","B"]}}` | `WHERE entry_type IN ('A','B')` |
| range | `{"range": {"grill_temp": {"gte": 200}}}` | `WHERE grill_temp >= 200` |
| full text | `{"match": {"entry_name": "salmon pan"}}` | `WHERE entry_name LIKE ...` roughly |
| AND | `{"bool": {"filter": [c1, c2]}}` | `c1 AND c2` |
| OR | `{"bool": {"should": [c1, c2], "minimum_should_match": 1}}` | `c1 OR c2` |
| NOT | `{"bool": {"must_not": [c1]}}` | `NOT c1` |
| everything | `{"match_all": {}}` | no `WHERE` |

`bool` clause types: `must` (AND, scored), `filter` (AND, not scored, cacheable,
prefer this), `should` (OR), `must_not` (NOT).

## Aggregations, with SQL alongside

| Goal | Elasticsearch | SQL |
|---|---|---|
| count per value | `{"terms": {"field": "entry_type"}}` | `GROUP BY entry_type` |
| numeric buckets | `{"histogram": {"field": "grill_temp", "interval": 20}}` | `GROUP BY floor(grill_temp/20)` |
| time buckets | `{"date_histogram": {"field": "upload_create_time", "calendar_interval": "day"}}` | `GROUP BY date_trunc('day', ...)` |
| min max avg sum | `{"stats": {"field": "grill_temp"}}` | `SELECT min(...), max(...), avg(...)` |
| distinct count | `{"cardinality": {"field": "entry_type"}}` | `COUNT(DISTINCT entry_type)` |
| nested sub-group | put an `aggs` inside a `terms` agg | `GROUP BY a, b` |

Example, count entries by type with the earliest upload time each:

```
docker compose exec -T elastic curl -s "localhost:9200/nomad_oasis_entries_v1/_search" \
  -H 'Content-Type: application/json' -d '{
    "size": 0,
    "aggs": {
      "by_type": {
        "terms": { "field": "entry_type" },
        "aggs": { "earliest": { "min": { "field": "upload_create_time" } } }
      }
    }
  }' | python3 -m json.tool
```

## NOMAD-specific fields

| Field | Meaning |
|---|---|
| `entry_id` | matches Mongo `entry._id` |
| `entry_type` | the section name, for example `GrillAttempt` |
| `upload_id`, `upload_name`, `upload_create_time` | the upload |
| `published` | `false` for unpublished, visible only to the owner |
| `section_defs.definition_qualified_name` | nested, used by app `filters_locked` |
| `search_quantities[].id` | `data.<name>#<qualified-name>`, dynamic schema quantities |

Query the nested `section_defs`:

```
docker compose exec -T elastic curl -s "localhost:9200/nomad_oasis_entries_v1/_search" \
  -H 'Content-Type: application/json' -d '{
    "size": 0,
    "query": { "nested": { "path": "section_defs", "query": {
      "term": { "section_defs.definition_qualified_name":
        "nomad_econversion_plugins.schema_packages.grill.GrillAttempt" } } } }
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['hits']['total'])"
```

## Gotchas

- `term` on a `text` field usually returns nothing. Use `match`, or target the
  `.keyword` sub-field if the mapping has one.
- Aggregations need `keyword`, `date`, or numeric fields, not `text`.
- `size: 0` when you only want aggregations, otherwise you also pull 10 hits.
- A nested field (`section_defs`) needs a `nested` query, a plain `term` on it
  silently matches nothing.
- The anonymous NOMAD API filters to `published: true`. Query Elasticsearch
  directly to see unpublished entries.
- Counts here can briefly exceed MongoDB during processing or after a failed
  delete. Reconcile with the Mongo count.

# How Nexus mirrors NOMAD Oasis

Nexus is a small demo built for a keynote. It reproduces a handful of design
patterns from NOMAD Oasis in a cooking domain, so an abstract research-data
idea becomes something you can click through in a few minutes. It is not a fork
of NOMAD and shares no code with it.

## What NOMAD Oasis is

NOMAD is a platform from the materials-science community for storing, describing,
and searching research data. An "Oasis" is a self-hosted NOMAD instance that a
group or institution runs on its own hardware.

The part Nexus borrows: in NOMAD you do not change the core application to
support a new kind of data. You add a schema that declares the fields for that
data type, and the rest of the system (the entry forms, the search facets, the
API) adapts to it. Data structure is configuration, not code.

## What Nexus is

A FastAPI + PostgreSQL service that stores "recipe attempt" entries whose fields
are defined by YAML schema files, plus a server-rendered web UI that browses and
analyses those entries generically from the same schemas. A companion app,
`e-kitchen` (repo `demo-oasis-virtualkitchen`), plays the role of an instrument:
it reads the schemas over HTTP and pushes generated experiments in through the
API.

In the keynote this pair is introduced as "Cooking Oasis". The running services
are named Nexus (the platform) and e-kitchen (the instrument); "Oasis" is not
used in the app itself.

## Concept mapping

| NOMAD Oasis | Nexus | Where |
|---|---|---|
| Metainfo: the schema/data-model layer | YAML schema files | `schemas/*.yaml` |
| A schema plugin that registers a new data type | Adding one YAML file, no code change | drop a file in `schemas/` |
| Section inheritance (`base_sections`) | The `extends:` key | `schemas/fermentation_wine.yaml` etc. |
| Quantities with type, shape, unit | Fields with `type`, `required`, `enum`, list `item` | any schema file |
| Schema introspection over the API | `GET /schemas` | `api/routers/schemas.py` |
| ELN: structured data entry generated from a schema | e-kitchen's guided form, built from `GET /schemas` | `demo-oasis-virtualkitchen/web/` |
| An upload / instrument feeding data in | e-kitchen calling `POST /entries` | `demo-oasis-virtualkitchen/client.py` |
| Entry / archive record | A stored entry | `GET /entries/{id}` |
| Faceted search across heterogeneous entries | The `/explore` tree and filter chips, derived from schema fields | `web/render.py` |
| Overview and analysis views | The `/analysis` dashboard | `web/render.py`, `web/templates/analysis.html` |
| An Oasis: one self-hosted instance | The whole docker-compose stack behind one domain | `docker-compose.yml`, `deploy/Caddyfile` |

## The three keynote stories, concretely

The talk uses three historical stories. Each one points at a feature you can
show in Nexus.

**Faraday's diary: the record matters as much as the result.**
Faraday logged around 30,000 experiments over four decades, successes and
failures alike, and marked which ones became published results. The published
paper was a thin slice of the full record.
In Nexus, every attempt is a stored entry with all of its conditions attached:
the temperature, the method, the ingredients, the outcome. Open any entry at
`/entries/{id}` and you see the whole record, not just a headline number. The
web UI is styled as a "Field Journal" for this reason.

**Mendeleev's table: structuring scattered data unlocks prediction.**
Many chemists had measured atomic weights independently. Mendeleev's move was to
organise that scattered, disagreeing data into one common structure, which made
the gaps visible and let him predict three unknown elements.
In Nexus the entries arrive from different "benches" (fermentation, grilling)
and originally from different code paths, yet they share one base schema. The
`/analysis` page runs a regression fit and a correlation heatmap across them,
which is only possible because the fields are declared and comparable.

**Whitworth's screw thread: standards create collective capability.**
Before 1841 every workshop cut screws to its own profile, so parts from
different makers did not fit. A single standardised thread let the Royal Navy
assemble engines from parts sourced across suppliers.
In Nexus the base schema plus `extends` is the thread, and `GET /schemas` is how
a separate program (e-kitchen) reads that standard and produces data the
platform accepts, with no shared code and no manual coordination.

**Kepler and Brahe's locked cabinet: structure is what makes data usable by a machine.**
The talk's later point is that an AI agent facing an unlabelled folder of files
is locked out the way Kepler was locked out of Brahe's data.
A Nexus entry is the opposite case: an agent can call `GET /schemas` to learn
what every field means, then query `GET /entries` and answer a real question
such as "which grilling attempts cleared the safe internal temperature", because
the structure is declared rather than implied.

## What Nexus deliberately does not mimic

Kept out on purpose, to keep the demo small and readable:

- Real authentication. NOMAD uses Keycloak / OIDC; Nexus has only a cosmetic
  nickname cookie, no accounts, no sessions.
- The archive format. NOMAD normalises data into a typed archive (HDF5,
  msgpack); Nexus stores a JSON blob per entry in Postgres.
- Processing. NOMAD runs parsers and normalisers on uploads; Nexus stores
  whatever a schema declares and computes nothing (the outcome formulas live in
  e-kitchen).
- Provenance and workflows. No workflow graphs, no links between entries.
- Federation, versioning, DOIs, and the metainfo unit system.

The point of the demo is the schema-driven core, not feature parity.

# NOMAD concepts cheat sheet

The NOMAD model this distribution builds on. Running version: NOMAD 1.4.3 with
`oasis: true`. Upstream docs: https://nomad-lab.eu/prod/v1/docs/. The team
record is `docs/oasis-adoption-plan.md`.

## What NOMAD is

A platform for storing, describing, and searching research data. You do not
edit its core to add a data type. You add a **schema** that declares the
fields, and the entry forms, the search facets, and the API adapt to it. Data
structure is configuration, not code. An **Oasis** is a self-hosted instance.

## Data model

| Term | Meaning |
|---|---|
| upload | a set of files you submit together |
| mainfile | a file in the upload that a parser claims |
| entry | one data record, produced from one mainfile. An upload yields one or many |
| raw | the uploaded files, unchanged, on disk at `.volumes/fs/staging/<upload_id>/raw/` |
| archive | the parsed, typed representation of an entry. msgpack on disk, read through NOMAD |
| processing | the parse-and-normalize step, run as a Temporal workflow |
| published | `false` means visible only to the owner. The anonymous API shows only `true` |

Read an archive:

```
docker compose exec -T app python3 -c "
from nomad.files import StagingUploadFiles
with StagingUploadFiles('<upload_id>').read_archive('<entry_id>') as a:
    print(a['<entry_id>'].to_dict()['data'])
"
```

## Where data lives

| Data | Storage |
|---|---|
| raw and processed files | bind mount `./.volumes/fs`, uid 1000 |
| entry metadata, upload records, process state | MongoDB, database `nomad_oasis_v1` |
| search index | Elasticsearch, index `nomad_oasis_entries_v1` |
| Temporal state | PostgreSQL, not NOMAD's |

## Metainfo, the schema layer

- **Section**: a class of data. Has a name and quantities. Can inherit from
  `base_sections`.
- **Quantity**: a field. Has `type` (`str`, `np.float64`, `Datetime`, an
  `MEnum`), optional `shape` (`['*']` for an array), optional `unit`, optional
  `description`.
- **Annotations**: extra behaviour. `eln.component` picks the form widget.
  `eln.hide` at section level removes inherited quantities and sub-sections
  from the form.
- Common base sections: `nomad.datamodel.data.EntryData`,
  `nomad.datamodel.metainfo.eln.ELNMeasurement`,
  `nomad.parsing.tabular.TableData`.

ELN component widgets: `StringEditQuantity`, `NumberEditQuantity`,
`EnumEditQuantity` (dropdown), `RadioEnumEditQuantity` (also a dropdown in
1.4.3), `DateTimeEditQuantity`, `RichTextEditQuantity`.

Enum type in YAML: `type: { type_kind: Enum, type_data: [a, b, c] }`.
Enum type in Python: `type=MEnum('a', 'b', 'c')`.

## The customization ladder, cheapest first

1. YAML ELN schema uploaded as data. No rebuild.
2. `tabular_parser` annotations on a `data_file` quantity, for CSV or Excel. No
   rebuild.
3. App entry point or `ui.apps` in `nomad.yaml`. Config only, no rebuild.
4. Python schema-package plugin, pinned by tag, image rebuilt. Versioned and
   shared.
5. Python parser plugin, only when a real file format forces it.

Stay as low on the ladder as the task allows.

## Authoring a schema as YAML

One `.archive.yaml` with two blocks:

```yaml
definitions:
  name: My schema
  sections:
    MySection:
      base_sections: [nomad.datamodel.metainfo.eln.ELNMeasurement, nomad.datamodel.data.EntryData]
      m_annotations:
        eln:
          hide: [lab_id, location]
      quantities:
        temperature:
          type: np.float64
          unit: celsius
          m_annotations: { eln: { component: NumberEditQuantity } }
data:
  m_def: MySection
  # for tabular:
  # data_file: my.csv
```

Upload the `.archive.yaml` alone to register a reusable schema, or with a
`data:` block and a CSV to also create an entry.

Tabular modes:

- **column mode** (`mapping_mode: column`): one entry, each CSV column becomes
  an array quantity.
- **row mode** (`mapping_mode: row`, `file_mode: multiple_new_entries`): the
  first CSV row fills the trigger entry, rows 2..N each become a new entry. N
  rows yield N entries.

Date columns parsed from a table must be `type: str`. `Datetime` arrays fail
with `Shape mismatch` in 1.4.3.

## Promoting to a plugin

A package under `src/<pkg>/schema_packages/` with:

- `grill.py`: `m_package = SchemaPackage()`, then
  `class GrillAttempt(ELNMeasurement, EntryData)` with
  `m_def = Section(a_eln=ELNAnnotation(hide=[...]))` and quantities, then
  `m_package.__init_metainfo__()` at the end.
- `__init__.py`: a `SchemaPackageEntryPoint` subclass and an instance.
- `pyproject.toml`: `[project.entry-points.'nomad.plugin']` mapping a name to
  `<pkg>.schema_packages:<instance>`.

Verify it loaded:

```
curl -s localhost/nomad-oasis/api/v1/info | python3 -c "
import sys, json
d = json.load(sys.stdin)
print([(p['name'], p.get('version')) for p in d['plugin_packages']])
print([e['name'] for e in d['plugin_entry_points'] if e.get('entry_point_type') == 'schema_package'])
"
```

An entry from a packaged schema has a stable `m_def` like
`nomad_econversion_plugins.schema_packages.grill.GrillAttempt`. An entry from an
uploaded YAML schema has a per-upload `m_def` like
`entry_id:<id>.GrillAttempt`. Only the stable form is usable in app config.

See `uv-packaging.md` for the build loop.

## Search quantities

NOMAD 1.4.3 indexes custom schema quantities dynamically, with no
`a_elasticsearch` annotation. Each is addressed as
`data.<name>#<section-qualified-name>`. For a packaged schema the qualifier is
the class path. List them from an entry document:

```
docker compose exec -T elastic curl -s "localhost:9200/nomad_oasis_entries_v1/_search" \
  -H 'Content-Type: application/json' -d '{"query":{"match":{"entry_type":"GrillAttempt"}},"size":1}' \
  | python3 -c "import sys,json; [print(sq['id']) for sq in json.load(sys.stdin)['hits']['hits'][0]['_source'].get('search_quantities',[])]"
```

## Apps, `ui.apps` in `nomad.yaml`

An app is a focused search page: a locked query, chosen columns, a trimmed
filter menu, a dashboard. Model fields on `nomad.config.models.ui.App`:

| Field | Purpose |
|---|---|
| `label`, `path`, `category` | name, URL segment, explore-menu group |
| `filters_locked` | a fixed query, for example `{section_defs.definition_qualified_name: <class path>}` |
| `columns` | list of `{search_quantity, title, selected}` |
| `menu.items` | `type: terms` uses `search_quantity`; `type: histogram` uses `x` |
| `dashboard.widgets` | `type: terms` or `histogram`, each needs a `layout` per breakpoint (`sm md lg xl xxl`) |

`ui.apps` is marked deprecated in 1.4.3 but works. The stock apps (Entries,
Calculations, ELN) are plugin entry points served by
`GET /api/v1/apps/entry-points`; the GUI merges them with `ui.apps.options`, so
defining your own does not remove them.

Validate before applying:

```
docker compose cp configs/nomad.yaml app:/tmp/x.yaml
docker compose exec -T app python3 -c "
import yaml
from nomad.config.models.ui import UI
UI(**yaml.safe_load(open('/tmp/x.yaml'))['ui'])
print('OK')
"
docker compose up -d --no-deps --force-recreate app worker
```

## Parser matching, short version

On upload, NOMAD runs `match_parser` on every file: filename regex, MIME type,
head-content regex, optional structural checks, in parser `level` order. The
first match becomes a mainfile. This image has only `parsers/tabular`,
`parsers/archive` (matches `*.archive.{json,yaml,yml}` by name), and
`parsers/broken`. A real instrument format needs a parser plugin. Full detail
is in the Phase 5 section of the adoption plan.

## API surface

| Path | Returns |
|---|---|
| `/nomad-oasis/alive` | liveness string |
| `/nomad-oasis/api/v1/info` | version, plugins, parsers, entry points |
| `/nomad-oasis/api/v1/entries` | published entries only without a token |
| `/nomad-oasis/api/v1/apps/entry-points` | the stock apps |
| `/nomad-oasis/gui/env.js` | the GUI config, including `ui.apps.options` |

## Auth and config

- Login goes to the central `nomad-lab.eu` Keycloak because
  `oasis.uses_central_user_management: true`. No local identity service.
- `configs/nomad.yaml` holds hostname, base path, DB and index names, the `ui:`
  block, and auth. It is bind-mounted into `app` and `worker`. Apply a change
  with `docker compose up -d --no-deps --force-recreate app worker`, not a
  plain `restart`.
- GUI branding: `ui.theme.title` sets the tab name. Logos are files under the
  GUI static folder, replaceable by bind mount. The landing page is redirected
  in nginx. See `nginx.md` and the Phase 4 branding note.

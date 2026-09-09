# Lab 2: a data type as a YAML ELN schema

Reproduces Phase 2 of `docs/oasis-adoption-plan.md`.

By the end you will have written an ELN schema as YAML, uploaded it, generated
a form from it, created an entry, and verified the saved archive. You will also
try row mode, where one table creates many entries.

Modules exercised: 2 YAML, 8 schemas.

Time: 2 to 4 hours. Prerequisite: Lab 1 done.

## Background

An ELN schema declares a section and its quantities. NOMAD generates a data
entry form from it. The schema is uploaded as data, so iteration takes minutes
with no image rebuild. This is the cheapest rung of the customization ladder.

Read first: `examples/grill-attempt/grill_attempt.archive.yaml` and the Phase 2
notes in the adoption plan.

## 1. Read the reference schema

```
cd ~/labs/oasis-lab0
less examples/grill-attempt/grill_attempt.archive.yaml
```

Points to notice:

- `base_sections:` lists `nomad.datamodel.metainfo.eln.ELNMeasurement` and
  `nomad.datamodel.data.EntryData`. The section inherits their quantities.
- `m_annotations.eln.hide` at the section level hides inherited quantities and
  inherited sub-sections you do not want on the form
  (`lab_id`, `location`, `steps`, `samples`, and so on).
- Each quantity has a `type`, an optional `unit`, and
  `m_annotations.eln.component`, the form widget.
- Enum syntax is
  `type: { type_kind: Enum, type_data: [red_meat, poultry, fish] }`.
  `EnumEditQuantity` renders a dropdown. `RadioEnumEditQuantity` also renders
  as a dropdown in this version.
- Date quantities are `type: str`, per the Phase 1 finding.

## 2. Upload the schema

1. GUI, Publish, Uploads, "Create a new upload".
2. Drop `examples/grill-attempt/grill_attempt.archive.yaml` on its own.
3. It processes into one entry of type `Schema`. That entry is the schema
   itself, not data.

## 3. Create an entry from the schema

1. In the upload, use the button **Create from schema**. The label is not
   "Create entry".
2. Pick the `GrillAttempt` section. The picker lists every section you have
   ever uploaded, so check the source file name.
3. The generated form appears: text fields, number fields with units, enums as
   dropdowns, and none of the hidden inherited fields.
4. Fill a few values and Save.

## 4. Verify the saved archive

```
docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '
db.entry.find({entry_type:"GrillAttempt"}, {_id:1, upload_id:1}).forEach(e => printjson(e))'
```

Take the entry id `EN` and its upload id `UP`, then:

```
docker compose exec -T app python3 -c "
from nomad.files import StagingUploadFiles
with StagingUploadFiles('UP').read_archive('EN') as arch:
    d = arch['EN'].to_dict()
print('m_def:', d['data']['m_def'])
print('data:', {k:v for k,v in d['data'].items() if not k.startswith('m_')})
"
```

`m_def` is a per-upload reference like
`entry_id:<id>.GrillAttempt`. That is the point of Lab 3: promoting the schema
gives it a stable package reference instead.

## 5. Row mode: one table, many entries

```
less examples/grill-attempt/grill_attempt_table.archive.yaml
```

Differences from column mode:

- `mapping_mode: row` and `file_mode: multiple_new_entries` in the
  `tabular_parser` annotation.
- The section quantities are scalars, not arrays.

Upload `grill_attempt_table.archive.yaml` together with its CSV. Result: the
first CSV row fills the trigger entry itself, and rows 2 to N each become a new
entry named `<label>_<idx>.<Section>.archive.yaml`. N rows produce N entries.

```
docker compose exec -T mongo mongosh nomad_oasis_v1 --quiet --eval '
db.entry.countDocuments({entry_type:"GrillAttemptRow"})'
```

## 6. Verification checklist

- [ ] The schema upload produced an entry of type `Schema`.
- [ ] "Create from schema" generated a form with enums as dropdowns and hidden
  fields absent.
- [ ] The saved archive `data` block matches what you typed.
- [ ] Row mode produced one entry per CSV row.

## Challenge

No walkthrough.

1. Write a new schema file `my_bench.archive.yaml` from scratch, not by copying
   the grill file. Section `BenchRun` on `ELNMeasurement` and `EntryData`, with
   exactly five quantities: one `str`, one `str` date, one `MEnum` with three
   options, one `np.float64` with a `unit` and a `NumberEditQuantity`, and one
   `np.float64` with no unit. Hide at least two inherited fields.
2. Upload it, create an entry from it, save values, and read the archive back
   to confirm every quantity round-tripped.
3. Add one quantity to the schema file, re-upload the file, create a second
   entry, and confirm the new quantity is on the form. Note how long this
   iteration took with no rebuild. You will compare that to Lab 3.

## Troubleshooting

- **Schema upload fails.** Almost always YAML indentation, or an enum written
  without the `type_kind`/`type_data` shape. Run the file through a YAML
  linter first.
- **A quantity does not appear on the form.** It has no
  `m_annotations.eln.component`, or the section-level `hide` list names it.
- **"Create from schema" lists many sections.** Uploaded schemas are visible
  across all uploads. Match the section to its source file name.

## Where this maps in the record

- `oasis-adoption-plan.md`, "Phase 2" and "Phase 2 notes".

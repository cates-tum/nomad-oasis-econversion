# grill-attempt

Phase 2. One grilling attempt as a NOMAD **ELN schema** with a generated edit
form. Ported from the Nexus `grill_red_meat` / `grill_poultry` / `grill_fish`
schemas plus `base_recipe_attempt`, collapsed into one `GrillAttempt` section
with a `protein_class` selector.

## Files

- `grill_attempt.archive.yaml` schema only, no `data:` block. Upload it, then
  create an entry from it through the GUI form.

## Section GrillAttempt

Base sections: `nomad.datamodel.metainfo.eln.ELNMeasurement` (gives `name`,
`datetime`, `description`, and the ELN form machinery) and
`nomad.datamodel.data.EntryData` (makes it a top-level entry type).

Hidden inherited fields (`m_annotations.eln.hide`): `lab_id`, `location`,
`method`, `tags`, and the sub-sections `steps`, `samples`, `instruments`,
`measurement_identifiers`.

Own quantities:

| quantity | type | unit | component |
|---|---|---|---|
| cuisine | str | | StringEditQuantity |
| protein_class | enum (red_meat, poultry, fish, vegetable) | | EnumEditQuantity |
| cut | str | | StringEditQuantity |
| heat_source | enum (grill, pan, oven) | | RadioEnumEditQuantity |
| grill_temp | float | celsius | NumberEditQuantity |
| cook_time | float | minute | NumberEditQuantity |
| internal_temp | float | celsius | NumberEditQuantity |
| usda_safe_min | float | celsius | NumberEditQuantity |
| rested_min | float | minute | NumberEditQuantity |
| doneness | enum (rare .. well_done, not_applicable) | | EnumEditQuantity |
| char_level | float (0-100) | | NumberEditQuantity |
| juiciness_score | float (0-100) | | NumberEditQuantity |
| outcome | enum (undercooked, perfect, overcooked) | | RadioEnumEditQuantity |

## How to use

1. Upload `grill_attempt.archive.yaml` to a new upload.
2. In the upload, use **CREATE ENTRY** (or the "+" on Processed data), pick the
   `GrillAttempt` schema, name the entry.
3. Fill the generated form. Enum fields are dropdowns or radio buttons, number
   fields accept a unit.
4. Save. The entry's Data tab shows the filled section.

## Next in Phase 2

Row-mode tabular variant: a schema with a `data_file` quantity and
`tabular_parser` in `mapping_mode: row`, `file_mode: multiple_new_entries`, so
each row of `../grill-sessions/grill_sessions.csv` becomes its own
`GrillAttempt` entry.

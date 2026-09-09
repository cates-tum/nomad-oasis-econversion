# grill-sessions

Twelve grill sessions, cooking domain, chosen to preview the Nexus grill
"attempt" that Phase 2 ports into a real ELN schema.

## Files

- `grill_sessions.csv` header plus 12 rows.
- `grill_sessions.archive.yaml` one file holding both the schema
  (`definitions:`) and one data instance (`data:`).

## Columns

| Column | Type | Unit | Notes |
|---|---|---|---|
| session_id | str | | GS-001 .. GS-012 |
| date | str | | ISO date. Kept as str: Datetime array columns did not convert cleanly through the tabular parser (shape mismatch). |
| protein | str | | beef, pork, chicken, fish, vegetable |
| grill_temp_c | float | celsius | grill surface temperature |
| cook_time_min | float | minute | |
| internal_temp_c | float | celsius | final internal temperature, 0 for the vegetable row |
| rested_min | float | minute | rest time after cooking |
| outcome | str | | undercooked, perfect, overcooked |

## What processing should produce

Column mode, `file_mode: current_entry`: NOMAD creates **one** entry of section
`GrillSessions`. Each CSV column is read into the matching array quantity on
that entry (`shape: ['*']`). So `grill_temp_c` becomes a length-12 array with
unit celsius, and so on. No child entries.

Check on the entry page:
- Files tab: `grill_sessions.csv` and `grill_sessions.archive.yaml` as raw files.
- Data tab: the `GrillSessions` section with eight array quantities filled.

## Phase 2 plan for this dataset

Add a row-mode variant: `mapping_mode: row`, `file_mode: multiple_new_entries`,
scalar quantities, so each row becomes its own entry. Then grow the schema
toward the Nexus grill attempt (base sections from
`nomad.datamodel.metainfo.eln`, ELN component widgets, hidden inherited fields).

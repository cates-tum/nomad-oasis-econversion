# app-test entries

Four data-only `.archive.yaml` entries of the promoted package schema
`nomad_econversion_plugins.schema_packages.grill.GrillAttempt` (plugin repo
`cates-tum/nomad-econversion-plugins`, pinned `v0.1.0`). Fixture for the
Phase 4 custom app "Grill Attempts".

Each file has no `definitions:` block; `data.m_def` points at the installed
package class, so the archive parser creates one `GrillAttempt` entry per file
and every entry shares the stable package qualified name (unlike the Phase 2
YAML entries, whose section is per-upload).

Spread of values so the app columns and dashboard widget show variety:

| file | protein_class | heat_source | outcome |
|---|---|---|---|
| ribeye_grill | red_meat | grill | perfect |
| chicken_thigh_grill | poultry | grill | undercooked |
| salmon_fillet_pan | fish | pan | perfect |
| zucchini_oven | vegetable | oven | overcooked |

## Upload

Zip the four files and upload via the GUI (Publish > New upload > drop the zip),
or drop them individually. No rebuild. They process with `parsers/archive`.

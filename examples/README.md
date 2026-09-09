# examples

Hand-built example datasets for the adoption phases. The shipped NOMAD example
uploads are not bundled in this image, so we keep our own here.

## Layout

One folder per dataset:

```
examples/
  <dataset-name>/
    <name>.archive.yaml   schema (definitions) plus a data instance, one file
    <name>.csv            the tabular data
    notes.md              what the dataset is, its columns, expected result
```

## How to load one (GUI)

1. http://localhost/nomad-oasis/gui/user/uploads > CREATE A NEW UPLOAD
2. Drag both files of a dataset folder into the drop zone.
3. NOMAD sees the `data:` block in the `.archive.yaml`, creates one entry, and
   runs the tabular parser on the CSV automatically. No extra clicks.
4. Watch the upload's processing status, then open the entry.

## Datasets

| Folder | Phase | Parser mode | Result |
|---|---|---|---|
| `grill-sessions` | 1 | tabular, column mode | one entry, each CSV column becomes an array quantity |

Phase 2 will add a row-mode variant of `grill-sessions` (one entry per row) and
port it toward the Nexus grill "attempt" schema.

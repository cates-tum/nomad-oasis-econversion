# YAML cheat sheet

Reference for editing `configs/nomad.yaml`, `docker-compose.yaml`, and the
workflow file. https://learnxinyminutes.com/docs/yaml/.

## Core syntax

```yaml
# a comment
key: value                 # a scalar
nested:
  child: value             # indentation is 2 spaces, never tabs
list:
  - first
  - second
inline_list: [a, b, c]
inline_map: { x: 1, y: 2 }
multiline_literal: |        # keeps newlines
  line one
  line two
multiline_folded: >         # folds newlines into spaces
  this becomes
  one long line
```

Indentation defines structure. Two spaces per level in these files. Tabs are a
syntax error.

## Quoting rules

Unquoted scalars are type-guessed. This bites you:

| Written | Parsed as | Force a string with |
|---|---|---|
| `yes`, `no`, `on`, `off`, `true`, `false` | boolean | `"yes"` |
| `3.12` | float | `"3.12"` |
| `010` | may be int | `"010"` |
| `null`, `~` | null | `"null"` |
| `2026-09-09` | date | `"2026-09-09"` |

In `docker-compose.yaml`, `PYTHON_VERSION: "3.12"` is quoted so it does not
become the float `3.12`. In this repo's workflow, `JUPYTER_VERSION: "2025-04-14"`
is quoted so it is not parsed as a date.

Strings with `:` followed by a space, or starting with `@`, `` ` ``, `[`, `{`,
`!`, `#`, need quotes.

## Block scalars

- `|` literal: keep every newline. Use for shell scripts, READMEs, SQL.
- `>` folded: newlines become spaces, blank lines become one newline. Use for
  long prose that should wrap.
- `|-` and `>-` strip the final newline.

The `readme:` field in a NOMAD app and the `run: |` step in a workflow both use
`|`.

## Anchors and aliases

```yaml
defaults: &defaults
  restart: unless-stopped
service_a:
  <<: *defaults
  image: a
```

`&name` defines an anchor, `*name` reuses it, `<<:` merges a map. You will see
this in some compose files. This repo's compose file does not lean on it.

## Multiple documents

`---` separates documents in one file. Kubernetes manifests use this. NOMAD and
Compose files are single-document.

## Validate before you apply

Fastest check, does it parse:

```
python3 -c "import yaml, sys; yaml.safe_load(open('configs/nomad.yaml')); print('parses')"
```

Check it against the program's model, better:

```
docker compose config --quiet && echo "compose OK"
```

```
docker compose cp configs/nomad.yaml app:/tmp/x.yaml
docker compose exec -T app python3 -c "
import yaml
from nomad.config.models.ui import UI
UI(**yaml.safe_load(open('/tmp/x.yaml'))['ui'])
print('nomad ui OK')
"
```

## Common breakages

| Symptom | Cause |
|---|---|
| `found character '\t' that cannot start any token` | a tab |
| a value is `True` when you wrote `yes` | unquoted boolean-like string |
| `mapping values are not allowed here` | a `:` in an unquoted string, or bad indent |
| a list item ignored | `-` not aligned with its siblings |
| whole block ignored by the program | indented one level too deep or too shallow |
| version parsed as a number | unquoted `3.12` or `2025-04-14` |

## Gotcha specific to this repo

Editing `configs/nomad.yaml` or `configs/nginx_base_conf` and running
`docker compose restart` may not take effect. The file is bind-mounted and the
save changed its inode. Use
`docker compose up -d --no-deps --force-recreate <service>`. See
`docker-compose.md`.

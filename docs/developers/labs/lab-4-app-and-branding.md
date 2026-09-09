# Lab 4: a custom app and GUI branding

Reproduces Phase 4 of `docs/oasis-adoption-plan.md`.

By the end you will have added a search app scoped to one schema, learned to
validate config against the model before applying it, and rebranded the GUI
with a custom title, a landing redirect, and replacement logo files. All of it
is config and bind mounts, no image rebuild.

Modules exercised: 10 ui.apps, 11 nginx.

Time: 3 to 4 hours. Prerequisite: Lab 3 done, packaged schema loaded, and a few
entries of the packaged `GrillAttempt` in the stack.

## Part A: the custom app

### A1. Look at the model, not the docs

The app config is validated by a pydantic model. Read the fields:

```
docker compose exec -T app python3 -c "
import inspect
from nomad.config.models.ui import App
print(inspect.getsource(App))
" | head -60
```

Key fields: `label`, `path`, `category`, `columns`, `menu`, `dashboard`,
`filters_locked`.

### A2. Find the searchable quantity ids

Custom schema quantities are indexed dynamically. Fetch one packaged
`GrillAttempt` entry and list them:

```
docker compose exec -T elastic curl -s "localhost:9200/nomad_oasis_entries_v1/_search" \
  -H 'Content-Type: application/json' -d '{
    "query": { "match": { "entry_type": "GrillAttempt" } }, "size": 1
  }' | python3 -c "
import sys, json
h = json.load(sys.stdin)['hits']['hits'][0]['_source']
for sq in h.get('search_quantities', []):
    print(sq['id'])
"
```

The ids look like
`data.protein_class#nomad_econversion_plugins.schema_packages.grill.GrillAttempt`.
That full string is what columns, menu items, and widgets reference. There is
no `a_elasticsearch` annotation needed for this in NOMAD 1.4.3.

### A3. Add the app block

Edit `configs/nomad.yaml`. Under `ui:` add an `apps.options` entry. Minimal
shape:

```yaml
ui:
  apps:
    options:
      my_grill:
        label: My Grill Attempts
        path: my-grill
        category: Use Cases
        filters_locked:
          section_defs.definition_qualified_name: nomad_econversion_plugins.schema_packages.grill.GrillAttempt
        columns:
          - search_quantity: entry_name
            selected: true
          - search_quantity: data.protein_class#nomad_econversion_plugins.schema_packages.grill.GrillAttempt
            title: Protein class
            selected: true
        menu:
          items:
            - type: terms
              search_quantity: data.protein_class#nomad_econversion_plugins.schema_packages.grill.GrillAttempt
              title: Protein class
              width: 12
            - type: histogram
              x: data.grill_temp#nomad_econversion_plugins.schema_packages.grill.GrillAttempt
              title: Grill temp
              width: 12
        dashboard:
          widgets:
            - type: terms
              title: Outcome
              search_quantity: data.outcome#nomad_econversion_plugins.schema_packages.grill.GrillAttempt
              layout:
                lg: { h: 6, w: 6, x: 0, y: 0 }
```

Note the histogram menu item uses `x:`, not `search_quantity:`. That key is
rejected on a histogram menu item.

### A4. Validate before applying

Never recreate the container on an unvalidated config. A broken file makes
`app` crash-loop.

```
docker compose cp configs/nomad.yaml app:/tmp/new_nomad.yaml
docker compose exec -T app python3 -c "
import yaml
from nomad.config.models.ui import UI
ui = UI(**yaml.safe_load(open('/tmp/new_nomad.yaml'))['ui'])
app = ui.apps.options['my_grill']
print('OK:', app.label, app.path, '| columns', len(app.columns), '| widgets', len(app.dashboard.widgets))
"
```

Fix any pydantic error it prints before continuing.

### A5. Apply and check

```
docker compose up -d --no-deps --force-recreate app worker
```

`restart` alone would not pick up the edited file, because saving the file
changed its inode and the container still points at the old one. `--force-recreate`
re-resolves the bind mount. See `../cheatsheets/docker-compose.md`.

Verify the app is in the GUI config:

```
curl -s "localhost/nomad-oasis/gui/env.js" | python3 -c "
import sys, re, json
env = json.loads(re.search(r'window\.nomadEnv\s*=\s*(\{.*\})', sys.stdin.read(), re.S).group(1))
print(list(env['ui']['apps']['options'].keys()))
"
```

Open the GUI, Explore menu, category Use Cases, your app. Confirm the locked
filter, the columns, the menu, and the dashboard widget.

## Part B: branding

Only three things are adjustable without forking the GUI: the browser tab
title, which page you land on, and the logo image files.

### B1. Title

In `configs/nomad.yaml`:

```yaml
ui:
  theme:
    title: My Oasis
```

Validate and apply as in A4 and A5.

### B2. Land on the app, not the About page

The landing route is hardcoded to About. Redirect it in nginx. Edit
`configs/nginx_base_conf`, add before the `location /nomad-oasis/gui/` block:

```
location = /nomad-oasis/gui/ {
    return 302 /nomad-oasis/gui/search/my-grill;
}
```

`location =` is an exact match, highest priority, so only the bare GUI root
redirects. Deeper routes and assets fall through to the prefix block.

Recreate the proxy:

```
docker compose up -d --no-deps --force-recreate proxy
```

Test without a browser:

```
curl -s -o /dev/null -D - "http://localhost/nomad-oasis/gui/" | grep -i '^location:'
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost/nomad-oasis/gui/search/my-grill"
```

First should be a 302 to your app. Second should be 200.

### B3. Replace the logo files

The GUI copies its static folder into `run/gui_configured` on every `app`
start, so a bind mount must sit on the **source** path, not the served copy.

Files and sizes: `nomad-text.png` 621x111 (loading screen), `nomad-oasis.png`
512x512 (About page), `nomad.png` 512x512 (nav bar), `favicon.png` 128x126,
`favicon-hres.png` 512x512, `favicon.ico`.

Generate placeholders:

```
python3 scripts/make-branding.py
ls configs/branding/
```

Add read-only mounts to the `app` service in `docker-compose.yaml`, one per
file, target
`/opt/venv/lib/python3.12/site-packages/nomad/app/static/gui/<file>`. Then:

```
docker compose config --quiet && echo compose OK
docker compose up -d --no-deps --force-recreate app
```

Verify the served bytes match your files:

```
for f in nomad-text.png nomad-oasis.png favicon.ico; do
  a=$(curl -s "http://localhost/nomad-oasis/gui/$f" | md5sum | cut -d' ' -f1)
  b=$(md5sum "configs/branding/$f" | cut -d' ' -f1)
  echo "$f $([ "$a" = "$b" ] && echo MATCH || echo DIFF)"
done
```

### B4. See it in the browser

The GUI service worker caches assets hard. Use a private window, or in a normal
window unregister the service worker (`about:debugging`, This Firefox, Service
Workers) and clear the site data, then hard reload.

## Verification checklist

- [ ] The app appears in Explore under its category and shows only locked-schema
  entries.
- [ ] You validated the config against the model before recreating anything.
- [ ] `curl` shows the GUI root returning a 302 to your app.
- [ ] Served logo bytes match `configs/branding/`.

## Challenge

1. Add a second app locked to a different `entry_type` (for example
   `GrillSessions`). Validate it against the model without restarting the
   stack, then apply. Confirm both apps show in `env.js`.
2. Add an nginx redirect from `/nomad-oasis/go/grill` to your app. Test it with
   `curl` only. Explain why you used a prefix or exact `location`, and what
   would break if you used a regex `location` here.
3. Change `configs/nomad.yaml` to an invalid `ui.apps` block on purpose (for
   example give a widget no `layout`). Run the A4 validation and read the
   pydantic error. Do not apply it. Fix it.

## Troubleshooting

- **`app` crash-loops after you applied config.** The config is invalid and you
  skipped A4. `docker compose logs app` shows the pydantic error. Fix the file,
  recreate.
- **The app is missing from `env.js`.** Wrong indentation under `ui.apps.options`,
  or you edited the file but ran `restart` instead of `--force-recreate`.
- **The redirect does not fire.** `nginx_base_conf` is included by
  `nginx_http.conf` inside the server block. Confirm the include line is there,
  and that your `location` sits before the `/nomad-oasis/gui/` prefix block.
- **Old logo still shows.** Service worker cache. Private window.

## Where this maps in the record

- `oasis-adoption-plan.md`, "Phase 4", "Phase 4 notes", and "Phase 4
  branding".

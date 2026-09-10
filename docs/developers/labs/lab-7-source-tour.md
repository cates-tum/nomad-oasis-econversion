# Lab 7: read the NOMAD source, trace one upload end to end

New in Tier 4, not a replay of a recorded phase. It turns the Phase 5
"How NOMAD matches a file to a parser" write-up in `oasis-adoption-plan.md`
from something you read into something you can navigate.

By the end you will be able to find the installed NOMAD package inside the
container, navigate it with `grep` and an editor, name the file and function
for parser matching and for the entries query route, and explain why a slow
parser does not freeze the API.

Modules exercised: 14 async and reading the source. Leans on Module 6 (data
model), Module 7 (Temporal), Module 9 (entry points).

Time: 4 to 6 hours, all reading and tracing, almost no typing. Prerequisite:
Labs 1 and 3 done. Read the "How NOMAD matches a file to a parser" section of
`oasis-adoption-plan.md` first.

## 1. Find the code

```
docker compose exec app python -c "import nomad, os; print(os.path.dirname(nomad.__file__))"
docker compose exec app sh -c 'ls $(python -c "import nomad,os;print(os.path.dirname(nomad.__file__))")'
```

For comfortable reading, open the same tree in VS Code. Either
`docker compose cp app:<path> /tmp/nomad-src` to get a copy, or attach VS Code
to the running container with the Dev Containers extension. A copy is simpler
and you will not edit it.

Sketch the top-level layout in your notes: `app/`, `processing/`, `parsing/`,
`metainfo/`, `config/`, `datamodel/`, `normalizing/`, `cli/`.

## 2. The parser match path

Open `nomad/parsing/parsers.py`. Find `match_parser`. Read it against the
five numbered steps in the adoption plan write-up and mark where each one is
in the code:

- the name skip for `.` and `~`
- the first-3-bytes compression check and the `parser_matching_size` head read
- the libmagic MIME detection and UTF-8 decode attempt
- the ordered loop calling `is_mainfile` on each enabled parser
- `strict=True` skipping the artificial parsers

Then find the `MatchingParser` class and list every `is_mainfile` check it
supports (`mainfile_name_re`, `mainfile_contents_re`, `mainfile_mime_re`,
`mainfile_binary_header`, `mainfile_contents_dict`, `supported_compressions`).
Confirm from the code that an unset check is skipped, not failed.

Question: for a file named `x.archive.yaml`, which parser wins and which single
check decides it? Verify with:

```
docker compose exec app python -c \
  "from nomad.parsing.parsers import match_parser; print(match_parser('/tmp/x.archive.yaml'))"
```

(create that file first with `docker compose exec app sh -c 'echo ... > /tmp/x.archive.yaml'`).

## 3. The API route

```
docker compose exec app sh -c 'grep -rn "entries/query\|/query" $(python -c "import nomad,os;print(os.path.dirname(nomad.__file__))")/app/v1/routers/'
```

Open the router file it points to. Find the path operation for the entries
query. Note:

- the decorator: method and path
- the request body type (a Pydantic model) and where that model is defined
- the auth dependency in the signature
- what it calls to actually run the search (an Elasticsearch client call)

Follow one import outward until you reach the Elasticsearch query construction.
You are looking for where the JSON query language from `nomad-api.md` becomes
an Elasticsearch DSL query.

## 4. The config model

The adoption plan says `configs/nomad.yaml`'s `ui.apps` is validated against a
Pydantic model. Find it:

```
docker compose exec app sh -c 'grep -rn "class Apps\|class App\b\|ui:" $(python -c "import nomad,os;print(os.path.dirname(nomad.__file__))")/config/'
```

Name the class. Read its fields and match them to the `ui.apps.options.grill_attempts`
block in `configs/nomad.yaml`. This is why a typo there stops the container
from starting: the model rejects the file at load.

## 5. The async question

Open a router file in `nomad/app/`. Note which path operations are `async def`
and which are plain `def`. Read the FastAPI "Concurrency" page, then answer:

- A plain `def` route doing a blocking Elasticsearch call: what does FastAPI do
  so it does not block the event loop?
- Parsing a 50 MB file takes 10 seconds of CPU. Where does that run, and why is
  it not in the `app` process at all? Trace it: the `app` registers a Temporal
  workflow, the `worker` (`nomad.cli admin run action-internal-worker`) picks
  up the activity. Find the activity function in `nomad/processing/`.

## 6. Trace one real upload

Upload a known-good `.archive.yaml` through the GUI or the API. Then, by
reading code and confirming with logs, write the path from HTTP request to
Elasticsearch document:

1. Which route received the upload (`grep` the uploads router).
2. Where it hands off to processing (`grep` for the workflow start).
3. The workflow and its activities in `nomad/processing/`.
4. Where an activity calls the parser (`match_parser`, then the parser's
   `parse`).
5. Where the result is written to Mongo and to Elasticsearch.

Confirm each hop against `docker compose logs --since 5m app worker`.

## 7. Verification checklist

- [ ] You can open `nomad/parsing/parsers.py` and point to each step of
      `match_parser`.
- [ ] You can name the file and function for the entries query route.
- [ ] You can name the Pydantic class that validates `ui.apps`.
- [ ] You can say where CPU-bound parsing runs and why the API stays
      responsive during it.
- [ ] You have a written 5-hop trace from upload request to ES document, each
      hop tied to a file and a log line.

## Challenge

1. Change one `is_mainfile` check on a throwaway parser config in your head:
   if `mainfile_name_re` were `.*\.yaml$` instead of `.*archive\.yaml$`, which
   other files in a normal upload would suddenly match? Check your reasoning
   against the code.
2. Find one `async def` and one plain `def` route in the same router. Explain
   the practical difference for a caller. Is there one?
3. Pick a small parser plugin from the FAIRmat GitHub org, read its
   `is_mainfile` and `parse`, and describe in three sentences what file it
   claims and what it writes into the archive.

## Troubleshooting

- **`docker compose exec app` fails, no such service.** The app is down.
  `docker compose up -d app`.
- **Import errors when you run a `python -c` snippet.** Run it inside the
  container, not on the host. The host has no `nomad` installed in the labs.
- **The grep finds nothing.** The path moved between NOMAD versions. Widen the
  pattern, or start from `openapi.json`'s `operationId` and grep for that.

## Where this maps in the record

- `oasis-adoption-plan.md`, "How NOMAD matches a file to a parser" in the
  Phase 5 section. This lab is how you verify that write-up against the code.
- Draft status: the grep patterns assume NOMAD 1.4.3 (`nomad-lab==1.4.3` in
  `pyproject.toml`). If a path has moved, fix the pattern here and commit it.

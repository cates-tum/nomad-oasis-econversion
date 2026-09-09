# Developer onboarding

This folder teaches you to reproduce the NOMAD Oasis distribution work in
`docs/oasis-adoption-plan.md` by hand, understanding every step. It exists so a
new developer can reach the same running state without copying commands they do
not understand.

## What is here

| Path | Purpose |
|---|---|
| `learning-plan.md` | The self-study plan: 12 modules in 3 tiers, in order, with concepts, resources, and checkpoints. Start here. |
| `labs/` | Hands-on walkthroughs. Each reproduces one phase of the adoption plan and ends with a challenge. |
| `cheatsheets/` | Command and concept reference per tool. Not tutorials. Look here while you work. |

## How to use it

1. Read `learning-plan.md` top to bottom once, so you know the shape of the
   whole thing.
2. Work the modules in order. Do not skip Tier 1 even if parts feel basic; the
   later tiers assume the Docker and Compose model is solid.
3. Each module points to a lab. Do the lab. Do the challenge at the end without
   looking at the walkthrough.
4. Keep the matching cheat sheet open while you work.
5. When a lab step matches something the team already did, it cites the commit
   or the section of `oasis-adoption-plan.md`. That file is the record of what
   happened; these labs are how you repeat it.

## Prerequisites

You provide the machine and accounts. The labs assume:

- Linux: Ubuntu 22.04 or newer, native or in a VM, or Windows with WSL2.
  The team reference machine is Ubuntu in VirtualBox on a Windows host.
- Docker Engine and the Compose v2 plugin. Check with
  `docker compose version`.
- git 2.30 or newer.
- The GitHub CLI `gh`, logged in (`gh auth status`).
- A GitHub account that can create repositories in the target namespace.
- About 30 GiB free disk and 10 GiB RAM available to the OS running Docker.
- Python 3.12 on the host is optional. `uv` runs in a container in the labs.
- VS Code with the Docker extension is optional but assumed in screenshots.

If any of these is missing, the relevant cheat sheet has install links.

## Scope

Anchored to this project. General Docker, git, and CI knowledge is explained
only as far as these phases needed it. Where a tool has far more surface than
we use (Elasticsearch, Temporal), the cheat sheet says so and links out.

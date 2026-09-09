# git cheat sheet

Reference for the git you need in this repo. Not a tutorial. Deep dive: Pro Git,
https://git-scm.com/book.

## Mental model

Four places a change can be:

1. **Working tree**: your files on disk.
2. **Index** (staging area): what `git add` has marked for the next commit.
3. **Local repository**: commits you have made, on your branch.
4. **Remote** (`origin`): the copy on GitHub, updated by `git push`.

A **commit** is a snapshot plus a parent link. A **branch** is a moving pointer
to a commit. `HEAD` is where you are.

## Everyday commands

| Command | What it does |
|---|---|
| `git status` | What changed, what is staged, what branch |
| `git status --short` | Compact form, `M` modified, `A` added, `??` untracked |
| `git diff` | Unstaged changes |
| `git diff --staged` | Staged changes, what a commit would contain |
| `git add PATH` | Stage a file or directory |
| `git add -A` | Stage everything, including deletions |
| `git restore PATH` | Discard unstaged changes to a file |
| `git restore --staged PATH` | Unstage, keep the change |
| `git commit -m "message"` | Commit the staged changes |
| `git log --oneline -10` | Last 10 commits, one line each |
| `git log --oneline origin/main..HEAD` | Local commits not yet pushed |
| `git show COMMIT` | One commit's message and diff |
| `git pull` | Fetch and merge `origin`'s changes into your branch |
| `git push origin main` | Send local `main` commits to `origin` |
| `git fetch` | Update remote-tracking refs without merging |

## This repo's flow

- Commits go straight to `main`. No PR gate for this prototype repo.
- Commit messages: one plain-English sentence, no `feat:` or `fix:` prefix.
- Every commit in this work carries the trailer lines from the session
  attribution. Match the existing history with `git log`.
- `configs/`, `docs/`, and workflow files are all tracked. `.env`, `.env.north`,
  and other generated files are in `.gitignore`.

Check something is ignored before you commit a new project:

```
git check-ignore .env && echo "ignored, good"
```

## Branches and tags

| Command | What it does |
|---|---|
| `git switch -c my-branch` | Create and switch to a branch |
| `git switch main` | Switch back |
| `git branch -d my-branch` | Delete a merged branch |
| `git tag v0.1.0` | Tag the current commit |
| `git push origin main --tags` | Push commits and tags |
| `git tag` | List tags |

Tags matter here: the plugin repo is pinned by tag
(`git+https://...@v0.1.0`), and the CI image push is gated to `v*.*.*` tags.

## Undo, safely

| Situation | Command |
|---|---|
| Unstage a file | `git restore --staged PATH` |
| Discard a file's uncommitted change | `git restore PATH` |
| Fix the last commit message | `git commit --amend` (only if not pushed) |
| Undo the last commit, keep changes staged | `git reset --soft HEAD~1` |
| Undo the last commit, keep changes unstaged | `git reset HEAD~1` |
| See a file as it was in a past commit | `git show COMMIT:path/to/file` |

Do not `git reset --hard` or `git push --force` on a shared branch without
asking. Both can destroy work that is hard to recover.

## Reading history

```
git log --oneline --graph -20        # branch shape
git log -p -- path/to/file           # a file's full change history
git blame path/to/file               # who last touched each line
git log --since=2026-09-01 --oneline # by date
```

## Gotchas

- `git add` stages a **snapshot**. If you edit the file again after `git add`,
  the new edit is not in the next commit unless you `git add` again.
- `git pull` can create a merge commit. If you have local commits and `origin`
  moved, expect a merge or a rebase prompt.
- An editor that saves by write-and-rename changes a file's inode. That does
  not affect git, but it does affect a running container's bind mount. See
  `docker-compose.md`.
- Deleting a file needs `git add -A` or `git rm` to be staged. A plain
  `git add PATH` on a deleted path does nothing useful.

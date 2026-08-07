# Project Health & Alignment Checklist

Living reference for auditing any project in this family (`trader`, `signal-provider`,
`price-provider`, and future additions). Run this when bringing a project up to par with
the others, before a version tag, or periodically as general hygiene. Pairs with
`coding-conventions.md` — that document covers *how code should be written*, this one
covers *what to systematically check* across a whole codebase, and how to check it safely.

Each section states what to check, why it matters, and the concrete method used — not just
"look for problems" but the actual command/approach that makes the check repeatable.

---

## 1. Crash Resilience

**Check for anything that blocks forever on an unattended process.**
```bash
grep -rn "input(" app/ --include="*.py"
```
`input("Press Enter to exit...")` after a fatal exception is a real, recurring bug pattern —
it reads as "graceful pause before exit" but on a server/service with no attached console it
hangs the process forever: technically alive, doing nothing, no more log lines, invisible
until someone manually kills it. Found and fixed identically in `trader` and
`signal-provider`.

**Every fatal exit point sends an alert before exiting**, not just logs one. A log line
nobody's watching a terminal for is not a notification. Concretely: any `except Exception`
around the run loop, and any startup failure (failed connection, missing required config)
that causes `sys.exit()`, should call the notify manager first.

**A heartbeat file, rewritten every loop iteration, after the real work completes** — not
at the top of the loop. This is the only way to distinguish "the process is alive and making
progress" from "the process is alive but stuck in a blocking call that never raises" — the
second case can't be caught by any amount of internal exception handling, because the code
that would report it has itself stopped running. Written once, read by nothing yet in any of
these three projects — the external watchdog that consumes these is a planned, not yet built,
addition.

---

## 2. Config & Environment Conventions

Cross-check against `coding-conventions.md` §2 specifically:

- `grep -rn "os.getenv\|os.environ" app/ --include="*.py"` — every hit must be inside
  `*/loaders/*.py`. Any hit elsewhere is a violation regardless of how small.
- Every loader function returns a typed dataclass, not a raw `str`/`dict`. A loader named
  `load_database_name() -> str` is a signal to look for the matching dataclass it should be
  returning instead — found and fixed in `signal-provider`.
- `grep -rn "| None" app/ --include="*.py"` — should return nothing; `Optional[X]` is the
  house style, mixed usage is what actually causes confusion (not which one is chosen).
- **`.env.sample`, not `.env.example`.** One project (`price-provider`) had drifted to the
  other name — cosmetic, but it's exactly the kind of inconsistency that makes "which
  project uses which convention" a thing you have to remember instead of just knowing.
- Does `.env.sample` actually contain every variable the loaders read? A loader reading a
  var that's absent from the sample file means new setups silently fall back to defaults
  nobody documented.

---

## 3. `requirements.txt` Accuracy

Never trust it by inspection alone — derive the real answer from the code:

```python
import re
from pathlib import Path

stdlib = {...}  # os, sys, json, logging, pathlib, typing, dataclasses, sqlite3, etc.
third_party = set()
for f in Path('.').rglob('*.py'):
    if '__pycache__' in f.parts:
        continue
    text = f.read_text(errors='ignore')
    for m in re.finditer(r'^\s*(?:from|import)\s+([a-zA-Z0-9_]+)', text, re.MULTILINE):
        mod = m.group(1)
        if mod != 'app' and mod not in stdlib:
            third_party.add(mod)
```

Compare the result against `requirements.txt` line by line (mind the PyPI-name vs.
import-name mismatches: `PyYAML`→`yaml`, `python-dotenv`→`dotenv`, `ctrader-open-api`→
`ctrader_open_api`). Flag both directions:
- **Imported but not listed** — will break on a clean install.
- **Listed but never imported** — found `pytz`, `requests`, and `pytest` unused in `trader`
  (the last because a claimed `tests/` folder didn't actually exist — the README was
  describing aspirational structure as if it were real).

Packages imported only transitively by a listed dependency (e.g. `pyOpenSSL` /
`service_identity` for Twisted's TLS support) are correct to keep even though nothing
imports them directly — don't flag those as unused without checking why they're there.

---

## 4. PEP8, Done Safely

Manual reformatting risks silently changing behavior. The safe sequence:

1. **Baseline**: `pycodestyle --max-line-length=120 --ignore=E402,W503 --statistics -qq`
   across the whole tree. (`E402` is ignored project-wide when imports intentionally follow
   `load_dotenv()` — that's a deliberate ordering, not an oversight, so don't "fix" it.
   `W503` — line break before a binary operator — contradicts current PEP8 guidance itself,
   safe to always ignore.)
2. **Backup first**: copy the whole tree before touching anything.
3. **Conservative `autopep8`** — whitespace/blank-line/spacing codes only, explicitly
   `--select`ed, never `--aggressive`:
   ```bash
   find app -name "*.py" -exec python3 -m autopep8 --in-place --max-line-length=120 \
     --select=E101,E111,E117,E122,E123,E125,E201,E221,E225,E231,E271,E272,E275,E301,E302,E303,E741,W291,W292,W293,W391 \
     {} \;
   ```
4. **Prove nothing changed**, don't just assume it: parse every file before and after with
   `ast.dump(ast.parse(...))` and diff. Any file where the dumps differ needs a manual look —
   in practice this flagged exactly the files with genuine manual edits (an extracted
   variable, a rewrapped multi-line string), never an autopep8 side effect.
5. **Hand-fix what's left** (usually long lines autopep8 won't safely rewrap on its own —
   f-strings, SQL literals, embedded HTML/CSS). Re-run the AST diff after manual edits too.
6. **Final state**: re-run `pycodestyle` — target is zero violations outside the accepted
   `E402`/`W503` exceptions.

A long line inside a triple-quoted HTML/CSS template is safe to wrap with an inserted
newline — browsers and CSS parsers ignore the extra whitespace — but verify by actually
rendering/`.format()`-ing the template after, don't assume.

---

## 5. README Accuracy

A stale README is worse than no README — it actively misleads. Check every factual claim
against the actual code, not against memory of what the project used to be:

- **Status claims** (`"scaffolded"`, `"not yet implemented"`) — grep for
  `NotImplementedError`/`TODO` in the area being described; if there are none, the feature
  is done and the README is lying about it. Found in `trader` (cTrader was fully live, README
  still said "scaffolded, ready for implementation").
- **Run commands** — actually check the path exists. Found in `price-provider`:
  `python run.py` when the real entry point was `app/runtime/run.py`.
- **Project layout diagrams** — compare against a real `find`/`tree` listing. Found in
  `signal-provider`: the README's tree was missing 8 of 12 active providers and several
  whole subsystems (publisher, eval).
- **Referenced filenames** — a rename (e.g. `.env.example` → `.env.sample`) needs a
  find-and-replace across the README too, not just the file itself.

---

## 6. Script/Batch File Naming Consistency

```bash
ls startup/*.bat
```
Look for inconsistency *within* the same file type in the same folder — e.g. `CTrader
deploy.bat` and `MT5 trader deploy.bat` using spaces while `backup_and_deploy_to_production.bat`
used underscores. Spaces in filenames aren't wrong, but they're inconsistent with the rest
and require quoting everywhere they're referenced (deploy scripts, docs) — an easy thing to
miss when renaming, so grep for the old name across the whole tree before considering it
done, not just in the folder it lives in.

---

## 7. Shared-Guideline Drift

`coding-conventions.md` is meant to be the *same document* across every project in the
family. It will drift the moment one project's copy gets updated and the others don't.

```bash
diff project-a/guidelines/coding-conventions.md project-b/guidelines/coding-conventions.md
```
When it drifts, sync forward from whichever copy is most current — don't try to merge by
hand. If a section only makes sense for one project (e.g. a worked example naming that
project's own files), keep it as a named worked example rather than genericizing it away —
concrete examples teach the pattern better than abstract ones, and the other projects can
follow the same pattern under their own names.

---

## 8. Shared Infrastructure (When Multiple Processes Touch the Same Resource)

Only applies once two or more app instances write to the same file/folder (e.g. a shared
`Data\` directory two levels above every instance's own root) — but check for it whenever
that setup exists:

- **SQLite written by more than one process** needs an explicit `timeout=` on every
  `sqlite3.connect()` call, or a lock collision raises immediately instead of waiting it out.
- **Primary keys must include whatever disambiguates the writers** — `(platform, account_id,
  id)`, not bare `id`, if two processes can independently produce the same id (e.g.
  independent per-broker ticket numbering). A bare-`id` PK plus `INSERT OR IGNORE` will
  silently drop a legitimate row from the second writer the moment their id ranges overlap.
- **The shared folder itself is computed relative to the app root, never hardcoded per
  environment** — so the same code, deployed to any instance, resolves to the same physical
  folder without per-deployment configuration.

---

## 9. Typo Sweep

Carried over from `coding-conventions.md` §3, worth repeating here as an explicit check
rather than something to remember informally:

```bash
grep -rn "<suspicious_token>" app/ --include="*.py"
```
A typo copied identically across an interface and every implementation of it passes every
"does this match the pattern" review, because it *does* match — every copy agrees with every
other copy. An occasional literal grep across the whole tree catches what diff review can't.

---

## Quick Checklist

- [ ] No blocking `input()` (or equivalent) after a fatal exception
- [ ] Every fatal exit path sends an alert, not just a log line
- [ ] Heartbeat file written after real work completes, once per loop iteration
- [ ] All `os.getenv()`/`os.environ` confined to `*/loaders/*.py`
- [ ] Every loader returns a typed dataclass; `Optional[X]` used consistently
- [ ] `.env.sample` exists, named consistently, and covers every var the loaders read
- [ ] `requirements.txt` matches actual imports in both directions (derived, not eyeballed)
- [ ] PEP8 pass done via conservative `autopep8` + AST diff proof, not manual guessing
- [ ] README's status claims, run commands, and layout diagrams match the real code
- [ ] Script/batch filenames consistent within their own folder
- [ ] `coding-conventions.md` identical (or deliberately, visibly different) across projects
- [ ] Shared SQLite files have `timeout=` and collision-safe primary keys
- [ ] Occasional literal grep for known typo patterns across the whole tree

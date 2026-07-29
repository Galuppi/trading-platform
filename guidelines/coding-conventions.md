# Trading Platform — Coding Conventions & Design Standards

Living reference for `trader`, `signal-provider`, `price-provider`, and any future
project in this family. Established during the `trader` fine-tuning pass
(July 2026). Use this as the checklist when aligning an existing project or
starting a new one — including as direct input to an agent tasked with
bringing another codebase in line.

Each rule below states the convention, why it exists, and a concrete
before/after where useful. Where a rule was learned from a real bug or
near-miss in this codebase, that's noted — these aren't arbitrary style
preferences.

---

## 1. Project / Folder Structure

```
app/
  base/                     # Abstract interfaces (ABCs) — one per cross-platform concern
  common/
    config/
      *.yaml                # Non-secret, non-strategy settings (e.g. account_risk.yaml)
      constants.py           # Fixed string/number constants, grouped with comments
      paths.py                # All filesystem paths, in one place
      loaders/                 # THE ONLY place os.getenv()/os.environ is allowed
    models/
      model_<concept>.py     # One file per concept area, dataclasses only
    services/
      <concept>_manager.py    # Or plain <concept>.py for non-manager services
  connectors/
    <platform>/                # mt5/, ctrader/, etc. — concrete implementations of app/base
  factories/
    factory_<concept>.py       # Construction functions only, no business logic
  strategies/
    <strategy_name>/
      strategy.py
      config.yaml
  runtime/
    main.py                    # Or run.py — composition root, see §6
    engine.py
scripts/
  <one_off_task>.py             # Migrations, connectivity checks, setup helpers
```

Rule of thumb: if a folder needs a name, prefer the plain concept
(`connectors/`, `strategies/`, `loaders/`) over a decorated one
(`platform_connectors/`, `strategy_definitions/`). The parent path already
gives context — see §4 on redundant naming, the same logic applies to
folders.

---

## 2. Environment Variables & Configuration

- **`os.getenv()` / `os.environ` may only appear inside a file under
  `app/common/config/loaders/`.** Nowhere else — not in `main.py`, not in a
  manager, not in a connector. This was enforced across all three projects;
  `price-provider` needed the most cleanup (it had raw `os.getenv()` calls
  directly in `run.py`).
- Each loader returns a **typed dataclass**, never a raw dict. E.g.
  `load_server_config() -> ServerConfig`, not `load_server_config() -> dict`.
- `main.py` / `run.py` composition looks like:
  ```python
  connector_config = load_connector_config()
  if is_already_running(LOCK_FILE_PATH, connector_config.environment):
      sys.exit(1)
  log_level = load_log_level()
  setup_logger(LOG_PATH, connector_config.environment, log_level)
  ```
  — every setting comes from a loader call, nothing is read inline.
- **Strategy/module-specific tunables live in per-item YAML** (e.g.
  `app/strategies/<name>/config.yaml`), not environment variables. Env vars
  are for deployment-level concerns (credentials, host/port, environment
  name, log level) — YAML is for business/trading configuration.

---

## 3. Naming: No Redundant Prefixes, No Platform Leakage

**Don't repeat the container's name in its own fields.** If the object
already gives context, the field doesn't need to repeat it:

```python
# Bad — redundant, reads as "risk.account_stop_loss"
class AccountRisk:
    account_stop_loss: float
    account_take_profit: float

# Good — the class name already says "account risk"
class AccountRisk:
    stop_loss: float
    take_profit: float
```

Only prefix a field when it disambiguates two genuinely different things
living on the *same* object — e.g. `TradeRecord.id` (the trade's own id) and
`TradeRecord.strategy_id` (which strategy placed it) are different concepts
that would collide as bare `id` twice.

**Don't bake one platform's vocabulary into a shared/generic model.** MT5
calls a strategy tag "magic" (an int); cTrader calls the equivalent thing
"label" (a string). Neither name belongs in the platform-agnostic layer:

```python
# Generic model — platform-agnostic name
class StrategyConfig:
    strategy_id: int      # not "magic"

# MT5 boundary — translate to the platform's own field name
request = {"magic": order.strategy_id}          # MT5's own vocabulary, kept as-is

# cTrader boundary — translate to that platform's own field
new_market_order(..., label=str(order.strategy_id))  # cTrader's own vocabulary, kept as-is
```

The rule cuts both ways: keep the generic model clean, *and* don't rename a
third-party API's own field to match your model — `"magic"` stays `"magic"`
in the literal MT5 request dict, because that's MT5's name for it, not
yours.

**Fix real, misleading names even mid-project**, but treat any rename that
touches already-*persisted* data (state files, DB columns) as a deploy-time
migration, not a free refactor — see §11.

**Typos are a distinct failure mode worth a deliberate check.** A typo
repeated identically across an interface and every implementation of it
(e.g. `get_server_tick_timestanp` copied into 3 connectors) passes every
"does this match the pattern" review, because it *does* match — every copy
agrees with every other copy. Worth an occasional literal grep for
suspicious tokens across the whole tree, not just diff review.

---

## 4. Type Hints

Use `typing.Optional[X]`, not the `X | None` union syntax. Doesn't matter
hugely which is chosen — it matters that only one is used. Mixed usage
(found in 5 places in `trader`, `Optional[X]` used ~166 times elsewhere) is
what actually creates confusion, not the syntax choice itself.

---

## 5. Factories & Dependency Injection

- One file per concern: `app/factories/factory_<concept>.py`.
- **Every factory function is named `get_<thing>(...)`**, regardless of
  whether it constructs a fresh instance or returns something cached. The
  name describes "hand me a ready-to-use X", not the internal mechanics.
  (Renamed `build_order_request` → `get_order_request`,
  `create_trade_record` → `get_trade_record`,
  `strategy_registry_config/class/registry` → `get_strategy_config` /
  `get_strategy_class` / `get_strategies` to match the other 9 factories
  that already used `get_*`.)
- Factories take **already-loaded config dataclasses** as parameters, not
  raw paths or dicts — with the single exception of the actual YAML→dataclass
  boundary function itself (e.g. `get_strategy_config(config_path: Path)`).
- Dependencies are wired via explicit constructor args or an
  `attach_services(...)` call, never a global registry or service locator.
- Composition happens **once**, in `main.py`/`run.py`: load config → build
  dependencies via factories → inject into the engine/strategies → run.

---

## 6. Base Classes / Interfaces

- Every concern that crosses platforms (`Account`, `Connector`, `Symbol`,
  `Trade`, `Strategy`) gets an ABC in `app/base/`, with one concrete
  implementation per platform under `app/connectors/<platform>/`.
- Interface method names must match **exactly** across every
  implementation. A platform-only need is handled inside that platform's
  connector, not added to the shared interface unless every platform can
  reasonably implement it.
- Class naming for platform implementations: `Mt5<Thing>` / `CTrader<Thing>`
  — capitalized to match how each platform actually brands itself (MT5,
  cTrader), not a generic scheme.

---

## 7. Properties vs. Explicit Methods

**`@property`** — for cheap, side-effect-free reads of state that's already
sitting in memory. No I/O, no parameters, no meaningful chance of failure.
The point is that reading it should *feel* like reading a plain attribute,
because that's exactly what it is.

**Explicit `get_*` / `is_*` / `has_*` methods** — for anything that does
real work: hits a broker API, reads a file, computes over a collection,
takes parameters, or might meaningfully fail/raise. The call syntax should
telegraph cost — `obj.value` should never surprise you by pinging MT5.

```python
# RiskManager — reads/writes an already-loaded in-memory dataclass, no I/O
@property
def stop_loss(self) -> Optional[float]:
    return self._risk.stop_loss if self._risk else None

@stop_loss.setter
def stop_loss(self, value: float) -> None:
    self._risk.stop_loss = value
    logger.info("Account stop loss updated — %s", value)

# Account — hits the live broker connection, stays an explicit method
def get_balance(self) -> float:
    return mt5.account_info().balance
```

A property setter is fine as long as the body stays trivial (assignment +
maybe a log line). If a "setter" needs to do real validation, retries, or
I/O, make it an explicit `update_*`/`set_*` method instead — don't hide real
work behind `obj.attr = x` syntax.

Boolean naming: `is_*` for state checks (`is_market_open`, `is_holiday`),
`has_*` for possession/threshold checks (`has_sufficient_margin`,
`has_reached_max_trades`). Both are legitimate — pick whichever reads more
naturally for the specific check rather than forcing one universally.

---

## 8. Models (dataclasses)

- `app/common/models/model_<concept>.py`, one file per concept area.
- Suffix conventions:
  - `*Config` — loaded settings (`StrategyConfig`, `AccountRisk`,
    `ConnectorConfig`, `ServerConfig`)
  - `*Record` — persisted/logged entities (`TradeRecord`)
  - `*Request` / `*Result` — transient operation payloads (`OrderRequest`,
    `OrderResult`, `TradeResult`)
- **New fields on a dataclass that gets persisted (e.g. `TradeRecord`) must
  have a default.** `TradeRecord(**old_persisted_dict)` has to keep working
  after the schema grows, or every trade opened before the change becomes
  unloadable the moment the process restarts.

---

## 9. Logging & Error Handling

- Every module that can fail sets up its own module-level logger near the
  top: `logger = logging.getLogger(__name__)`. No module should be silently
  loggerless — this was missing entirely in `state_manager.py`,
  `dashboard_manager.py`, and `lock.py` and has since been added to all
  three.
- **No bare `except Exception: pass`.** At minimum:
  - `logger.debug(...)` for genuinely inconsequential, expected races
    (e.g. a lock file that's already gone).
  - `logger.warning(...)` for anything that silently drops user-visible
    state — most importantly, a persisted record failing to deserialize.
    This exact case (`TradeRecord(**tdata)` failing silently on a stale
    field) is precisely the kind of bug a future rename can reintroduce
    without a log line to catch it.
- Include the relevant identifier in the message (trade id, symbol,
  strategy name) so a failure is traceable from the log alone.

---

## 10. Single-Instance Locking

One `lock.py` per app (`app/common/services/lock.py`), exposing exactly:

```python
def is_already_running(lock_path: Path, environment: str) -> bool: ...
def release_lock(lock_path: Path) -> None: ...
```

- Locking is enforced **only in Production** — dev runs (VS Code, manual
  testing) are never blocked by a stale lock.
- `lock.py` **never reads the environment itself** — the caller (`main.py`)
  loads it via the connector-config loader and passes it in.
- `main.py`/`run.py` calls `is_already_running()` as the very first thing,
  before any other setup, and calls `release_lock()` in a top-level
  `finally` block.

---

## 11. Persisted State & Migrations

- A rename or removal of any field that ends up in **persisted** data
  (`state.json`, a DB column) is **not a free refactor** — it needs an
  explicit migration step before deploy, even though the equivalent rename
  on a fresh-loaded YAML file (like `account_risk.yaml`) is free.
- Prefer a small one-off script under `scripts/` that migrates the file in
  place (with a timestamped backup) over trying to make code tolerate both
  old and new field names indefinitely.
- Deploy order for any change touching persisted state:
  **stop process → deploy code → run migration (or deliberately wipe state,
  if genuinely safe, e.g. markets closed with no open positions) → restart.**
- Deserialization of persisted records must never fail silently (see §9) —
  a silent drop here means a real open position becomes invisible to the
  engine (no exit-signal checks, no SL/TP management, per-strategy trade
  counts reset to zero) with no error anywhere to indicate why.

---

## 12. Worked Example: a Full Convention Pass

The `strategy_id` / `magic` / `label` chain touches almost every rule above
and is a good template for reviewing any future concept:

1. **Started wrong**: `"magic": 0` hardcoded directly in the MT5 request —
   no config, no per-strategy identity, platform-specific term used nowhere
   else.
2. **First pass**: added `magic: int` to `StrategyConfig`, threaded through
   `OrderRequest` → `TradeRecord` → the MT5 request. Correct data flow, but
   wrong name — "magic" is MT5's word, not a generic concept.
3. **Corrected**: renamed the generic model field to `strategy_id`; MT5's
   request dict keeps the literal `"magic"` key (that's MT5's own field
   name); cTrader's `label` param receives the same `strategy_id`, converted
   to `str` (cTrader's own field name, its own type).
4. **Deploy risk caught before shipping**: live `state.json` already had
   trades persisted with the old `magic` key. A migration script was
   written and tested (backup + key rename) before this was cleared to
   deploy — then dropped from the plan entirely once it turned out the
   deploy window was a weekend with no open positions, making the migration
   moot. The discipline (check persisted-state impact before any rename)
   is the point, not the specific script.

---

## Quick Checklist for Aligning Another Project

- [ ] All `os.getenv()`/`os.environ` calls live only in `*/config/loaders/*.py`
- [ ] Every loader returns a typed dataclass
- [ ] `main.py`/`run.py` only calls loaders + factories, no inline env/config logic
- [ ] No field name repeats its own container's name
- [ ] No platform-specific vocabulary (broker field names, etc.) in shared models
- [ ] One `lock.py` with `is_already_running(lock_path, environment)` /
      `release_lock(lock_path)`, production-gated, environment passed in by caller
- [ ] All factory functions named `get_<thing>`, one file per concern
- [ ] `Optional[X]` used consistently, no `X | None` mixed in
- [ ] Every module that can fail has its own `logger = logging.getLogger(__name__)`
- [ ] No bare `except Exception: pass` — at least `debug` or `warning` with context
- [ ] Cheap in-memory reads are `@property`; I/O or parameterized reads are explicit methods
- [ ] New fields on persisted dataclasses have defaults
- [ ] Any rename touching persisted state has a migration plan before deploy

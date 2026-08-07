# trader

A live, multi-strategy, multi-asset, multi-platform trading application. Trades on both
**MetaTrader 5** and **cTrader** — both connectors are fully implemented and live.

---

## How it runs

```
main.py                    → loads config, wires up services, starts the engine
  └─ Engine.run()           → connects, syncs state with broker, loops strategies every 30s
       └─ Strategy          → per-symbol entry/exit signals, one class per strategy
            └─ Trade         → stateless order execution (Mt5Trade / CTraderTrade)
                 └─ Calculator → pure math: sizing, stop loss, profit — no side effects
       └─ StateManager       → persists trades, account snapshots, daily risk state
       └─ DashboardManager   → writes the live HTML dashboard + terminal status line
```

Strategies never talk to the broker directly — they go through `Trade`, which is a thin,
stateless execution layer. All the math (position sizing, stop-loss points, profit) is
centralized in `Calculator`, which takes no side effects and is fully testable in isolation.

---

## Strategies

Each strategy is a self-contained folder under `app/strategies/` with its own `strategy.py`
and `config.yaml`. New strategies are picked up automatically at startup — no registration
step required, `factory_strategy.py` discovers and loads any folder with both files present.

| Strategy | What it does |
|---|---|
| `break_out` | Enters when price breaks out of a defined opening range. |
| `go_long` | Long-only, one directional trade per session. |
| `go_long_ext` | Long-only with a defined opening range and entry window. |
| `monday_open_swing` | Enters at Monday's open, exits Tuesday close. |
| `news_cross` | SMA crossover, signal driven by news sentiment scoring. |
| `quotes_cross` | SMA crossover, signal driven by live quote/price data. |

`news_cross` and `quotes_cross` both subclass a shared crossover base and are the two
strategies that can run on the same symbol simultaneously — trade lookups in `StateManager`
are scoped by strategy name specifically to keep them from stepping on each other's state.

---

## Platform support

| Platform | Status |
|---|---|
| MetaTrader 5 | Implemented — live trading via the `MetaTrader5` package, requires the MT5 terminal running and logged in |
| cTrader | Implemented — live trading via the cTrader Open API (`ctrader-open-api`), OAuth-based, no terminal required |

Adding a platform means implementing `Account`, `Connector`, `Symbol`, and `Trade` (see
`app/base/`) and registering it in `app/factories/factory_platform.py`. Nothing else in the
app needs to change — strategies, the engine, and state persistence are all platform-agnostic.

### cTrader OAuth setup

cTrader authenticates via OAuth rather than a login/password, so getting a `CTRADER_REFRESH_TOKEN`
into `.env` is a one-time browser step rather than just typing in credentials:

```bash
scripts\run_ctrader_oauth_setup.bat
```

This starts a small local web server, opens your browser to the cTrader consent page, and once
you approve, exchanges the resulting code for tokens itself — `CTRADER_CLIENT_SECRET` never
touches the browser. The result page shows the refresh token (with a copy button) and your
linked accounts side by side, so you can match the account number shown in the cTrader UI to
the `ctidTraderAccountId` that `CTRADER_ACCOUNT_ID` actually expects — nothing is written to
`.env` automatically, copy it over yourself. One-time prerequisite: register
`http://localhost:5069/oauth_callback.html` as a redirect URI on
[connect.spotware.com/apps](https://connect.spotware.com/apps).

---

## Configuration

All runtime config comes from `.env` (copy `.env.sample` to get started). Variables are
grouped by what they actually configure, not lumped under one generic prefix:

- **`PLATFORM_*`** — settings that apply regardless of broker: `PLATFORM_TYPE` (`mt5` or
  `ctrader`), `PLATFORM_ENVIRONMENT` (`Development`/`Production`), `PLATFORM_SERVER`,
  `PLATFORM_TIMEZONE`, `PLATFORM_TIME_OFFSET`
- **`MT5_*`** — MetaTrader-specific credentials: `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_TERMINAL_PATH`
- **`CTRADER_*`** — cTrader-specific credentials: `CTRADER_ACCOUNT_ID`, `CTRADER_CLIENT_ID`,
  `CTRADER_CLIENT_SECRET`, `CTRADER_REFRESH_TOKEN`, `CTRADER_API_KEY`
- **`NOTIFY_*`** — Pushover notification settings: `NOTIFY_SERVER_URL`, `NOTIFY_APP_TOKEN`,
  `NOTIFY_USER_KEY`
- **`DATABASE`** — filename of the shared deals database (default `deals.db` if unset), resolved
  against `DATA_DIR` — see "Deal archiving, heartbeat & crash alerts" below
- **`LOG_LEVEL`** — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

`PLATFORM_ENVIRONMENT` also gates the single-instance lock file: the app only refuses to start
a second instance when `PLATFORM_ENVIRONMENT=Production`, so dev runs from VS Code won't get
blocked by a stale lock. The lock file is released on shutdown regardless of how the process
ends (clean exit, crash, or Ctrl+C).

Notifications are Pushover-only — there's no multi-service abstraction here, since that's the
only service actually in use.

---

## Running it

**Development** — open the folder in VS Code, select the venv interpreter, run
`app/runtime/main.py` directly (F5 or via a `launch.json` debug config).

**Production** — `startup/run_app_prod.bat` activates the production venv and runs the app.
`startup/backup_and_deploy_to_production.bat` handles backing up and deploying a new build to
the production folder. `startup/release_app_prod.bat` is the release entry point.

```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.sample .env   # then fill in real credentials
python app\runtime\main.py
```

MT5 requires the MetaTrader 5 terminal to be installed and running locally, logged into the
account matching `MT5_LOGIN` — the Python package talks to the running terminal, it doesn't
connect independently.

---

## Deal archiving, heartbeat & crash alerts

**Deal archiving** — every closed trade is written to a shared SQLite database once an hour, so
per-strategy/per-symbol performance can be queried or visualized (e.g. in Metabase) without
depending on state that gets pruned after 24h. The database lives in `DATA_DIR`
(`Apps\..\Data\`, two levels above the per-instance app folder), so it's shared by every
instance in the app family and untouched by an app-only redeploy — MT5 and cTrader running in
parallel write into the same file safely (see `DealArchiveManager` for the collision-safety
details).

**Heartbeat** — `app/runtime/state/heartbeat.json` is rewritten once per successful loop
iteration. A stale timestamp (no external watchdog reads this yet — that's a planned addition)
means the process has genuinely frozen, as opposed to hit a handled, logged error.

**Crash alerts** — a failed platform connection at startup, or any unhandled exception during
the run loop, sends a Pushover notification before the process exits, instead of hanging
indefinitely on an unattended console.

---

## Project layout

```
app/
  base/         abstract interfaces: Account, Connector, Symbol, Trade, Strategy, BaseEngine
  common/
    config/     constants, paths, env loaders
    models/     dataclasses: ConnectorConfig, TradeRecord, StrategyConfig, DatabaseConfig, etc.
    services/   Calculator, StateManager, DashboardManager, NewsManager, RiskManager,
                SyncManager, DealArchiveManager, PlatformTime, PushoverManager
  connectors/
    mt5/        MetaTrader 5 implementation (live)
    ctrader/    cTrader implementation (live)
  factories/    wiring — builds concrete instances from config, no business logic
  runtime/      main.py (entry point) and engine.py (the run loop)
  strategies/   one folder per strategy, each with strategy.py + config.yaml
startup/        .bat scripts for dev/prod runs and deployment
scripts/        one-off diagnostics and the cTrader OAuth setup helper
```

---

## Status

- ✅ MT5 and cTrader live connectors, fully wired
- ✅ Six strategies running against both platforms
- ✅ Deal archiving, heartbeat, and crash alerting in place
- ✅ Type hints and docstrings complete across the codebase
- 🔜 Advanced risk manager, web-based monitoring dashboard, external heartbeat watchdog

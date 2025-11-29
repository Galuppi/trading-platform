# 🧠 Trading System Architecture

A modular, **multi-strategy**, **multi-asset**, and **multi-platform** trading framework designed for both **live trading** and **backtesting**.  
Currently supports **MetaTrader 5 (MT5)** with an upcoming **cTrader connector**.  
Includes a fully functional **backtester** and a **historical data loader** that retrieves M1 data directly from the broker server.

---

## ⚙️ Overview

| Component | Description |
|------------|--------------|
| **main.py** | Orchestrator that wires up all components — strategies, engine, and state management. Determines mode (live or backtest) based on `.env`. |
| **Engine** (`engine.py` / `enginetester.py`) | Core runtime loop that executes strategies, manages position states, and persists trades. |
| **Strategy classes** | Contain all trading logic. Each strategy calls `execute_entry()` and `execute_exit()` to interact with the system. |
| **Trade classes** (e.g. `Mt5TesterTrade`) | Represent trades. Handle execution or simulation, but remain **stateless** — profit/commission logic lives in `Calculator`. |
| **Calculator** | Centralized component for all trade math: profit, commissions, margin, and swap calculations. Pure and testable. |
| **StateManager** | Handles trade persistence and state saving. Interfaces include `add_trade()`, `mark_trade_closed()`, and `get_all_trades()`. |
| **PlatformTime** | Unified time abstraction used for consistent timestamp handling across live and backtesting. |

---

## 🧩 System Flow

```
main.py (Orchestrator)
   ↓
Engine / EngineTester
   ↓
Strategy (multi-strategy)
   ↓
Trade / Mt5TesterTrade (execution abstraction)
   ↓
Calculator (math only)
   ↓
StateManager (persistence)
```

### ✅ Core Design Principles

- **Multi-Strategy** — multiple strategies can run simultaneously.  
- **Multi-Asset** — each strategy can handle several symbols concurrently.  
- **Multi-Platform** — supports MT5 now, cTrader next.  
- **Stateless Trades** — `Trade` objects hold no persistent state.  
- **Pure Computation** — all math is in `Calculator`, fully testable.  
- **Unified Time Handling** — `PlatformTime` ensures consistent timestamps.  

---

## 🧮 Backtesting vs. Live Trading

The system switches automatically based on `.env` configuration:

| Mode | `.env` setting | Engine used | Description |
|------|----------------|-------------|--------------|
| **Backtest** | `PLATFORM_TYPE=mt5tester` | `EngineTester` | Runs simulated trades using M1 historical data pulled from the broker. |
| **Live** | `PLATFORM_TYPE=mt5` | `Engine` | Executes real trades through the MT5 connector. |

### Backtester Highlights

- Fetches **M1 timeframe** data directly from the broker server.  
- Simulates fills, commissions, and slippage through `Calculator`.  
- Uses **the same strategy code** as live trading for identical logic.  
- Persists trade results via `StateManager.add_trade()`.  

---

## 🧱 Key Components

### **StateManager**
- Responsible for persisting trades and state snapshots.  
- Uses `@dataclass` and `asdict()` for reliable serialization.  
- Automatically saves state on every trade update.  

### **Mt5TesterTrade**
- Stateless trade simulator for backtesting.  
- Delegates profit and commission computation to `Calculator`.  
- Never persists or mutates external state directly.  

### **Calculator**
- Centralized math engine for:  
  - Profit/loss  
  - Commission and swap  
  - Margin requirements  
  - Slippage adjustments  

### **PlatformTime**
- Provides consistent timestamps and timezone handling.  
- Used across all modules for unified time logic.  

---

## 🔌 Platform Support

| Platform | Status | Notes |
|-----------|--------|-------|
| **MetaTrader 5** | ✅ Fully implemented | Live + Backtest |
| **cTrader** | 🚧 Coming soon | Connector in development |
| **MetaTrader 4** | 🧩 Possible | Compatible with core design |

---

## 💾 Data Handling

- Historical data loader fetches **M1 timeframe** data from the broker’s server.  
- Data is cached locally for efficient re-use.  
- Backtester uses the same strategy logic as live trading.  
- All trades and results are persisted via `StateManager`.

---

## 🧰 Technical Notes

- **Dataclasses** are used for all model objects (`TradeRecord`, `StateBalances`, etc.).  
- **Dependency Injection** supports modular connector swapping (MT5, cTrader, etc.).  
- **Logging** uses Python's standard `logging` library.  
- **Environment Variables** configure runtime behavior:
  ```bash
  PLATFORM_TYPE=mt5tester
  BACKTEST_DEPOSIT=100000
  BACKTEST_LEVERAGE=1:500
  ```

---

## 🧭 Key Guarantees

✅ All state persistence happens in `Engine`  
✅ `Mt5TesterTrade` is **stateless** and calls `Calculator` only  
✅ Trade data is stored via `StateManager.add_trade()`  
✅ Trade records use `@dataclass` + `asdict()` for clean serialization  
✅ Multi-strategy, multi-asset, multi-platform architecture by design  

---

## 🚀 Roadmap

- [x] MT5 Live Connector  
- [x] MT5 Backtester  
- [x] Historical Data Loader  
- [ ] cTrader Connector  
- [ ] Advanced Risk Manager  
- [ ] Web Dashboard for Monitoring  

---

## 🧩 Summary

This trading system provides a **clean separation of concerns**:

- **Strategy logic** → Strategy classes  
- **Execution logic** → Trade / Connector layer  
- **Computation** → Calculator  
- **Persistence** → StateManager  
- **Orchestration** → main.py  

This architecture ensures a highly **extensible**, **testable**, and **broker-agnostic** trading system — suitable for both live trading and historical backtesting.

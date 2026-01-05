import os
import webbrowser
from datetime import datetime
from typing import Any, List, Optional
from colorama import Fore, Style, init

from app.common.config.paths import DASHBOARD_PATH
from app.common.system.platform_time import PlatformTime
from app.common.config.constants import MODE_BACKTEST

init(autoreset=True)


class DashboardManager:

    HTML_TEMPLATE = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Trading System Status</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body {{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#1e1e1e;color:#e0e0e0;margin:0;padding:20px;}}
            .container {{max-width:1000px;margin:0 auto;}}
            h1 {{color:#4CAF50;text-align:center;margin-bottom:10px;}}
            .meta {{text-align:center;color:#aaa;font-size:0.9em;margin-bottom:20px;}}
            .section {{
                background:#2d2d2d;
                margin:15px 0;
                padding:16px;
                border-radius:8px;
                border-left:4px solid #4CAF50;
                font-size:0.95em;
            }}
            .section h3 {{
                margin:0 0 12px 0;
                color:#4CAF50;
                font-size:1.1em;
            }}
            .item {{margin:6px 0;}}
            .label {{color:#4CAF50;font-weight:bold;}}
            .profit-neg {{color:#f44336;}}
            .profit-pos {{color:#4CAF50;}}
            .market-open {{color:#4CAF50;}}
            .market-closed {{color:#f44336;}}
            .strategy {{background:#333;margin:10px 0;padding:12px;border-radius:6px;}}
            .footer {{text-align:center;margin-top:30px;color:#777;font-size:0.85em;}}
            .warning {{color:#ff9800;}}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Trading System Status</h1>
            <div class="meta">Mode: {mode} • {date} • Local: {local_time} • Platform: {platform_time} • UTC: {utc_time}</div>
            {balances_html}
            <div class="section">
                <h3>Strategies</h3>
                {strategies_html}
            </div>
            <div class="section">
                <h3>Scheduled event</h3>
                {last_event_html}
            </div>
            <div class="footer">Last updated: {timestamp}</div>
        </div>
    </body>
    </html>"""

    def __init__(self, dashboard_path: str = str(DASHBOARD_PATH)):
        self.dashboard_path = dashboard_path
        self._browser_opened = False

    def _clear_terminal(self) -> None:
        print("\033[2J\033[H", end="", flush=True)
        os.system('cls' if os.name == 'nt' else 'clear')

    def _open_browser_once(self) -> None:
        if not self._browser_opened:
            try:
                webbrowser.open(f"file://{os.path.abspath(self.dashboard_path)}", new=2)
                self._browser_opened = True
            except Exception:
                pass

    def _build_html(
        self,
        strategies: List[Any],
        state_manager: Any,
        mode: str,
        backtester_config: Optional[Any],
        summary_writer: Optional[Any],
    ) -> str:
        current_time = datetime.now()
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        current_date = PlatformTime.now().strftime("%Y-%m-%d")
        local_time = PlatformTime.local_now().strftime("%H:%M")
        platform_time = PlatformTime.now().strftime("%H:%M")
        utc_time = PlatformTime.local_now_utc().strftime("%H:%M")

        strategies_html = ""
        for strategy in strategies:
            strategy_name = strategy.strategy_display_name
            asset_list = ", ".join(asset.symbol for asset in strategy.assets)
            trades = state_manager.get_execute_entrys(strategy=strategy.strategy_name) or []
            open_trades = len(trades)
            is_market_open = strategy.is_market_open()
            is_holiday = strategy.is_holiday()
            market_class = "market-open" if is_market_open else "market-closed"

            strategies_html += f"""
            <div class="strategy">
                <div><span class="label">Strategy:</span> {strategy_name}</div>
                <div><span class="label">Assets:</span> {asset_list}</div>
                <div><span class="label">Open Trades:</span> {open_trades}</div>
                <div><span class="label">Market open:</span> <span class="{market_class}">{'Yes' if is_market_open else 'No'}</span></div>
                <div><span class="label">Holiday:</span> {'Yes' if is_holiday else 'No'}</div>
            </div>"""

        last_event = state_manager.get_last_event()
        if last_event:
            last_event_html = f"""
            <div class="item"><span class="label">Title:</span> {last_event.title}</div>
            <div class="item"><span class="label">Impact:</span> {last_event.impact}</div>
            <div class="item"><span class="label">Country:</span> {last_event.country}</div>
            <div class="item"><span class="label">Time:</span> {last_event.time}</div>
            """
        else:
            last_event_html = "<div class='item'>No event</div>"

        if mode == MODE_BACKTEST:
            balances_html = self._build_backtest_balances(backtester_config, summary_writer)
        else:
            balances_html = self._build_live_balances(state_manager)

        return self.HTML_TEMPLATE.format(
            mode=mode.capitalize(),
            date=current_date,
            local_time=local_time,
            platform_time=platform_time,
            strategies_html=strategies_html,
            balances_html=balances_html,
            last_event_html=last_event_html,
            timestamp=timestamp,
            utc_time=utc_time,
        )

    def _build_backtest_balances(self, backtester_config, summary_writer):
        if not backtester_config or not summary_writer:
            return "<div class='warning'>[WARNING] Backtest config/writer missing</div>"
        try:
            initial_deposit = float(backtester_config.backtest_deposit)
            balance_info = summary_writer.get_balance_info(initial_deposit=initial_deposit)
            balance_str = f"{balance_info['balance']:.2f}"
            profit = balance_info["profit"]
            target_reached = balance_info.get("target_reached", False)
            target_reached_str = "Yes" if target_reached else "No"
            profit_class = "profit-neg" if profit < 0 else "profit-pos"
            profit_html = f"<span class='{profit_class}'>{profit:+.2f}</span>"
            return f"""
            <div class="section">
                <h3>Balances</h3>
                <div class="item"><span class="label">Balance:</span> {balance_str}</div>
            </div>
            <div class="section">
                <h3>Daily performance</h3>
                <div class="item"><span class="label">Profit:</span> {profit_html}</div>
                <div class="item"><span class="label">Target reached:</span> {target_reached_str}</div>
            </div>"""
        except Exception as exc:
            return f"<div class='warning'>[ERROR] Backtest: {exc}</div>"

    def _build_live_balances(self, state_manager):
        try:
            balance_state = state_manager.get_state_balances()
            equity_str = f"{balance_state.equity:.2f}"
            balance_str = f"{balance_state.balance:.2f}"
            begin_balance_str = f"{balance_state.begin_balance:.2f}"
            profit = balance_state.profit
            target_reached = "Yes" if balance_state.target_reached else "No"
            profit_class = "profit-neg" if profit < 0 else "profit-pos"
            profit_html = f"<span class='{profit_class}'>{profit:+.2f}</span>"
            return f"""
            <div class="section">
                <h3>Balances</h3>
                <div class="item"><span class="label">Balance:</span> {balance_str}</div>
                <div class="item"><span class="label">Equity:</span> {equity_str}</div>
            </div>
            <div class="section">
                <h3>Daily performance</h3>
                <div class="item"><span class="label">Begin balance:</span> {begin_balance_str}</div>
                <div class="item"><span class="label">Profit:</span> {profit_html}</div>
                <div class="item"><span class="label">Target reached:</span> {target_reached}</div>
            </div>"""
        except Exception as exc:
            return f"<div class='warning'>[ERROR] Live balance: {exc}</div>"

    def _write_dashboard(self, html_content: str) -> None:
        try:
            path = os.path.abspath(self.dashboard_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as html_file:
                html_file.write(html_content)
            self._open_browser_once()
        except Exception as exc:
            print(f"{Fore.YELLOW}[WARN] Dashboard write failed: {exc}")

    def _print_terminal_log(self, strategies: List[Any], state_manager: Any, mode: str) -> None:
        self._clear_terminal()
        print("\n" + "=" * 60)
        print(f" STATUS | {mode.upper()} | {PlatformTime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)
        for strategy in strategies:
            strategy_name = strategy.strategy_display_name
            asset_list = ", ".join(asset.symbol for asset in strategy.assets)
            trades = len(state_manager.get_execute_entrys(strategy=strategy.strategy_name) or [])
            market_status = "OPEN" if strategy.is_market_open() else "CLOSED"
            print(f" • {strategy_name} | Trades: {trades} | {market_status} | {asset_list}")
        print("-" * 60)

        if mode != MODE_BACKTEST:
            try:
                balance_state = state_manager.get_state_balances()
                color = Fore.RED if balance_state.profit < 0 else Fore.GREEN
                print(
                    f" Equity: {balance_state.equity:.2f} | "
                    f"Balance: {balance_state.balance:.2f} | "
                    f"Profit: {color}{balance_state.profit:+.2f}{Style.RESET_ALL}"
                )
            except Exception:
                print(" [balance unavailable]")
        print("=" * 60 + "\n")

    def print_status_report(
        self,
        strategies: List[Any],
        state_manager: Any,
        mode: str,
        backtester_config: Optional[Any] = None,
        summary_writer: Optional[Any] = None,
        *,
        log_to_terminal: bool = False,
    ) -> None:
        try:
            html_content = self._build_html(strategies, state_manager, mode, backtester_config, summary_writer)
            self._write_dashboard(html_content)
        except Exception as exc:
            print(f"{Fore.RED}[ERROR] Dashboard failed: {exc}")

        if log_to_terminal:
            self._print_terminal_log(strategies, state_manager, mode)

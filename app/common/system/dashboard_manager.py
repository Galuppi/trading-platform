from typing import Any

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
    HTML_TEMPLATE = '<!DOCTYPE html>\n    <html lang="en">\n    <head>\n        <meta charset="UTF-8">\n        <meta name="viewport" content="width=device-width, initial-scale=1.0">\n        <title>Trading System Status</title>\n        <meta http-equiv="refresh" content="10">\n        <style>\n            body {{font-family:\'Segoe UI\',Tahoma,Geneva,Verdana,sans-serif;background:#1e1e1e;color:#e0e0e0;margin:0;padding:20px;}}\n            .container {{max-width:1000px;margin:0 auto;}}\n            h1 {{color:#4CAF50;text-align:center;margin-bottom:10px;}}\n            .meta {{text-align:center;color:#aaa;font-size:0.9em;margin-bottom:20px;}}\n            .section {{\n                background:#2d2d2d;\n                margin:15px 0;\n                padding:16px;\n                border-radius:8px;\n                border-left:4px solid #4CAF50;\n                font-size:0.95em;\n            }}\n            .section h3 {{\n                margin:0 0 12px 0;\n                color:#4CAF50;\n                font-size:1.1em;\n            }}\n            .item {{margin:6px 0;}}\n            .label {{color:#4CAF50;font-weight:bold;}}\n            .profit-neg {{color:#f44336;}}\n            .profit-pos {{color:#4CAF50;}}\n            .market-open {{color:#4CAF50;}}\n            .market-closed {{color:#f44336;}}\n            .strategy {{background:#333;margin:10px 0;padding:12px;border-radius:6px;}}\n            .footer {{text-align:center;margin-top:30px;color:#777;font-size:0.85em;}}\n            .warning {{color:#ff9800;}}\n        </style>\n    </head>\n    <body>\n        <div class="container">\n            <h1>Trading System Status</h1>\n            <div class="meta">Mode: {mode} • {date} • Local: {local_time} • Platform: {platform_time}</div>\n            <div class="section">\n                <h3>Balances</h3>\n                {balances_html}\n            </div>\n            <div class="section">\n                <h3>Strategies</h3>\n                {strategies_html}\n            </div>\n            <div class="footer">Last updated: {timestamp}</div>\n        </div>\n    </body>\n    </html>'

    def __init__(self, dashboard_path: str=str(DASHBOARD_PATH)) -> Any:
        """Perform the defined operation."""
        self.dashboard_path = dashboard_path
        self._browser_opened = False

    def _clear_terminal(self) -> None:
        """Perform the defined operation."""
        print('\x1bc', end='')

    def _open_browser_once(self) -> None:
        """Perform the defined operation."""
        if not self._browser_opened:
            try:
                webbrowser.open(f'file://{os.path.abspath(self.dashboard_path)}', new=2)
                self._browser_opened = True
            except Exception:
                pass

    def _build_html(self, strategies: List[Any], state_manager: Any, mode: str, backtester_config: Optional[Any], summary_writer: Optional[Any]) -> str:
        """Perform the defined operation."""
        current_time = datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')
        current_date = PlatformTime.now().strftime('%Y-%m-%d')
        local_time = PlatformTime.local_now().strftime('%H:%M')
        platform_time = PlatformTime.now().strftime('%H:%M')
        strategies_html = ''
        for strategy in strategies:
            strategy_name = strategy.strategy_display_name
            asset_list = ', '.join((asset.symbol for asset in strategy.assets))
            trades = state_manager.get_execute_entrys(strategy=strategy.strategy_name) or []
            open_trades = len(trades)
            is_market_open = strategy.is_market_open()
            is_holiday = strategy.is_holiday()
            market_class = 'market-open' if is_market_open else 'market-closed'
            strategies_html += f'''\n            <div class="strategy">\n                <div><span class="label">Strategy:</span> {strategy_name}</div>\n                <div><span class="label">Assets:</span> {asset_list}</div>\n                <div><span class="label">Open Trades:</span> {open_trades}</div>\n                <div><span class="label">Market open:</span> <span class="{market_class}">{('Yes' if is_market_open else 'No')}</span></div>\n                <div><span class="label">Holiday:</span> {('Yes' if is_holiday else 'No')}</div>\n            </div>'''
        if mode == MODE_BACKTEST:
            balances_html = self._build_backtest_balances(backtester_config, summary_writer)
        else:
            balances_html = self._build_live_balances(state_manager)
        return self.HTML_TEMPLATE.format(mode=mode.capitalize(), date=current_date, local_time=local_time, platform_time=platform_time, strategies_html=strategies_html, balances_html=balances_html, timestamp=timestamp)

    def _build_backtest_balances(self, backtester_config: Any, summary_writer: Any) -> Any:
        """Perform the defined operation."""
        if not backtester_config or not summary_writer:
            return "<div class='warning'>[WARNING] Backtest config/writer missing</div>"
        try:
            initial_deposit = float(backtester_config.backtest_deposit)
            balance_info = summary_writer.get_balance_info(initial_deposit=initial_deposit)
            balance_str = f"{balance_info['balance']:.2f}"
            profit = balance_info['profit']
            profit_class = 'profit-neg' if profit < 0 else 'profit-pos'
            profit_html = f"<span class='{profit_class}'>{profit:+.2f}</span>"
            return f'\n            <div class="item"><span class="label">Balance:</span> {balance_str}</div>\n            <div class="item"><span class="label">Profit:</span> {profit_html}</div>'
        except Exception as exc:
            return f"<div class='warning'>[ERROR] Backtest: {exc}</div>"

    def _build_live_balances(self, state_manager: Any) -> Any:
        """Perform the defined operation."""
        try:
            balance_state = state_manager.get_state_balances()
            equity_str = f'{balance_state.equity:.2f}'
            balance_str = f'{balance_state.balance:.2f}'
            profit = balance_state.profit
            profit_class = 'profit-neg' if profit < 0 else 'profit-pos'
            profit_html = f"<span class='{profit_class}'>{profit:+.2f}</span>"
            return f'\n            <div class="item"><span class="label">Equity:</span> {equity_str}</div>\n            <div class="item"><span class="label">Balance:</span> {balance_str}</div>\n            <div class="item"><span class="label">Profit:</span> {profit_html}</div>'
        except Exception as exc:
            return f"<div class='warning'>[ERROR] Live balance: {exc}</div>"

    def _write_dashboard(self, html_content: str) -> None:
        """Perform the defined operation."""
        try:
            path = os.path.abspath(self.dashboard_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as html_file:
                html_file.write(html_content)
            self._open_browser_once()
        except Exception as exc:
            print(f'{Fore.YELLOW}[WARN] Dashboard write failed: {exc}')

    def _print_terminal_log(self, strategies: List[Any], state_manager: Any, mode: str) -> None:
        """Perform the defined operation."""
        self._clear_terminal()
        print('\n' + '=' * 60)
        print(f" STATUS | {mode.upper()} | {PlatformTime.now().strftime('%Y-%m-%d %H:%M')}")
        print('=' * 60)
        for strategy in strategies:
            strategy_name = strategy.strategy_display_name
            asset_list = ', '.join((asset.symbol for asset in strategy.assets))
            trades = len(state_manager.get_execute_entrys(strategy=strategy.strategy_name) or [])
            market_status = 'OPEN' if strategy.is_market_open() else 'CLOSED'
            print(f' • {strategy_name} | Trades: {trades} | {market_status} | {asset_list}')
        print('-' * 60)
        if mode != MODE_BACKTEST:
            try:
                balance_state = state_manager.get_state_balances()
                color = Fore.RED if balance_state.profit < 0 else Fore.GREEN
                print(f' Equity: {balance_state.equity:.2f} | Balance: {balance_state.balance:.2f} | Profit: {color}{balance_state.profit:+.2f}{Style.RESET_ALL}')
            except Exception:
                print(' [balance unavailable]')
        print('=' * 60 + '\n')

    def print_status_report(self, strategies: List[Any], state_manager: Any, mode: str, backtester_config: Optional[Any]=None, summary_writer: Optional[Any]=None, *, log_to_terminal: bool=False) -> None:
        """Perform the defined operation."""
        try:
            html_content = self._build_html(strategies, state_manager, mode, backtester_config, summary_writer)
            self._write_dashboard(html_content)
        except Exception as exc:
            print(f'{Fore.RED}[ERROR] Dashboard failed: {exc}')
        if log_to_terminal:
            self._print_terminal_log(strategies, state_manager, mode)
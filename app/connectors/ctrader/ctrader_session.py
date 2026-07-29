"""Shared cTrader Open API session: connection, auth, caches, and a sync bridge over the Twisted reactor.

The cTrader Open API (ctrader-open-api / OpenApiPy) is Twisted-based and fully
asynchronous (Deferreds + a running reactor). The rest of this application is
synchronous (MT5-style blocking calls, polled every 30s by Engine). This module
is the bridge between the two worlds:

- The Twisted reactor runs once per process, on a dedicated daemon thread.
- All requests that have a real Req/Res pair (auth, symbols, trader info,
  reconcile, deal list, trendbars, spot subscriptions, SL/TP amendment) go
  through `_request()`, which uses `blockingCallFromThread` to hand the send
  to the reactor thread and block the calling (engine) thread until the
  matching response arrives or times out.
- Order execution (`ProtoOANewOrderReq` / `ProtoOAClosePositionReq`) has no
  matching Res message in this API — confirmation arrives asynchronously as a
  `ProtoOAExecutionEvent`. Those are correlated via `clientOrderId` (for new
  orders) or `positionId` (for closes) using a queue-based waiter registered
  before the request is sent.

`CTraderConnector`, `CTraderAccount`, `CTraderSymbol`, and `CTraderTrade` are
all thin wrappers around a single `CTraderSession` instance (a process-wide
singleton), the same way the MT5 classes are thin wrappers around the global
`MetaTrader5` module. This is required because `factory_platform.py` builds
these classes independently and separately from `connector.connect()`, so the
session must be lazily connected rather than injected at construction time.

IMPORTANT — things that could not be verified against a live server from this
environment and should be checked carefully against the demo account before
any real reliance on them:

- Volume conversion: order volume, minVolume/maxVolume/stepVolume all share
  the same cTrader-internal scale as `symbol.lotSize`, so lots <-> API volume
  conversion is done via `lots_to_api_volume()` / `api_volume_to_lots()`
  (single source of truth — this used to be duplicated separately in
  ctrader_trade.py and ctrader_account.py, which is a real risk if the
  rounding rule ever needs to change). This is scale-consistent regardless of
  the absolute scale factor, but has not been verified against a live fill.
- `get_tick_value()` (in ctrader_symbol.py) assumes the symbol's profit
  currency equals the account currency (no cross-currency conversion is
  applied). Fine for USD-quoted instruments on a USD account; will be wrong
  otherwise.
- Access token lifetime is ~2,628,000s (30 days), per Spotware's docs. Two
  mechanisms keep long-running sessions alive without ever hitting a live
  expiry: (1) `connection_check()` proactively refreshes the token once
  `ACCESS_TOKEN_REFRESH_INTERVAL_SECONDS` has elapsed since the last refresh
  (called every ~30s from the engine loop), and (2) `_request()` reactively
  catches an `OA_AUTH_TOKEN_EXPIRED` error response and transparently
  refreshes + retries the request once. Both paths call `_refresh_access_token()`
  followed by `_authenticate_account()`, since a refreshed access token must be
  re-sent via `ProtoOAAccountAuthReq` to remain valid for the session.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from app.common.config.constants import ENVIRONMENT_PRODUCTION
from app.common.models.model_connector import ConnectorConfig
from app.common.models.model_symbol import SpotPrice
from app.common.services.state_manager import StateManager

logger = logging.getLogger(__name__)

# Default request timeout for Req/Res style calls.
DEFAULT_TIMEOUT_SECONDS = 10
# How long to wait for the initial TCP/SSL connection to be established.
CONNECT_TIMEOUT_SECONDS = 20
# How long to wait for an order's ExecutionEvent confirmation.
EXECUTION_TIMEOUT_SECONDS = 15

# cTrader Open API represents prices (spot bid/ask, trendbar low + deltas) as
# fixed-point integers scaled by 10^5, independent of the symbol's own display
# `digits`. This is a documented Spotware convention, not derived per-symbol.
PRICE_SCALE = 100000.0

# ProtoOAExecutionType enum values that end an order/close wait; anything
# else (e.g. ORDER_ACCEPTED) is an intermediate event to keep waiting past.
EXECUTION_TYPE_FILLED = 3
EXECUTION_TYPE_REJECTED = 7
TERMINAL_EXECUTION_TYPES = (EXECUTION_TYPE_FILLED, EXECUTION_TYPE_REJECTED)

# Documented access token lifetime is ~2,628,000s (30 days). Refresh well
# before that so a long-running session never hits a live expiry.
ACCESS_TOKEN_REFRESH_INTERVAL_SECONDS = 20 * 24 * 60 * 60  # 20 days

# errorCode returned by cTrader when an API call is made with an expired
# access token (confirmed via Spotware community forum, not in the proto enum).
AUTH_TOKEN_EXPIRED_ERROR_CODE = "OA_AUTH_TOKEN_EXPIRED"


class CTraderSession:
    """Process-wide singleton wrapping one cTrader Open API connection."""

    _instance: Optional["CTraderSession"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "CTraderSession":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        self.config: Optional[ConnectorConfig] = None
        self.state_manager: Optional[StateManager] = None
        self._execution_event_callback = None

        self._client = None  # ctrader_open_api.Client
        self._reactor_thread: Optional[threading.Thread] = None
        self._reactor_started = threading.Event()

        self._connected_event = threading.Event()
        self._state_lock = threading.RLock()
        self._app_authenticated = False
        self._account_authenticated = False

        self.ctid_trader_account_id: Optional[int] = None
        self._access_token: Optional[str] = None
        self._last_token_refresh_time: Optional[float] = None

        # symbol caches, keyed by cTrader symbolId and by upper-cased symbol name
        self._symbols_by_name: Dict[str, Any] = {}   # name -> ProtoOALightSymbol
        self._symbols_by_id: Dict[int, Any] = {}      # id -> ProtoOALightSymbol
        self._symbol_details_by_id: Dict[int, Any] = {}  # id -> ProtoOASymbol (full)
        self._symbols_loaded = False

        # live spot cache, keyed by symbolId -> SpotPrice
        self._spot_cache: Dict[int, SpotPrice] = {}
        self._subscribed_symbol_ids: set = set()

        # assetId -> name (e.g. "USD"), used to resolve a symbol's profit currency
        self._assets_by_id: Dict[int, str] = {}

        # order execution correlation
        self._order_waiters: Dict[str, "queue.Queue"] = {}
        self._close_waiters: Dict[int, "queue.Queue"] = {}

    # ------------------------------------------------------------------
    # Configuration / connection lifecycle
    # ------------------------------------------------------------------

    def configure(self, config: ConnectorConfig, state_manager: StateManager = None) -> None:
        if not config.client_id or not config.client_secret or not config.refresh_token or not config.account_id:
            raise ValueError(
                "cTrader requires 'client_id', 'client_secret', 'refresh_token' and "
                "'account_id' in ConnectorConfig (Open API OAuth credentials)."
            )
        self.config = config
        self.state_manager = state_manager

    def is_connected(self) -> bool:
        with self._state_lock:
            return bool(
                self._client is not None
                and getattr(self._client, "isConnected", False)
                and self._account_authenticated
            )

    def connect(self) -> bool:
        """Establish (or re-establish) the cTrader Open API session. Blocking, idempotent."""
        if self.config is None:
            raise RuntimeError("CTraderSession.connect() called before configure().")

        try:
            self._ensure_reactor_running()
            self._ensure_client_connected()
            self._authenticate_application()
            self._refresh_access_token()
            self._verify_account_access()
            self._authenticate_account()
            self._load_symbols()

            with self._state_lock:
                self._account_authenticated = True

            logger.info(
                f"Successfully connected to cTrader Open API! "
                f"Account: #{self.config.account_id}, Environment: {self.config.environment}"
            )
            return True

        except Exception as error:
            logger.error(f"cTrader connection failed: {error}")
            with self._state_lock:
                self._account_authenticated = False
            return False

    def connection_check(self) -> bool:
        if not self.is_connected():
            return False

        if self._access_token_due_for_refresh():
            logger.info("cTrader access token approaching expiry; refreshing proactively.")
            try:
                self._refresh_access_token()
                self._authenticate_account()
            except Exception as error:
                logger.error(f"Proactive cTrader access token refresh failed: {error}")
                with self._state_lock:
                    self._account_authenticated = False
                return False

        return True

    def _access_token_due_for_refresh(self) -> bool:
        if self._last_token_refresh_time is None:
            return False
        return (time.time() - self._last_token_refresh_time) >= ACCESS_TOKEN_REFRESH_INTERVAL_SECONDS

    # ------------------------------------------------------------------
    # Reactor thread management
    # ------------------------------------------------------------------

    def _ensure_reactor_running(self) -> None:
        if self._reactor_thread is not None and self._reactor_thread.is_alive():
            return

        from twisted.internet import reactor

        def _run() -> None:
            self._reactor_started.set()
            reactor.run(installSignalHandlers=False)

        self._reactor_thread = threading.Thread(target=_run, name="ctrader-reactor", daemon=True)
        self._reactor_thread.start()

        if not self._reactor_started.wait(timeout=5):
            raise RuntimeError("Twisted reactor thread failed to start.")

        # Give the reactor a brief moment to actually enter its run loop before
        # anything is scheduled onto it via callFromThread.
        time.sleep(0.1)

    def _ensure_client_connected(self) -> None:
        from ctrader_open_api import Client, EndPoints, TcpProtocol
        from twisted.internet import reactor

        with self._state_lock:
            if self._client is not None and self._client.isConnected:
                return

            host = (
                EndPoints.PROTOBUF_LIVE_HOST
                if self.config.environment == ENVIRONMENT_PRODUCTION
                else EndPoints.PROTOBUF_DEMO_HOST
            )
            port = EndPoints.PROTOBUF_PORT

            logger.info(f"Connecting to cTrader Open API: {host}:{port}")

            client = Client(host, port, TcpProtocol)
            client.setConnectedCallback(self._on_connected)
            client.setDisconnectedCallback(self._on_disconnected)
            client.setMessageReceivedCallback(self._on_message)

            self._connected_event.clear()
            self._app_authenticated = False
            self._account_authenticated = False
            self._client = client

        reactor.callFromThread(client.startService)

        if not self._connected_event.wait(timeout=CONNECT_TIMEOUT_SECONDS):
            raise RuntimeError("Timed out waiting for cTrader TCP/SSL connection.")

    def _on_connected(self, _client) -> None:
        logger.info("cTrader TCP/SSL connection established.")
        self._connected_event.set()

    def _on_disconnected(self, _client, reason) -> None:
        logger.warning(f"cTrader connection lost: {reason}")
        with self._state_lock:
            self._app_authenticated = False
            self._account_authenticated = False
        self._connected_event.clear()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate_application(self) -> None:
        with self._state_lock:
            if self._app_authenticated:
                return

        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq,
        )

        request = ProtoOAApplicationAuthReq(
            clientId=self.config.client_id,
            clientSecret=self.config.client_secret,
        )
        self._request(request)

        with self._state_lock:
            self._app_authenticated = True
        logger.info("cTrader application authenticated.")

    def _refresh_access_token(self) -> None:
        """Refresh the access token; Spotware rotates the refresh token on each call."""
        from ctrader_open_api import Auth

        persisted_token = self.state_manager.get_ctrader_refresh_token() if self.state_manager else None
        current_refresh_token = persisted_token or self.config.refresh_token

        auth = Auth(self.config.client_id, self.config.client_secret, redirectUri="")
        token_response = auth.refreshToken(current_refresh_token)

        access_token = token_response.get("accessToken") if isinstance(token_response, dict) else None
        if not access_token:
            raise RuntimeError(f"Failed to refresh cTrader access token: {token_response}")

        self._access_token = access_token
        self._last_token_refresh_time = time.time()
        logger.info("cTrader access token refreshed.")

        new_refresh_token = token_response.get("refreshToken")
        if new_refresh_token and new_refresh_token != current_refresh_token:
            self.config.refresh_token = new_refresh_token
            if self.state_manager:
                self.state_manager.save_ctrader_refresh_token(new_refresh_token)
            else:
                logger.warning(f"No state_manager attached; new refresh token not persisted: {new_refresh_token}")

    def _verify_account_access(self) -> None:
        """Required by Spotware between app auth and account auth."""
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetAccountListByAccessTokenReq

        request = ProtoOAGetAccountListByAccessTokenReq(accessToken=self._access_token)
        response = self._request(request)

        account_id = int(self.config.account_id)
        known_ids = [account.ctidTraderAccountId for account in response.ctidTraderAccount]
        if account_id not in known_ids:
            raise RuntimeError(f"Account {account_id} not found in access token's account list: {known_ids}")

    def _authenticate_account(self) -> None:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAAccountAuthReq

        account_id = int(self.config.account_id)
        request = ProtoOAAccountAuthReq(
            ctidTraderAccountId=account_id,
            accessToken=self._access_token,
        )
        self._request(request)
        self.ctid_trader_account_id = account_id
        logger.info(f"cTrader account #{account_id} authenticated.")

    # ------------------------------------------------------------------
    # Symbol cache
    # ------------------------------------------------------------------

    def _load_symbols(self) -> None:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASymbolsListReq

        request = ProtoOASymbolsListReq(ctidTraderAccountId=self.ctid_trader_account_id)
        response = self._request(request)

        with self._state_lock:
            self._symbols_by_name.clear()
            self._symbols_by_id.clear()
            for light_symbol in response.symbol:
                self._symbols_by_name[light_symbol.symbolName.upper()] = light_symbol
                self._symbols_by_id[light_symbol.symbolId] = light_symbol
            self._symbols_loaded = True

        logger.info(f"Loaded {len(self._symbols_by_name)} cTrader symbols.")

    def resolve_symbol_id(self, symbol: str) -> int:
        light = self._symbols_by_name.get(symbol.upper())
        if light is None:
            raise ValueError(f"Unknown cTrader symbol: {symbol}")
        return light.symbolId

    def get_symbol_details(self, symbol: str) -> Any:
        """Return the full ProtoOASymbol (digits, volumes, lotSize, etc.), loading it on first use."""
        symbol_id = self.resolve_symbol_id(symbol)

        with self._state_lock:
            cached = self._symbol_details_by_id.get(symbol_id)
        if cached is not None:
            return cached

        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASymbolByIdReq

        request = ProtoOASymbolByIdReq(
            ctidTraderAccountId=self.ctid_trader_account_id,
            symbolId=[symbol_id],
        )
        response = self._request(request)
        if not response.symbol:
            raise ValueError(f"cTrader returned no symbol details for {symbol}")

        details = response.symbol[0]
        with self._state_lock:
            self._symbol_details_by_id[symbol_id] = details
        return details

    def get_light_symbol(self, symbol: str) -> Any:
        light = self._symbols_by_name.get(symbol.upper())
        if light is None:
            raise ValueError(f"Unknown cTrader symbol: {symbol}")
        return light

    def get_asset_name(self, asset_id: int) -> str:
        with self._state_lock:
            cached = self._assets_by_id.get(asset_id)
        if cached is not None:
            return cached

        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAAssetListReq

        request = ProtoOAAssetListReq(ctidTraderAccountId=self.ctid_trader_account_id)
        response = self._request(request)

        with self._state_lock:
            for asset in response.asset:
                self._assets_by_id[asset.assetId] = asset.name
            cached = self._assets_by_id.get(asset_id, "")
        return cached

    def lots_to_api_volume(self, symbol: str, lots: float) -> int:
        """Convert a lot size to cTrader's internal API volume unit for `symbol`.

        Single source of truth for this conversion — previously duplicated
        separately in ctrader_trade.py and ctrader_account.py, which is a real
        risk if the rounding rule ever needs to change.
        """
        info = self.get_symbol_details(symbol)
        return int(round(lots * info.lotSize))

    def api_volume_to_lots(self, symbol: str, api_volume: int) -> float:
        """Convert cTrader's internal API volume unit back to a lot size for `symbol`."""
        info = self.get_symbol_details(symbol)
        return api_volume / info.lotSize

    # ------------------------------------------------------------------
    # Live spot prices
    # ------------------------------------------------------------------

    def ensure_subscribed(self, symbol: str) -> int:
        """Ensure a live spot subscription is active for `symbol`; returns its symbolId."""
        symbol_id = self.resolve_symbol_id(symbol)

        with self._state_lock:
            if symbol_id in self._subscribed_symbol_ids:
                return symbol_id

        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASubscribeSpotsReq

        request = ProtoOASubscribeSpotsReq(
            ctidTraderAccountId=self.ctid_trader_account_id,
            symbolId=[symbol_id],
        )
        self._request(request)

        with self._state_lock:
            self._subscribed_symbol_ids.add(symbol_id)

        # Spot ticks arrive asynchronously after subscribing; give the first one
        # a moment to land so callers get real prices instead of a cache miss.
        deadline = time.time() + 5
        while symbol_id not in self._spot_cache and time.time() < deadline:
            time.sleep(0.1)

        return symbol_id

    def get_spot(self, symbol: str) -> SpotPrice:
        symbol_id = self.ensure_subscribed(symbol)
        with self._state_lock:
            spot = self._spot_cache.get(symbol_id)
        if spot is None:
            raise ValueError(f"No live price available yet for cTrader symbol: {symbol}")
        return spot

    # ------------------------------------------------------------------
    # Account / trade data
    # ------------------------------------------------------------------

    def get_trader(self) -> Any:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOATraderReq

        request = ProtoOATraderReq(ctidTraderAccountId=self.ctid_trader_account_id)
        response = self._request(request)
        return response.trader

    def get_unrealized_pnl(self) -> List[Any]:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAGetPositionUnrealizedPnLReq,
        )

        request = ProtoOAGetPositionUnrealizedPnLReq(ctidTraderAccountId=self.ctid_trader_account_id)
        response = self._request(request)
        return list(response.positionUnrealizedPnL)

    def reconcile(self) -> Any:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAReconcileReq

        request = ProtoOAReconcileReq(ctidTraderAccountId=self.ctid_trader_account_id)
        return self._request(request)

    def deal_list(self, from_timestamp_ms: int, to_timestamp_ms: int, max_rows: int = 500) -> List[Any]:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOADealListReq

        request = ProtoOADealListReq(
            ctidTraderAccountId=self.ctid_trader_account_id,
            fromTimestamp=from_timestamp_ms,
            toTimestamp=to_timestamp_ms,
            maxRows=max_rows,
        )
        response = self._request(request)
        return list(response.deal)

    def get_trendbars(self, symbol: str, period_enum: int, from_timestamp_ms: int, to_timestamp_ms: int) -> List[Any]:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetTrendbarsReq

        symbol_id = self.resolve_symbol_id(symbol)
        request = ProtoOAGetTrendbarsReq(
            ctidTraderAccountId=self.ctid_trader_account_id,
            symbolId=symbol_id,
            period=period_enum,
            fromTimestamp=from_timestamp_ms,
            toTimestamp=to_timestamp_ms,
        )
        response = self._request(request)
        return list(response.trendbar)

    def get_expected_margin(self, symbol: str, api_volume: int) -> Any:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAExpectedMarginReq

        symbol_id = self.resolve_symbol_id(symbol)
        request = ProtoOAExpectedMarginReq(
            ctidTraderAccountId=self.ctid_trader_account_id,
            symbolId=symbol_id,
            volume=[api_volume],
        )
        return self._request(request)

    def amend_position_sl_tp(self, position_id: int, stop_loss: float, take_profit: float) -> Any:
        """Amend an open position's stop-loss / take-profit.

        Routed through `_request()` (not a raw client.send) so that a
        `ProtoOAErrorRes` from a failed amend actually surfaces as an
        exception instead of being silently discarded — the original
        implementation ignored the response entirely, so failed amends never
        got logged.

        `stopLoss`/`takeProfit` are only included in the request when a real
        value is given. cTrader rejects the entire amend with
        TRADING_BAD_STOPS ("Protection can't be negative") if either field is
        sent as a literal 0 instead of being omitted — confirmed against a
        live account: every amend with TP=0.0 was rejected outright, taking
        a perfectly valid stop loss down with it.
        """
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAAmendPositionSLTPReq

        request_fields = {
            "ctidTraderAccountId": self.ctid_trader_account_id,
            "positionId": position_id,
        }
        if stop_loss:
            request_fields["stopLoss"] = stop_loss
        if take_profit:
            request_fields["takeProfit"] = take_profit

        request = ProtoOAAmendPositionSLTPReq(**request_fields)
        return self._request(request, timeout=5)

    # ------------------------------------------------------------------
    # Order placement / closing (event-correlated, no direct Res)
    # ------------------------------------------------------------------

    def new_market_order(self, symbol: str, api_volume: int, trade_side_enum: int, comment: str = "", label: str = "") -> Any:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType

        symbol_id = self.resolve_symbol_id(symbol)
        client_order_id = uuid.uuid4().hex[:32]

        wait_queue: "queue.Queue" = queue.Queue(maxsize=1)
        with self._state_lock:
            self._order_waiters[client_order_id] = wait_queue

        try:
            request = ProtoOANewOrderReq(
                ctidTraderAccountId=self.ctid_trader_account_id,
                symbolId=symbol_id,
                orderType=ProtoOAOrderType.MARKET,
                tradeSide=trade_side_enum,
                volume=api_volume,
                comment=comment or "",
                label=label or "",
                clientOrderId=client_order_id,
            )
            self._fire_and_forget(request)

            deadline = time.time() + EXECUTION_TIMEOUT_SECONDS
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise TimeoutError(
                        f"Timed out waiting for execution confirmation on order {client_order_id} ({symbol})"
                    )
                try:
                    event = wait_queue.get(timeout=remaining)
                except queue.Empty:
                    raise TimeoutError(
                        f"Timed out waiting for execution confirmation on order {client_order_id} ({symbol})"
                    )
                if event.executionType in TERMINAL_EXECUTION_TYPES:
                    return event
        finally:
            with self._state_lock:
                self._order_waiters.pop(client_order_id, None)

    def close_position(self, position_id: int, api_volume: int) -> Any:
        from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAClosePositionReq

        wait_queue: "queue.Queue" = queue.Queue(maxsize=1)
        with self._state_lock:
            self._close_waiters[position_id] = wait_queue

        try:
            request = ProtoOAClosePositionReq(
                ctidTraderAccountId=self.ctid_trader_account_id,
                positionId=position_id,
                volume=api_volume,
            )
            self._fire_and_forget(request)

            deadline = time.time() + EXECUTION_TIMEOUT_SECONDS
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise TimeoutError(
                        f"Timed out waiting for execution confirmation on close of position {position_id}"
                    )
                try:
                    event = wait_queue.get(timeout=remaining)
                except queue.Empty:
                    raise TimeoutError(
                        f"Timed out waiting for execution confirmation on close of position {position_id}"
                    )
                if event.executionType in TERMINAL_EXECUTION_TYPES:
                    return event
        finally:
            with self._state_lock:
                self._close_waiters.pop(position_id, None)

    # ------------------------------------------------------------------
    # Low-level send helpers
    # ------------------------------------------------------------------

    def _request(self, message, timeout: int = DEFAULT_TIMEOUT_SECONDS, _retried: bool = False) -> Any:
        """Send a request that has a matching Res message and block for the response."""
        from ctrader_open_api import Protobuf
        from twisted.internet import reactor
        from twisted.internet.threads import blockingCallFromThread

        if self._client is None:
            raise RuntimeError("cTrader client is not connected.")

        raw_response = blockingCallFromThread(
            reactor, self._client.send, message, None, timeout
        )
        response = Protobuf.extract(raw_response)

        if not _retried and self._is_auth_expired_error(response):
            logger.warning("cTrader access token expired mid-session; refreshing and retrying request once.")
            self._refresh_access_token()
            self._authenticate_account()
            return self._request(message, timeout=timeout, _retried=True)

        self._raise_if_error(response)
        return response

    @staticmethod
    def _is_auth_expired_error(response: Any) -> bool:
        return (
            response.__class__.__name__ == "ProtoOAErrorRes"
            and getattr(response, "errorCode", None) == AUTH_TOKEN_EXPIRED_ERROR_CODE
        )

    def _fire_and_forget(self, message, _retried: bool = False) -> None:
        """Send a request that has no matching Res (order/close); ignore ack timeout, rely on events."""
        from twisted.internet import reactor
        from twisted.internet.threads import blockingCallFromThread

        if self._client is None:
            raise RuntimeError("cTrader client is not connected.")

        try:
            raw_response = blockingCallFromThread(
                reactor, self._client.send, message, None, 3
            )
            from ctrader_open_api import Protobuf

            response = Protobuf.extract(raw_response)

            if not _retried and self._is_auth_expired_error(response):
                logger.warning("cTrader access token expired mid-session; refreshing and retrying order request once.")
                self._refresh_access_token()
                self._authenticate_account()
                self._fire_and_forget(message, _retried=True)
                return

            self._raise_if_error(response)
        except TimeoutError:
            # Expected: order/close confirmation comes via ExecutionEvent, not a Res.
            pass

    @staticmethod
    def _raise_if_error(response: Any) -> None:
        if response.__class__.__name__ == "ProtoOAErrorRes":
            raise RuntimeError(f"cTrader error [{response.errorCode}]: {response.description}")

    # ------------------------------------------------------------------
    # Incoming message dispatch (runs on the reactor thread)
    # ------------------------------------------------------------------

    def _on_message(self, _client, message) -> None:
        try:
            from ctrader_open_api import Protobuf

            payload = Protobuf.extract(message)
            type_name = payload.__class__.__name__

            if type_name == "ProtoOASpotEvent":
                self._handle_spot_event(payload)
            elif type_name == "ProtoOAExecutionEvent":
                self._handle_execution_event(payload)
            elif type_name in ("ProtoOAAccountDisconnectEvent", "ProtoOAClientDisconnectEvent"):
                logger.warning(f"cTrader disconnect event received: {type_name}")
                with self._state_lock:
                    self._account_authenticated = False
        except Exception as error:
            logger.warning(f"Error handling incoming cTrader message: {error}")

    def _handle_spot_event(self, event: Any) -> None:
        with self._state_lock:
            spot = self._spot_cache.setdefault(event.symbolId, SpotPrice())
            if event.bid:
                spot.bid = event.bid / PRICE_SCALE
            if event.ask:
                spot.ask = event.ask / PRICE_SCALE
            spot.timestamp = event.timestamp

    def set_execution_event_callback(self, callback) -> None:
        """Register a callback invoked for every incoming ProtoOAExecutionEvent."""
        self._execution_event_callback = callback

    def _handle_execution_event(self, event: Any) -> None:
        if self._execution_event_callback:
            self._execution_event_callback(event)

        client_order_id = getattr(event.order, "clientOrderId", "") if event.HasField("order") else ""
        position_id = event.position.positionId if event.HasField("position") else None

        with self._state_lock:
            if client_order_id and client_order_id in self._order_waiters:
                try:
                    self._order_waiters[client_order_id].put_nowait(event)
                except queue.Full:
                    pass
                return

            if position_id is not None and position_id in self._close_waiters:
                try:
                    self._close_waiters[position_id].put_nowait(event)
                except queue.Full:
                    pass
                return

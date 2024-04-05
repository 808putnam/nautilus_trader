# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2024 808putnam All rights reserved.
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

import asyncio
from decimal import Decimal

import pandas as pd

from nautilus_trader.adapters.phoenix.common.constants import PHOENIX_VENUE
from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixEnumParser
from nautilus_trader.adapters.phoenix.common.enums import PhoenixErrorCode
from nautilus_trader.adapters.phoenix.common.enums import PhoenixTimeInForce
from nautilus_trader.adapters.phoenix.common.schemas.account import PhoenixOrder
from nautilus_trader.adapters.phoenix.common.schemas.account import PhoenixUserTrade
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbol
from nautilus_trader.adapters.phoenix.common.schemas.user import PhoenixListenKey
from nautilus_trader.adapters.phoenix.config import PhoenixExecClientConfig
from nautilus_trader.adapters.phoenix.http.account import PhoenixAccountHttpAPI
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.error import PhoenixError
from nautilus_trader.adapters.phoenix.http.market import PhoenixMarketHttpAPI
from nautilus_trader.adapters.phoenix.http.user import PhoenixUserDataHttpAPI
from nautilus_trader.adapters.phoenix.websocket.client import PhoenixWebSocketClient
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.datetime import nanos_to_millis
from nautilus_trader.core.datetime import secs_to_millis
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.messages import CancelAllOrders
from nautilus_trader.execution.messages import CancelOrder
from nautilus_trader.execution.messages import ModifyOrder
from nautilus_trader.execution.messages import SubmitOrder
from nautilus_trader.execution.messages import SubmitOrderList
from nautilus_trader.execution.reports import FillReport
from nautilus_trader.execution.reports import OrderStatusReport
from nautilus_trader.execution.reports import PositionStatusReport
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderType
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.enums import TrailingOffsetType
from nautilus_trader.model.enums import TriggerType
from nautilus_trader.model.enums import trailing_offset_type_to_str
from nautilus_trader.model.enums import trigger_type_to_str
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.orders import LimitOrder
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.model.orders import Order
from nautilus_trader.model.orders import StopLimitOrder
from nautilus_trader.model.orders import StopMarketOrder
from nautilus_trader.model.orders import TrailingStopMarketOrder
from nautilus_trader.model.position import Position


class PhoenixCommonExecutionClient(LiveExecutionClient):
    """
    Execution client providing common functionality for the `Phoenix` exchanges.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    client : PhoenixHttpClient
        The phoenix HTTP client.
    account : PhoenixAccountHttpAPI
        The phoenix Account HTTP API.
    market : PhoenixMarketHttpAPI
        The phoenix Market HTTP API.
    user : PhoenixUserHttpAPI
        The phoenix User HTTP API.
    enum_parser : PhoenixEnumParser
        The parser for Phoenix enums.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : PhoenixSpotInstrumentProvider
        The instrument provider.
    account_type : PhoenixAccountType
        The account type for the client.
    base_url_ws : str
        The base URL for the WebSocket client.
    config : PhoenixExecClientConfig
        The configuration for the client.

    Warnings
    --------
    This class should not be used directly, but through a concrete subclass.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: PhoenixHttpClient,
        account: PhoenixAccountHttpAPI,
        market: PhoenixMarketHttpAPI,
        user: PhoenixUserDataHttpAPI,
        enum_parser: PhoenixEnumParser,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: InstrumentProvider,
        account_type: PhoenixAccountType,
        base_url_ws: str,
        config: PhoenixExecClientConfig,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=ClientId(PHOENIX_VENUE.value),
            venue=PHOENIX_VENUE,
            oms_type=OmsType.HEDGING if account_type.is_futures else OmsType.NETTING,
            instrument_provider=instrument_provider,
            account_type=AccountType.CASH if account_type.is_spot else AccountType.MARGIN,
            base_currency=None,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )

        # Configuration
        self._phoenix_account_type = account_type
        self._use_gtd = config.use_gtd
        self._use_reduce_only = config.use_reduce_only
        self._use_position_ids = config.use_position_ids
        self._treat_expired_as_canceled = config.treat_expired_as_canceled
        self._log.info(f"Account type: {self._phoenix_account_type.value}.", LogColor.BLUE)
        self._log.info(f"{config.use_gtd=}", LogColor.BLUE)
        self._log.info(f"{config.use_reduce_only=}", LogColor.BLUE)
        self._log.info(f"{config.use_position_ids=}", LogColor.BLUE)
        self._log.info(f"{config.treat_expired_as_canceled=}", LogColor.BLUE)
        self._log.info(f"{config.max_retries=}", LogColor.BLUE)
        self._log.info(f"{config.retry_delay=}", LogColor.BLUE)

        self._set_account_id(AccountId(f"{PHOENIX_VENUE.value}-spot-master"))

        # Enum parser
        self._enum_parser = enum_parser

        # Http API
        self._http_client = client
        self._http_account = account
        self._http_market = market
        self._http_user = user

        # Listen keys
        self._ping_listen_keys_interval: int = 60 * 5  # Once every 5 mins (hardcode)
        self._ping_listen_keys_task: asyncio.Task | None = None
        self._listen_key: str | None = None

        # WebSocket API
        self._ws_client = PhoenixWebSocketClient(
            clock=clock,
            handler=self._handle_user_ws_message,
            handler_reconnect=None,
            base_url=base_url_ws,
            loop=self._loop,
        )

        # Hot caches
        self._instrument_ids: dict[str, InstrumentId] = {}
        self._generate_order_status_retries: dict[ClientOrderId, int] = {}
        self._modifying_orders: dict[ClientOrderId, VenueOrderId] = {}

        # Order submission method hashmap
        self._submit_order_method = {
            OrderType.MARKET: self._submit_market_order,
            OrderType.LIMIT: self._submit_limit_order,
            OrderType.STOP_LIMIT: self._submit_stop_limit_order,
            OrderType.LIMIT_IF_TOUCHED: self._submit_stop_limit_order,
            OrderType.STOP_MARKET: self._submit_stop_market_order,
            OrderType.MARKET_IF_TOUCHED: self._submit_stop_market_order,
            OrderType.TRAILING_STOP_MARKET: self._submit_trailing_stop_market_order,
        }

        self._recv_window = 5_000

        # Retry logic (hard coded for now)
        self._max_retries: int = config.max_retries or 0
        self._retry_delay: float = config.retry_delay or 1.0
        self._retry_errors: set[PhoenixErrorCode] = {
            PhoenixErrorCode.DISCONNECTED,
            PhoenixErrorCode.TOO_MANY_REQUESTS,  # Short retry delays may result in bans
            PhoenixErrorCode.TIMEOUT,
            PhoenixErrorCode.SERVER_BUSY,
            PhoenixErrorCode.INVALID_TIMESTAMP,
            PhoenixErrorCode.CANCEL_REJECTED,
            PhoenixErrorCode.ME_RECVWINDOW_REJECT,
        }

        self._order_retries: dict[ClientOrderId, int] = {}

        self._log.info(f"Base URL HTTP {self._http_client.base_url}.", LogColor.BLUE)
        self._log.info(f"Base URL WebSocket {base_url_ws}.", LogColor.BLUE)

    @property
    def use_position_ids(self) -> bool:
        """
        Whether a `position_id` will be assigned to order events generated by the
        client.

        Returns
        -------
        bool

        """
        return self._use_position_ids

    @property
    def treat_expired_as_canceled(self) -> bool:
        """
        Whether the `EXPIRED` execution type is treated as a `CANCEL`.

        Returns
        -------
        bool

        """
        return self._treat_expired_as_canceled

    async def _connect(self) -> None:
        try:
            # Initialize instrument provider
            await self._instrument_provider.initialize()

            # Authenticate API key and update account(s)
            await self._update_account_state()

            # Get listen keys
            response: PhoenixListenKey = await self._http_user.create_listen_key()
        except PhoenixError as e:
            self._log.exception(f"Error on connect: {e.message}", e)
            return

        # Check Phoenix-Nautilus clock sync
        server_time: int = await self._http_market.request_server_time()
        self._log.info(f"Phoenix server time {server_time} UNIX (ms).")

        nautilus_time: int = self._clock.timestamp_ms()
        self._log.info(f"Nautilus clock time {nautilus_time} UNIX (ms).")

        # Setup WebSocket listen key
        self._listen_key = response.listenKey
        self._log.info(f"Listen key {self._listen_key}")
        self._ping_listen_keys_task = self.create_task(self._ping_listen_keys())

        # Connect WebSocket client
        await self._ws_client.subscribe_listen_key(self._listen_key)

    async def _update_account_state(self) -> None:
        # Replace method in child class
        raise NotImplementedError

    async def _ping_listen_keys(self) -> None:
        try:
            while True:
                self._log.debug(
                    f"Scheduled `ping_listen_keys` to run in "
                    f"{self._ping_listen_keys_interval}s.",
                )
                await asyncio.sleep(self._ping_listen_keys_interval)
                if self._listen_key:
                    self._log.debug(f"Pinging WebSocket listen key {self._listen_key}...")
                    await self._http_user.keepalive_listen_key(listen_key=self._listen_key)
        except asyncio.CancelledError:
            self._log.debug("Canceled `ping_listen_keys` task.")

    async def _disconnect(self) -> None:
        # Cancel tasks
        if self._ping_listen_keys_task:
            self._log.debug("Canceling `ping_listen_keys` task...")
            self._ping_listen_keys_task.cancel()
            self._ping_listen_keys_task = None

        await self._ws_client.disconnect()

    # -- EXECUTION REPORTS ------------------------------------------------------------------------

    async def generate_order_status_report(
        self,
        instrument_id: InstrumentId,
        client_order_id: ClientOrderId | None = None,
        venue_order_id: VenueOrderId | None = None,
    ) -> OrderStatusReport | None:
        PyCondition.false(
            client_order_id is None and venue_order_id is None,
            "both `client_order_id` and `venue_order_id` were `None`",
        )

        retries = self._generate_order_status_retries.get(client_order_id, 0)
        if retries > 3:
            self._log.error(
                f"Reached maximum retries 3/3 for generating OrderStatusReport for "
                f"{repr(client_order_id) if client_order_id else ''} "
                f"{repr(venue_order_id) if venue_order_id else ''}...",
            )
            return None

        self._log.info(
            f"Generating OrderStatusReport for "
            f"{repr(client_order_id) if client_order_id else ''} "
            f"{repr(venue_order_id) if venue_order_id else ''}...",
        )

        try:
            if venue_order_id:
                phoenix_order = await self._http_account.query_order(
                    symbol=instrument_id.symbol.value,
                    order_id=int(venue_order_id.value),
                )
            else:
                phoenix_order = await self._http_account.query_order(
                    symbol=instrument_id.symbol.value,
                    orig_client_order_id=(
                        client_order_id.value if client_order_id is not None else None
                    ),
                )
        except PhoenixError as e:
            retries += 1
            self._log.error(
                f"Cannot generate order status report for {client_order_id!r}: {e.message}. Retry {retries}/3",
            )
            self._generate_order_status_retries[client_order_id] = retries
            if not client_order_id:
                self._log.warning("Cannot retry without a client order ID.")
            else:
                order: Order | None = self._cache.order(client_order_id)
                if order is None:
                    self._log.warning("Order not found in cache.")
                    return None
                elif order.is_closed:
                    return None  # Nothing else to do

                if retries >= 3:
                    # Order will no longer be considered in-flight once this event is applied.
                    # We could pop the value out of the hashmap here, but better to leave it in
                    # so that there are no longer subsequent retries (we don't expect many of these).
                    self.generate_order_rejected(
                        strategy_id=order.strategy_id,
                        instrument_id=instrument_id,
                        client_order_id=client_order_id,
                        reason=str(e.message),
                        ts_event=self._clock.timestamp_ns(),
                    )
            return None  # Error now handled

        if not phoenix_order or (phoenix_order.origQty and Decimal(phoenix_order.origQty) == 0):
            # Cannot proceed to generating report
            self._log.error(
                f"Cannot generate `OrderStatusReport` for {client_order_id=!r}, {venue_order_id=!r}: "
                "order not found.",
            )
            return None

        report: OrderStatusReport = phoenix_order.parse_to_order_status_report(
            account_id=self.account_id,
            instrument_id=self._get_cached_instrument_id(phoenix_order.symbol),
            report_id=UUID4(),
            enum_parser=self._enum_parser,
            treat_expired_as_canceled=self._treat_expired_as_canceled,
            ts_init=self._clock.timestamp_ns(),
        )

        self._log.debug(f"Received {report}.")
        return report

    def _get_cache_active_symbols(self) -> set[str]:
        # Check cache for all active symbols
        open_orders: list[Order] = self._cache.orders_open(venue=self.venue)
        open_positions: list[Position] = self._cache.positions_open(venue=self.venue)
        active_symbols: set[str] = set()
        for o in open_orders:
            active_symbols.add(PhoenixSymbol(o.instrument_id.symbol.value))
        for p in open_positions:
            active_symbols.add(PhoenixSymbol(p.instrument_id.symbol.value))
        return active_symbols

    async def _get_phoenix_position_status_reports(
        self,
        symbol: str | None = None,
    ) -> list[PositionStatusReport]:
        # Implement in child class
        raise NotImplementedError

    async def _get_phoenix_active_position_symbols(
        self,
        symbol: str | None = None,
    ) -> set[str]:
        # Implement in child class
        raise NotImplementedError

    async def generate_order_status_reports(
        self,
        instrument_id: InstrumentId | None = None,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        open_only: bool = False,
    ) -> list[OrderStatusReport]:
        self._log.info("Requesting OrderStatusReports...")

        try:
            # Check Phoenix for all order active symbols
            symbol = instrument_id.symbol.value if instrument_id is not None else None
            active_symbols = self._get_cache_active_symbols()
            active_symbols.update(await self._get_phoenix_active_position_symbols(symbol))
            phoenix_open_orders = await self._http_account.query_open_orders(symbol)
            for order in phoenix_open_orders:
                active_symbols.add(order.symbol)
            # Get all orders for those active symbols
            phoenix_orders: list[PhoenixOrder] = []
            for symbol in active_symbols:
                # Here we don't pass a `start_time` or `end_time` as order reports appear to go
                # randomly missing when these are specified. We filter on the Nautilus side below.
                # Explicitly setting limit to the max lookback of 1000, in the future we should
                # add pagination.
                response = await self._http_account.query_all_orders(symbol=symbol, limit=1_000)
                phoenix_orders.extend(response)
        except PhoenixError as e:
            self._log.exception(f"Cannot generate OrderStatusReport: {e.message}", e)
            return []

        start_ms = secs_to_millis(start.timestamp()) if start is not None else None
        end_ms = secs_to_millis(end.timestamp()) if end is not None else None

        reports: list[OrderStatusReport] = []
        for order in phoenix_orders:
            if start_ms is not None and order.time < start_ms:
                continue  # Filter start on the Nautilus side
            if end_ms is not None and order.time > end_ms:
                continue  # Filter end on the Nautilus side
            if order.origQty and Decimal(order.origQty) == 0:
                continue  # Cannot parse zero quantity order (filter for Phoenix)
            report = order.parse_to_order_status_report(
                account_id=self.account_id,
                instrument_id=self._get_cached_instrument_id(order.symbol),
                report_id=UUID4(),
                enum_parser=self._enum_parser,
                treat_expired_as_canceled=self._treat_expired_as_canceled,
                ts_init=self._clock.timestamp_ns(),
            )
            self._log.debug(f"Received {reports}.")
            reports.append(report)

        len_reports = len(reports)
        plural = "" if len_reports == 1 else "s"
        self._log.info(f"Received {len(reports)} OrderStatusReport{plural}.")

        return reports

    async def generate_fill_reports(
        self,
        instrument_id: InstrumentId | None = None,
        venue_order_id: VenueOrderId | None = None,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
    ) -> list[FillReport]:
        self._log.info("Requesting FillReports...")

        try:
            # Check Phoenix for all trades on active symbols
            symbol = instrument_id.symbol.value if instrument_id is not None else None
            active_symbols = self._get_cache_active_symbols()
            active_symbols.update(await self._get_phoenix_active_position_symbols(symbol))
            phoenix_trades: list[PhoenixUserTrade] = []
            for symbol in active_symbols:
                response = await self._http_account.query_user_trades(
                    symbol=symbol,
                    start_time=secs_to_millis(start.timestamp()) if start is not None else None,
                    end_time=secs_to_millis(end.timestamp()) if end is not None else None,
                )
                phoenix_trades.extend(response)
        except PhoenixError as e:
            self._log.exception(f"Cannot generate FillReport: {e.message}", e)
            return []

        # Parse all Phoenix trades
        reports: list[FillReport] = []
        for trade in phoenix_trades:
            if trade.symbol is None:
                self._log.warning(f"No symbol for trade {trade}.")
                continue
            report = trade.parse_to_fill_report(
                account_id=self.account_id,
                instrument_id=self._get_cached_instrument_id(trade.symbol),
                report_id=UUID4(),
                ts_init=self._clock.timestamp_ns(),
                use_position_ids=self._use_position_ids,
            )
            self._log.debug(f"Received {report}.")
            reports.append(report)

        # Confirm sorting in ascending order
        reports = sorted(reports, key=lambda x: x.trade_id)

        len_reports = len(reports)
        plural = "" if len_reports == 1 else "s"
        self._log.info(f"Received {len(reports)} FillReport{plural}.")

        return reports

    async def generate_position_status_reports(
        self,
        instrument_id: InstrumentId | None = None,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
    ) -> list[PositionStatusReport]:
        self._log.info("Requesting PositionStatusReports...")

        try:
            symbol = instrument_id.symbol.value if instrument_id is not None else None
            reports = await self._get_phoenix_position_status_reports(symbol)
        except PhoenixError as e:
            self._log.exception(f"Cannot generate PositionStatusReport: {e.message}", e)
            return []

        len_reports = len(reports)
        plural = "" if len_reports == 1 else "s"
        self._log.info(f"Received {len(reports)} PositionStatusReport{plural}.")

        return reports

    # -- COMMAND HANDLERS -------------------------------------------------------------------------

    def _check_order_validity(self, order: Order) -> None:
        # Implement in child class
        raise NotImplementedError

    def _should_retry(self, error_code: PhoenixErrorCode, retries: int) -> bool:
        if (
            error_code not in self._retry_errors
            or not self._max_retries
            or retries > self._max_retries
        ):
            return False
        return True

    def _determine_time_in_force(self, order: Order) -> PhoenixTimeInForce:
        time_in_force = self._enum_parser.parse_internal_time_in_force(order.time_in_force)
        if time_in_force == TimeInForce.GTD and not self._use_gtd:
            time_in_force = TimeInForce.GTC
            self._log.info(
                f"Converted GTD `time_in_force` to GTC for {order.client_order_id}.",
                LogColor.BLUE,
            )
        return time_in_force

    def _determine_good_till_date(
        self,
        order: Order,
        time_in_force: PhoenixTimeInForce | None,
    ) -> int | None:
        if time_in_force is None or time_in_force != PhoenixTimeInForce.GTD:
            return None

        good_till_date = nanos_to_millis(order.expire_time_ns) if order.expire_time_ns else None
        if self._phoenix_account_type.is_spot_or_margin:
            good_till_date = None
            self._log.warning("Cannot set GTD time in force with `expiry_time` for Phoenix Spot.")
        return good_till_date

    def _determine_reduce_only(self, order: Order) -> bool:
        return order.is_reduce_only if self._use_reduce_only else False

    def _determine_reduce_only_str(self, order: Order) -> str | None:
        if self._phoenix_account_type.is_futures:
            return str(self._determine_reduce_only(order))
        return None

    async def _submit_order(self, command: SubmitOrder) -> None:
        await self._submit_order_inner(command.order)

    async def _submit_order_inner(self, order: Order) -> None:
        if order.is_closed:
            self._log.warning(f"Cannot submit already closed order {order}.")
            return

        # Check validity
        self._check_order_validity(order)
        self._log.debug(f"Submitting {order}.")

        # Generate event here to ensure correct ordering of events
        self.generate_order_submitted(
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            ts_event=self._clock.timestamp_ns(),
        )

        while True:
            try:
                await self._submit_order_method[order.order_type](order)
                self._order_retries.pop(order.client_order_id, None)
                break  # Successful request
            except KeyError:
                raise RuntimeError(f"unsupported order type, was {order.order_type}")
            except PhoenixError as e:
                error_code = PhoenixErrorCode(e.message["code"])

                retries = self._order_retries.get(order.client_order_id, 0) + 1
                self._order_retries[order.client_order_id] = retries

                if not self._should_retry(error_code, retries):
                    self.generate_order_rejected(
                        strategy_id=order.strategy_id,
                        instrument_id=order.instrument_id,
                        client_order_id=order.client_order_id,
                        reason=str(e.message),
                        ts_event=self._clock.timestamp_ns(),
                    )
                    break

                self._log.warning(
                    f"{error_code.name}: retrying {order.client_order_id!r} "
                    f"{retries}/{self._max_retries} in {self._retry_delay}s ...",
                )
                await asyncio.sleep(self._retry_delay)

    async def _submit_market_order(self, order: MarketOrder) -> None:
        await self._http_account.new_order(
            symbol=order.instrument_id.symbol.value,
            side=self._enum_parser.parse_internal_order_side(order.side),
            order_type=self._enum_parser.parse_internal_order_type(order),
            quantity=str(order.quantity),
            reduce_only=self._determine_reduce_only_str(order),
            new_client_order_id=order.client_order_id.value,
            recv_window=str(self._recv_window),
        )

    async def _submit_limit_order(self, order: LimitOrder) -> None:
        time_in_force = self._determine_time_in_force(order)
        if order.is_post_only and self._phoenix_account_type.is_spot_or_margin:
            time_in_force = None
        elif order.is_post_only and self._phoenix_account_type.is_futures:
            time_in_force = PhoenixTimeInForce.GTX

        await self._http_account.new_order(
            symbol=order.instrument_id.symbol.value,
            side=self._enum_parser.parse_internal_order_side(order.side),
            order_type=self._enum_parser.parse_internal_order_type(order),
            time_in_force=time_in_force,
            good_till_date=self._determine_good_till_date(order, time_in_force),
            quantity=str(order.quantity),
            price=str(order.price),
            iceberg_qty=str(order.display_qty) if order.display_qty is not None else None,
            reduce_only=self._determine_reduce_only_str(order),
            new_client_order_id=order.client_order_id.value,
            recv_window=str(self._recv_window),
        )

    async def _submit_stop_limit_order(self, order: StopLimitOrder) -> None:
        if self._phoenix_account_type.is_spot_or_margin:
            working_type = None
        elif order.trigger_type in (TriggerType.DEFAULT, TriggerType.LAST_TRADE):
            working_type = "CONTRACT_PRICE"
        elif order.trigger_type == TriggerType.MARK_PRICE:
            working_type = "MARK_PRICE"
        else:
            self._log.error(
                f"Cannot submit order: invalid `order.trigger_type`, was "
                f"{trigger_type_to_str(order.trigger_price)}. {order}",
            )
            return

        time_in_force = self._determine_time_in_force(order)
        await self._http_account.new_order(
            symbol=order.instrument_id.symbol.value,
            side=self._enum_parser.parse_internal_order_side(order.side),
            order_type=self._enum_parser.parse_internal_order_type(order),
            time_in_force=time_in_force,
            good_till_date=self._determine_good_till_date(order, time_in_force),
            quantity=str(order.quantity),
            price=str(order.price),
            stop_price=str(order.trigger_price),
            working_type=working_type,
            iceberg_qty=str(order.display_qty) if order.display_qty is not None else None,
            reduce_only=self._determine_reduce_only_str(order),
            new_client_order_id=order.client_order_id.value,
            recv_window=str(self._recv_window),
        )

    async def _submit_order_list(self, command: SubmitOrderList) -> None:
        for order in command.order_list.orders:
            self.generate_order_submitted(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                ts_event=self._clock.timestamp_ns(),
            )

        for order in command.order_list.orders:
            if order.linked_order_ids:  # TODO(cs): Implement
                self._log.warning(f"Cannot yet handle OCO conditional orders, {order}.")
            await self._submit_order_inner(order)

    async def _submit_stop_market_order(self, order: StopMarketOrder) -> None:
        if self._phoenix_account_type.is_spot_or_margin:
            working_type = None
        elif order.trigger_type in (TriggerType.DEFAULT, TriggerType.LAST_TRADE):
            working_type = "CONTRACT_PRICE"
        elif order.trigger_type == TriggerType.MARK_PRICE:
            working_type = "MARK_PRICE"
        else:
            self._log.error(
                f"Cannot submit order: invalid `order.trigger_type`, was "
                f"{trigger_type_to_str(order.trigger_price)}. {order}",
            )
            return

        time_in_force = self._determine_time_in_force(order)
        await self._http_account.new_order(
            symbol=order.instrument_id.symbol.value,
            side=self._enum_parser.parse_internal_order_side(order.side),
            order_type=self._enum_parser.parse_internal_order_type(order),
            time_in_force=time_in_force,
            good_till_date=self._determine_good_till_date(order, time_in_force),
            quantity=str(order.quantity),
            stop_price=str(order.trigger_price),
            working_type=working_type,
            reduce_only=self._determine_reduce_only_str(order),
            new_client_order_id=order.client_order_id.value,
            recv_window=str(self._recv_window),
        )

    async def _submit_trailing_stop_market_order(self, order: TrailingStopMarketOrder) -> None:
        if order.trigger_type in (TriggerType.DEFAULT, TriggerType.LAST_TRADE):
            working_type = "CONTRACT_PRICE"
        elif order.trigger_type == TriggerType.MARK_PRICE:
            working_type = "MARK_PRICE"
        else:
            self._log.error(
                f"Cannot submit order: invalid `order.trigger_type`, was "
                f"{trigger_type_to_str(order.trigger_price)}. {order}",
            )
            return

        if order.trailing_offset_type != TrailingOffsetType.BASIS_POINTS:
            self._log.error(
                f"Cannot submit order: invalid `order.trailing_offset_type`, was "
                f"{trailing_offset_type_to_str(order.trailing_offset_type)} (use `BASIS_POINTS`). "
                f"{order}",
            )
            return

        # Ensure activation price
        activation_price: Price | None = order.trigger_price
        if not activation_price:
            quote = self._cache.quote_tick(order.instrument_id)
            trade = self._cache.trade_tick(order.instrument_id)
            if quote:
                if order.side == OrderSide.BUY:
                    activation_price = quote.ask_price
                elif order.side == OrderSide.SELL:
                    activation_price = quote.bid_price
            elif trade:
                activation_price = trade.price
            else:
                self._log.error(
                    "Cannot submit order: no trigger price specified for Phoenix activation price "
                    f"and could not find quotes or trades for {order.instrument_id}",
                )

        time_in_force = self._determine_time_in_force(order)
        await self._http_account.new_order(
            symbol=order.instrument_id.symbol.value,
            side=self._enum_parser.parse_internal_order_side(order.side),
            order_type=self._enum_parser.parse_internal_order_type(order),
            time_in_force=time_in_force,
            good_till_date=self._determine_good_till_date(order, time_in_force),
            quantity=str(order.quantity),
            activation_price=str(activation_price),
            callback_rate=str(order.trailing_offset / 100),
            working_type=working_type,
            reduce_only=self._determine_reduce_only_str(order),
            new_client_order_id=order.client_order_id.value,
            recv_window=str(self._recv_window),
        )

    def _get_cached_instrument_id(self, symbol: str) -> InstrumentId:
        # Parse instrument ID
        nautilus_symbol: str = PhoenixSymbol(symbol).parse_as_nautilus(
            self._phoenix_account_type,
        )
        instrument_id: InstrumentId | None = self._instrument_ids.get(nautilus_symbol)
        if not instrument_id:
            instrument_id = InstrumentId(Symbol(nautilus_symbol), PHOENIX_VENUE)
            self._instrument_ids[nautilus_symbol] = instrument_id
        return instrument_id

    async def _modify_order(self, command: ModifyOrder) -> None:
        if self._phoenix_account_type.is_spot_or_margin:
            self._log.error(
                "Cannot modify order: only supported for `USDT_FUTURE` and `COIN_FUTURE` account types.",
            )
            return

        order: Order | None = self._cache.order(command.client_order_id)
        if order is None:
            self._log.error(f"{command.client_order_id!r} not found to modify.")
            return

        if order.order_type != OrderType.LIMIT:
            self._log.error(
                "Cannot modify order: "
                f"only LIMIT orders supported by the venue (was {order.type_string()}).",
            )
            return

        while True:
            try:
                await self._http_account.modify_order(
                    symbol=order.instrument_id.symbol.value,
                    order_id=int(order.venue_order_id.value) if order.venue_order_id else None,
                    side=self._enum_parser.parse_internal_order_side(order.side),
                    quantity=str(command.quantity) if command.quantity else str(order.quantity),
                    price=str(command.price) if command.price else str(order.price),
                )
                self._order_retries.pop(command.client_order_id, None)
                break  # Successful request
            except PhoenixError as e:
                error_code = PhoenixErrorCode(e.message["code"])

                retries = self._order_retries.get(command.client_order_id, 0) + 1
                self._order_retries[command.client_order_id] = retries

                if not self._should_retry(error_code, retries):
                    break

                self._log.warning(
                    f"{error_code.name}: retrying {command.client_order_id!r} "
                    f"{retries}/{self._max_retries} in {self._retry_delay}s ...",
                )
                await asyncio.sleep(self._retry_delay)

    async def _cancel_order(self, command: CancelOrder) -> None:
        while True:
            try:
                await self._cancel_order_single(
                    instrument_id=command.instrument_id,
                    client_order_id=command.client_order_id,
                    venue_order_id=command.venue_order_id,
                )
                self._order_retries.pop(command.client_order_id, None)
                break  # Successful request
            except PhoenixError as e:
                error_code = PhoenixErrorCode(e.message["code"])

                retries = self._order_retries.get(command.client_order_id, 0) + 1
                self._order_retries[command.client_order_id] = retries

                if not self._should_retry(error_code, retries):
                    break

                self._log.warning(
                    f"{error_code.name}: retrying {command.client_order_id!r} "
                    f"{retries}/{self._max_retries} in {self._retry_delay}s ...",
                )
                await asyncio.sleep(self._retry_delay)

    async def _cancel_all_orders(self, command: CancelAllOrders) -> None:
        open_orders_strategy: list[Order] = self._cache.orders_open(
            instrument_id=command.instrument_id,
            strategy_id=command.strategy_id,
        )
        for order in open_orders_strategy:
            if order.is_pending_cancel:
                continue  # Already pending cancel

        # Check total orders for instrument
        open_orders_total_count = self._cache.orders_open_count(
            instrument_id=command.instrument_id,
        )

        try:
            if open_orders_total_count == len(open_orders_strategy):
                await self._http_account.cancel_all_open_orders(
                    symbol=command.instrument_id.symbol.value,
                )
            else:
                for order in open_orders_strategy:
                    await self._cancel_order_single(
                        instrument_id=order.instrument_id,
                        client_order_id=order.client_order_id,
                        venue_order_id=order.venue_order_id,
                    )
        except PhoenixError as e:
            if "Unknown order sent" in e.message:
                self._log.info(
                    "No open orders to cancel according to Phoenix.",
                    LogColor.GREEN,
                )
            else:
                self._log.exception(f"Cannot cancel open orders: {e.message}", e)

    async def _cancel_order_single(
        self,
        instrument_id: InstrumentId,
        client_order_id: ClientOrderId,
        venue_order_id: VenueOrderId | None,
    ) -> None:
        order: Order | None = self._cache.order(client_order_id)
        if order is None:
            self._log.error(f"{client_order_id!r} not found to cancel.")
            return

        if order.is_closed:
            self._log.warning(
                f"CancelOrder command for {client_order_id!r} when order already {order.status_string()} "
                "(will not send to exchange).",
            )
            return

        try:
            await self._http_account.cancel_order(
                symbol=instrument_id.symbol.value,
                order_id=int(venue_order_id.value) if venue_order_id else None,
                orig_client_order_id=client_order_id.value if client_order_id else None,
            )
        except PhoenixError as e:
            error_code = PhoenixErrorCode(e.message["code"])
            if error_code == PhoenixErrorCode.CANCEL_REJECTED:
                self._log.warning(f"Cancel rejected: {e.message}.")
            else:
                self._log.exception(
                    f"Cannot cancel order "
                    f"{client_order_id!r}, "
                    f"{venue_order_id!r}: "
                    f"{e.message}",
                    e,
                )

    # -- WEBSOCKET EVENT HANDLERS --------------------------------------------------------------------

    def _handle_user_ws_message(self, raw: bytes) -> None:
        # Implement in child class
        raise NotImplementedError

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

from decimal import Decimal

import msgspec

from nautilus_trader.adapters.phoenix.common.enums import PhoenixEnumParser
from nautilus_trader.adapters.phoenix.common.enums import PhoenixExecutionType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixOrderSide
from nautilus_trader.adapters.phoenix.common.enums import PhoenixOrderStatus
from nautilus_trader.adapters.phoenix.common.enums import PhoenixOrderType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixTimeInForce
from nautilus_trader.adapters.phoenix.common.execution import PhoenixCommonExecutionClient
from nautilus_trader.adapters.phoenix.spot.enums import PhoenixSpotEventType
from nautilus_trader.core.datetime import millis_to_nanos
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.reports import OrderStatusReport
from nautilus_trader.model.enums import LiquiditySide
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.enums import TrailingOffsetType
from nautilus_trader.model.enums import TriggerType
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.objects import AccountBalance
from nautilus_trader.model.objects import Currency
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


################################################################################
# WebSocket messages
################################################################################


class PhoenixSpotUserMsgData(msgspec.Struct, frozen=True):
    """
    Inner struct for execution WebSocket messages from `Phoenix`
    """

    e: PhoenixSpotEventType


class PhoenixSpotUserMsgWrapper(msgspec.Struct, frozen=True):
    """
    Provides a wrapper for execution WebSocket messages from `Phoenix`.
    """

    stream: str
    data: PhoenixSpotUserMsgData


class PhoenixSpotBalance(msgspec.Struct, frozen=True):
    """
    Inner struct for `Phoenix Spot/Margin` balances.
    """

    a: str  # Asset
    f: str  # Free
    l: str  # Locked

    def parse_to_account_balance(self) -> AccountBalance:
        currency = Currency.from_str(self.a)
        free = Decimal(self.f)
        locked = Decimal(self.l)
        total: Decimal = free + locked
        return AccountBalance(
            total=Money(total, currency),
            locked=Money(locked, currency),
            free=Money(free, currency),
        )


class PhoenixSpotAccountUpdateMsg(msgspec.Struct, frozen=True):
    """
    WebSocket message for `Phoenix Spot/Margin` Account Update events.
    """

    e: str  # Event Type
    E: int  # Event Time
    u: int  # Transaction Time
    B: list[PhoenixSpotBalance]

    def parse_to_account_balances(self) -> list[AccountBalance]:
        return [balance.parse_to_account_balance() for balance in self.B]

    def handle_account_update(self, exec_client: PhoenixCommonExecutionClient):
        """
        Handle PhoenixSpotAccountUpdateMsg as payload of outboundAccountPosition.
        """
        exec_client.generate_account_state(
            balances=self.parse_to_account_balances(),
            margins=[],
            reported=True,
            ts_event=millis_to_nanos(self.u),
        )


class PhoenixSpotAccountUpdateWrapper(msgspec.Struct, frozen=True):
    """
    WebSocket message wrapper for `Phoenix Spot/Margin` Account Update events.
    """

    stream: str
    data: PhoenixSpotAccountUpdateMsg


class PhoenixSpotOrderUpdateData(msgspec.Struct, kw_only=True):
    """
    WebSocket message 'inner struct' for `Phoenix Spot/Margin` Order Update events.
    """

    e: PhoenixSpotEventType
    E: int  # Event time
    s: str  # Symbol
    c: str  # Client order ID
    S: PhoenixOrderSide
    o: PhoenixOrderType
    f: PhoenixTimeInForce
    q: str  # Original Quantity
    p: str  # Original Price
    P: str  # Stop price
    F: str  # Iceberg quantity
    g: int  # Order list ID
    C: str  # Original client order ID; This is the ID of the order being canceled
    x: PhoenixExecutionType
    X: PhoenixOrderStatus
    r: str  # Order reject reason; will be an error code
    i: int  # Order ID
    l: str  # Order Last Filled Quantity
    z: str  # Order Filled Accumulated Quantity
    L: str  # Last Filled Price
    n: str | None = None  # Commission, will not push if no commission
    N: str | None = None  # Commission Asset, will not push if no commission
    T: int  # Order Trade Time
    t: int  # Trade ID
    I: int  # Ignore
    w: bool  # Is the order on the book?
    m: bool  # Is trade the maker side
    M: bool  # Ignore
    O: int  # Order creation time
    Z: str  # Cumulative quote asset transacted quantity
    Y: str  # Last quote asset transacted quantity (i.e. lastPrice * lastQty)
    Q: str  # Quote Order Qty

    def parse_to_order_status_report(
        self,
        account_id: AccountId,
        instrument_id: InstrumentId,
        client_order_id: ClientOrderId,
        venue_order_id: VenueOrderId,
        ts_event: int,
        ts_init: int,
        enum_parser: PhoenixEnumParser,
    ) -> OrderStatusReport:
        price = Price.from_str(self.p) if self.p is not None else None
        trigger_price = Price.from_str(self.P) if self.P is not None else None
        order_side = OrderSide.BUY if self.S == PhoenixOrderSide.BUY else OrderSide.SELL
        post_only = self.f == PhoenixTimeInForce.GTX
        display_qty = (
            Quantity.from_str(
                str(Decimal(self.q) - Decimal(self.F)),
            )
            if self.F is not None
            else None
        )

        return OrderStatusReport(
            account_id=account_id,
            instrument_id=instrument_id,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
            order_side=order_side,
            order_type=enum_parser.parse_phoenix_order_type(self.o),
            time_in_force=enum_parser.parse_phoenix_time_in_force(self.f),
            order_status=OrderStatus.ACCEPTED,
            price=price,
            trigger_price=trigger_price,
            trigger_type=TriggerType.LAST_TRADE,
            trailing_offset=None,
            trailing_offset_type=TrailingOffsetType.NO_TRAILING_OFFSET,
            quantity=Quantity.from_str(self.q),
            filled_qty=Quantity.from_str(self.z),
            display_qty=display_qty,
            avg_px=None,
            post_only=post_only,
            reduce_only=False,
            report_id=UUID4(),
            ts_accepted=ts_event,
            ts_last=ts_event,
            ts_init=ts_init,
        )

    def handle_execution_report(
        self,
        exec_client: PhoenixCommonExecutionClient,
    ):
        """
        Handle PhoenixSpotOrderUpdateData as payload of executionReport event.
        """
        client_order_id_str: str = self.c
        if not client_order_id_str or not client_order_id_str.startswith("O"):
            client_order_id_str = self.C
        client_order_id = ClientOrderId(client_order_id_str)
        ts_event = millis_to_nanos(self.T)
        venue_order_id = VenueOrderId(str(self.i))
        instrument_id = exec_client._get_cached_instrument_id(self.s)
        strategy_id = exec_client._cache.strategy_id_for_order(client_order_id)
        if strategy_id is None:
            report = self.parse_to_order_status_report(
                account_id=exec_client.account_id,
                instrument_id=instrument_id,
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                ts_event=ts_event,
                ts_init=exec_client._clock.timestamp_ns(),
                enum_parser=exec_client._enum_parser,
            )
            exec_client._send_order_status_report(report)
        elif self.x == PhoenixExecutionType.NEW:
            exec_client.generate_order_accepted(
                strategy_id=strategy_id,
                instrument_id=instrument_id,
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                ts_event=ts_event,
            )
        elif self.x == PhoenixExecutionType.TRADE:
            instrument = exec_client._instrument_provider.find(instrument_id=instrument_id)

            # Determine commission
            commission_asset: str = self.N
            commission_amount: str = self.n
            if commission_asset is not None:
                commission = Money.from_str(f"{commission_amount} {commission_asset}")
            else:
                # Phoenix typically charges commission as base asset or BNB
                commission = Money(0, instrument.base_currency)

            exec_client.generate_order_filled(
                strategy_id=strategy_id,
                instrument_id=instrument_id,
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                venue_position_id=None,  # NETTING accounts
                trade_id=TradeId(str(self.t)),  # Trade ID
                order_side=exec_client._enum_parser.parse_phoenix_order_side(self.S),
                order_type=exec_client._enum_parser.parse_phoenix_order_type(self.o),
                last_qty=Quantity.from_str(self.l),
                last_px=Price.from_str(self.L),
                quote_currency=instrument.quote_currency,
                commission=commission,
                liquidity_side=LiquiditySide.MAKER if self.m else LiquiditySide.TAKER,
                ts_event=ts_event,
            )
        elif self.x == PhoenixExecutionType.CANCELED:
            exec_client.generate_order_canceled(
                strategy_id=strategy_id,
                instrument_id=instrument_id,
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                ts_event=ts_event,
            )
        elif self.x == PhoenixExecutionType.EXPIRED:
            exec_client.generate_order_expired(
                strategy_id=strategy_id,
                instrument_id=instrument_id,
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                ts_event=ts_event,
            )
        else:
            # Event not handled
            exec_client._log.warning(f"Received unhandled {self}")


class PhoenixSpotOrderUpdateWrapper(msgspec.Struct, frozen=True):
    """
    WebSocket message wrapper for `Phoenix Spot/Margin` Order Update events.
    """

    stream: str
    data: PhoenixSpotOrderUpdateData

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
from nautilus_trader.adapters.phoenix.common.enums import PhoenixOrderSide
from nautilus_trader.adapters.phoenix.common.enums import PhoenixOrderStatus
from nautilus_trader.adapters.phoenix.common.enums import PhoenixOrderType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixTimeInForce
from nautilus_trader.core.datetime import millis_to_nanos
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.reports import FillReport
from nautilus_trader.execution.reports import OrderStatusReport
from nautilus_trader.model.enums import ContingencyType
from nautilus_trader.model.enums import LiquiditySide
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.enums import TrailingOffsetType
from nautilus_trader.model.enums import TriggerType
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import OrderListId
from nautilus_trader.model.identifiers import PositionId
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.objects import Currency
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


################################################################################
# HTTP responses
################################################################################


class PhoenixUserTrade(msgspec.Struct, frozen=True):
    """
    HTTP response from `Phoenix Spot/Margin` `GET /api/v3/myTrades` HTTP response from
    `Phoenix USD-M Futures` `GET /fapi/v1/userTrades` HTTP response from `Phoenix COIN-M
    Futures` `GET /dapi/v1/userTrades`
    """

    commission: str
    commissionAsset: str
    price: str
    qty: str

    # Parameters not present in 'fills' list (see FULL response of PhoenixOrder)
    symbol: str | None = None
    id: int | None = None
    orderId: int | None = None
    time: int | None = None
    quoteQty: str | None = None  # SPOT/MARGIN & USD-M FUTURES only

    # Parameters in SPOT/MARGIN only:
    orderListId: int | None = None  # unless OCO, the value will always be -1
    isBuyer: bool | None = None
    isMaker: bool | None = None
    isBestMatch: bool | None = None
    tradeId: int | None = None  # only in PhoenixOrder FULL response

    # Parameters in FUTURES only:
    buyer: bool | None = None
    maker: bool | None = None
    realizedPnl: str | None = None
    side: PhoenixOrderSide | None = None
    positionSide: str | None = None
    baseQty: str | None = None  # COIN-M FUTURES only
    pair: str | None = None  # COIN-M FUTURES only

    def parse_to_fill_report(
        self,
        account_id: AccountId,
        instrument_id: InstrumentId,
        report_id: UUID4,
        ts_init: int,
        use_position_ids: bool = True,
    ) -> FillReport:
        venue_position_id: PositionId | None = None
        if self.positionSide is not None and use_position_ids:
            venue_position_id = PositionId(f"{instrument_id}-{self.positionSide}")

        order_side = OrderSide.BUY if self.isBuyer or self.buyer else OrderSide.SELL
        liquidity_side = LiquiditySide.MAKER if self.isMaker or self.maker else LiquiditySide.TAKER

        return FillReport(
            account_id=account_id,
            instrument_id=instrument_id,
            venue_order_id=VenueOrderId(str(self.orderId)),
            venue_position_id=venue_position_id,
            trade_id=TradeId(str(self.id)),
            order_side=order_side,
            last_qty=Quantity.from_str(self.qty),
            last_px=Price.from_str(self.price),
            liquidity_side=liquidity_side,
            ts_event=millis_to_nanos(self.time),
            commission=Money(self.commission, Currency.from_str(self.commissionAsset)),
            report_id=report_id,
            ts_init=ts_init,
        )


class PhoenixOrder(msgspec.Struct, frozen=True):
    """
    HTTP response from `Phoenix Spot/Margin` `GET /api/v3/order` HTTP response from
    `Phoenix USD-M Futures` `GET /fapi/v1/order` HTTP response from `Phoenix COIN-M
    Futures` `GET /dapi/v1/order`
    """

    symbol: str
    orderId: int
    clientOrderId: str

    # Parameters not in ACK response:
    price: str | None = None
    origQty: str | None = None
    executedQty: str | None = None
    status: PhoenixOrderStatus | None = None
    timeInForce: PhoenixTimeInForce | None = None
    goodTillDate: int | None = None
    type: PhoenixOrderType | None = None
    side: PhoenixOrderSide | None = None
    stopPrice: str | None = None  # please ignore when order type is TRAILING_STOP_MARKET
    time: int | None = None
    updateTime: int | None = None

    # Parameters in SPOT/MARGIN only:
    orderListId: int | None = None  # Unless OCO, the value will always be -1
    cumulativeQuoteQty: str | None = None  # cumulative quote qty
    icebergQty: str | None = None
    isWorking: bool | None = None
    workingTime: int | None = None
    origQuoteOrderQty: str | None = None
    selfTradePreventionMode: str | None = None
    transactTime: int | None = None  # POST & DELETE methods only
    fills: list[PhoenixUserTrade] | None = None  # FULL response only

    # Parameters in FUTURES only:
    avgPrice: str | None = None
    origType: PhoenixOrderType | None = None
    reduceOnly: bool | None = None
    positionSide: str | None = None
    closePosition: bool | None = None
    activatePrice: str | None = None  # activation price, only for TRAILING_STOP_MARKET order
    priceRate: str | None = None  # callback rate, only for TRAILING_STOP_MARKET order
    workingType: str | None = None
    priceProtect: bool | None = None  # if conditional order trigger is protected
    cumQuote: str | None = None  # USD-M FUTURES only
    cumBase: str | None = None  # COIN-M FUTURES only
    pair: str | None = None  # COIN-M FUTURES only

    def parse_to_order_status_report(
        self,
        account_id: AccountId,
        instrument_id: InstrumentId,
        report_id: UUID4,
        enum_parser: PhoenixEnumParser,
        treat_expired_as_canceled: bool,
        ts_init: int,
    ) -> OrderStatusReport:
        if self.price is None:
            raise RuntimeError(
                "Cannot generate order status report from Phoenix ACK response.",
            )

        client_order_id = ClientOrderId(self.clientOrderId) if self.clientOrderId != "" else None
        order_list_id = OrderListId(str(self.orderListId)) if self.orderListId is not None else None
        contingency_type = (
            ContingencyType.OCO
            if self.orderListId is not None and self.orderListId != -1
            else ContingencyType.NO_CONTINGENCY
        )

        trigger_price = Decimal(self.stopPrice) if self.stopPrice is not None else Decimal()
        trigger_type = TriggerType.NO_TRIGGER
        if self.workingType is not None:
            trigger_type = enum_parser.parse_phoenix_trigger_type(self.workingType)
        elif trigger_price > 0:
            trigger_type = TriggerType.LAST_TRADE

        trailing_offset = None
        trailing_offset_type = TrailingOffsetType.NO_TRAILING_OFFSET
        if self.priceRate is not None:
            trailing_offset = Decimal(self.priceRate)
            trailing_offset_type = TrailingOffsetType.BASIS_POINTS

        avg_px = Decimal(self.avgPrice) if self.avgPrice is not None else None
        post_only = (
            self.type == PhoenixOrderType.LIMIT_MAKER or self.timeInForce == PhoenixTimeInForce.GTX
        )
        reduce_only = self.reduceOnly if self.reduceOnly is not None else False

        if self.side is None:
            raise ValueError("`side` was `None` when a value was expected")
        if self.type is None:
            raise ValueError("`type` was `None` when a value was expected")
        if self.timeInForce is None:
            raise ValueError("`timeInForce` was `None` when a value was expected")
        if self.status is None:
            raise ValueError("`status` was `None` when a value was expected")

        order_status = enum_parser.parse_phoenix_order_status(self.status)
        if treat_expired_as_canceled and order_status == OrderStatus.EXPIRED:
            order_status = OrderStatus.CANCELED

        return OrderStatusReport(
            account_id=account_id,
            instrument_id=instrument_id,
            client_order_id=client_order_id,
            order_list_id=order_list_id,
            venue_order_id=VenueOrderId(str(self.orderId)),
            order_side=enum_parser.parse_phoenix_order_side(self.side),
            order_type=enum_parser.parse_phoenix_order_type(self.type),
            contingency_type=contingency_type,
            time_in_force=(
                enum_parser.parse_phoenix_time_in_force(self.timeInForce)
                if self.timeInForce
                else None
            ),
            order_status=order_status,
            price=Price.from_str(self.price),
            trigger_price=Price.from_str(str(trigger_price)),  # `decimal.Decimal`
            trigger_type=trigger_type,
            trailing_offset=trailing_offset,
            trailing_offset_type=trailing_offset_type,
            quantity=Quantity.from_str(self.origQty),
            filled_qty=Quantity.from_str(self.executedQty),
            avg_px=avg_px,
            post_only=post_only,
            reduce_only=reduce_only,
            ts_accepted=millis_to_nanos(self.time),
            ts_last=millis_to_nanos(self.updateTime),
            report_id=report_id,
            ts_init=ts_init,
        )


class PhoenixStatusCode(msgspec.Struct, frozen=True):
    """
    HTTP response status code.
    """

    code: int
    msg: str

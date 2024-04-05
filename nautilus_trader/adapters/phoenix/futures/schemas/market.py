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

from nautilus_trader.adapters.phoenix.common.enums import PhoenixOrderType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixTimeInForce
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixExchangeFilter
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixRateLimit
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixSymbolFilter
from nautilus_trader.adapters.phoenix.futures.enums import PhoenixFuturesContractStatus
from nautilus_trader.adapters.phoenix.futures.types import PhoenixFuturesMarkPriceUpdate
from nautilus_trader.core.datetime import millis_to_nanos
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.enums import CurrencyType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.objects import Currency
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


################################################################################
# HTTP responses
################################################################################


class PhoenixFuturesAsset(msgspec.Struct, frozen=True):
    """
    HTTP response 'inner struct' from `Phoenix Futures` GET /fapi/v1/exchangeInfo.
    """

    asset: str
    marginAvailable: bool
    autoAssetExchange: str


class PhoenixFuturesSymbolInfo(msgspec.Struct, kw_only=True, frozen=True):
    """
    HTTP response 'inner struct' from `Phoenix Futures` GET /fapi/v1/exchangeInfo.
    """

    symbol: str
    pair: str
    contractType: str  # Can be '' empty string
    deliveryDate: int
    onboardDate: int
    status: PhoenixFuturesContractStatus | None = None
    maintMarginPercent: str
    requiredMarginPercent: str
    baseAsset: str
    quoteAsset: str
    marginAsset: str
    pricePrecision: int
    quantityPrecision: int
    baseAssetPrecision: int
    quotePrecision: int
    underlyingType: str
    underlyingSubType: list[str]
    settlePlan: int | None = None
    triggerProtect: str
    liquidationFee: str
    marketTakeBound: str
    filters: list[PhoenixSymbolFilter]
    orderTypes: list[PhoenixOrderType]
    timeInForce: list[PhoenixTimeInForce]

    def parse_to_base_currency(self):
        return Currency(
            code=self.baseAsset,
            precision=self.baseAssetPrecision,
            iso4217=0,  # Currently undetermined for crypto assets
            name=self.baseAsset,
            currency_type=CurrencyType.CRYPTO,
        )

    def parse_to_quote_currency(self):
        return Currency(
            code=self.quoteAsset,
            precision=self.quotePrecision,
            iso4217=0,  # Currently undetermined for crypto assets
            name=self.quoteAsset,
            currency_type=CurrencyType.CRYPTO,
        )


class PhoenixFuturesExchangeInfo(msgspec.Struct, kw_only=True, frozen=True):
    """
    HTTP response from `Phoenix Futures` GET /fapi/v1/exchangeInfo.
    """

    timezone: str
    serverTime: int
    rateLimits: list[PhoenixRateLimit]
    exchangeFilters: list[PhoenixExchangeFilter]
    assets: list[PhoenixFuturesAsset] | None = None
    symbols: list[PhoenixFuturesSymbolInfo]


class PhoenixFuturesMarkFunding(msgspec.Struct, frozen=True):
    """
    HTTP response from `Phoenix Future` GET /fapi/v1/premiumIndex.
    """

    symbol: str
    markPrice: str  # Mark price
    indexPrice: str  # Index price
    estimatedSettlePrice: (
        str  # Estimated Settle Price (only useful in the last hour before the settlement starts)
    )
    lastFundingRate: str  # This is the lasted funding rate
    nextFundingTime: int
    interestRate: str
    time: int


class PhoenixFuturesFundRate(msgspec.Struct, frozen=True):
    """
    HTTP response from `Phoenix Future` GET /fapi/v1/fundingRate.
    """

    symbol: str
    fundingRate: str
    fundingTime: str


################################################################################
# WebSocket messages
################################################################################


class PhoenixFuturesTradeData(msgspec.Struct, frozen=True):
    """
    WebSocket message 'inner struct' for `Phoenix Futures` Trade Streams.

    Fields
    ------
    - e: Event type
    - E: Event time
    - s: Symbol
    - t: Trade ID
    - p: Price
    - q: Quantity
    - b: Buyer order ID
    - a: Seller order ID
    - T: Trade time
    - m: Is the buyer the market maker?

    """

    e: str  # Event type
    E: int  # Event time
    T: int  # Trade time
    s: str  # Symbol
    t: int  # Trade ID
    p: str  # Price
    q: str  # Quantity
    X: PhoenixOrderType  # Buyer order type
    m: bool  # Is the buyer the market maker?

    def parse_to_trade_tick(
        self,
        instrument_id: InstrumentId,
        ts_init: int,
    ) -> TradeTick:
        return TradeTick(
            instrument_id=instrument_id,
            price=Price.from_str(self.p),
            size=Quantity.from_str(self.q),
            aggressor_side=AggressorSide.SELLER if self.m else AggressorSide.BUYER,
            trade_id=TradeId(str(self.t)),
            ts_event=millis_to_nanos(self.T),
            ts_init=ts_init,
        )


class PhoenixFuturesTradeMsg(msgspec.Struct, frozen=True):
    """
    WebSocket message from `Phoenix Futures` Trade Streams.
    """

    stream: str
    data: PhoenixFuturesTradeData


class PhoenixFuturesMarkPriceData(msgspec.Struct, frozen=True):
    """
    WebSocket message 'inner struct' for `Phoenix Futures` Mark Price Update events.
    """

    e: str  # Event type
    E: int  # Event time
    s: str  # Symbol
    p: str  # Mark price
    i: str  # Index price
    P: str  # Estimated Settle Price, only useful in the last hour before the settlement starts
    r: str  # Funding rate
    T: int  # Next funding time

    def parse_to_phoenix_futures_mark_price_update(
        self,
        instrument_id: InstrumentId,
        ts_init: int,
    ) -> PhoenixFuturesMarkPriceUpdate:
        return PhoenixFuturesMarkPriceUpdate(
            instrument_id=instrument_id,
            mark=Price.from_str(self.p),
            index=Price.from_str(self.i),
            estimated_settle=Price.from_str(self.P),
            funding_rate=Decimal(self.r),
            ts_next_funding=millis_to_nanos(self.T),
            ts_event=millis_to_nanos(self.E),
            ts_init=ts_init,
        )


class PhoenixFuturesMarkPriceMsg(msgspec.Struct, frozen=True):
    """
    WebSocket message from `Phoenix Futures` Mark Price Update events.
    """

    stream: str
    data: PhoenixFuturesMarkPriceData

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

import msgspec

from nautilus_trader.adapters.phoenix.common.data import PhoenixCommonDataClient
from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.adapters.phoenix.config import PhoenixDataClientConfig
from nautilus_trader.adapters.phoenix.futures.enums import PhoenixFuturesEnumParser
from nautilus_trader.adapters.phoenix.futures.http.market import PhoenixFuturesMarketHttpAPI
from nautilus_trader.adapters.phoenix.futures.schemas.market import PhoenixFuturesMarkPriceMsg
from nautilus_trader.adapters.phoenix.futures.schemas.market import PhoenixFuturesTradeMsg
from nautilus_trader.adapters.phoenix.futures.types import PhoenixFuturesMarkPriceUpdate
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.model.data import CustomData
from nautilus_trader.model.data import DataType
from nautilus_trader.model.data import OrderBookDelta
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.identifiers import InstrumentId


class PhoenixFuturesDataClient(PhoenixCommonDataClient):
    """
    Provides a data client for the `Phoenix Futures` exchange.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    client : PhoenixHttpClient
        The Phoenix HTTP client.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : InstrumentProvider
        The instrument provider.
    base_url_ws : str
        The base URL for the WebSocket client.
    account_type : PhoenixAccountType
        The account type for the client.
    config : PhoenixDataClientConfig
        The configuration for the client.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: PhoenixHttpClient,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: InstrumentProvider,
        base_url_ws: str,
        config: PhoenixDataClientConfig,
        account_type: PhoenixAccountType = PhoenixAccountType.USDT_FUTURE,
    ):
        PyCondition.true(
            account_type.is_futures,
            "account_type was not USDT_FUTURE or COIN_FUTURE",
        )

        # Futures HTTP API
        self._futures_http_market = PhoenixFuturesMarketHttpAPI(client, account_type)

        # Futures enum parser
        self._futures_enum_parser = PhoenixFuturesEnumParser()

        # Instantiate common base class
        super().__init__(
            loop=loop,
            client=client,
            market=self._futures_http_market,
            enum_parser=self._futures_enum_parser,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            account_type=account_type,
            base_url_ws=base_url_ws,
            config=config,
        )

        # Register additional futures websocket handlers
        self._ws_handlers["@markPrice"] = self._handle_mark_price

        # Websocket msgspec decoders
        self._decoder_futures_trade_msg = msgspec.json.Decoder(PhoenixFuturesTradeMsg)
        self._decoder_futures_mark_price_msg = msgspec.json.Decoder(PhoenixFuturesMarkPriceMsg)

    # -- WEBSOCKET HANDLERS ---------------------------------------------------------------------------------

    def _handle_book_partial_update(self, raw: bytes) -> None:
        msg = self._decoder_order_book_msg.decode(raw)
        instrument_id: InstrumentId = self._get_cached_instrument_id(msg.data.s)
        book_snapshot: OrderBookDeltas = msg.data.parse_to_order_book_snapshot(
            instrument_id=instrument_id,
            ts_init=self._clock.timestamp_ns(),
        )
        # Check if book buffer active
        book_buffer: list[OrderBookDelta | OrderBookDeltas] | None = self._book_buffer.get(
            instrument_id,
        )
        if book_buffer is not None:
            book_buffer.append(book_snapshot)
        else:
            self._handle_data(book_snapshot)

    def _handle_trade(self, raw: bytes) -> None:
        # NOTE @trade is an undocumented endpoint for Futures exchanges
        msg = self._decoder_futures_trade_msg.decode(raw)
        instrument_id: InstrumentId = self._get_cached_instrument_id(msg.data.s)
        trade_tick: TradeTick = msg.data.parse_to_trade_tick(
            instrument_id=instrument_id,
            ts_init=self._clock.timestamp_ns(),
        )
        self._handle_data(trade_tick)

    def _handle_mark_price(self, raw: bytes) -> None:
        msg = self._decoder_futures_mark_price_msg.decode(raw)
        instrument_id: InstrumentId = self._get_cached_instrument_id(msg.data.s)
        data = msg.data.parse_to_phoenix_futures_mark_price_update(
            instrument_id=instrument_id,
            ts_init=self._clock.timestamp_ns(),
        )
        data_type = DataType(
            PhoenixFuturesMarkPriceUpdate,
            metadata={"instrument_id": instrument_id},
        )
        generic = CustomData(data_type=data_type, data=data)
        self._handle_data(generic)

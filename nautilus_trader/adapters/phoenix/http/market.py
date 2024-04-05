# -------------------------------------------------------------------------------------------------
#  Copyright (C)2024 808putnam All rights reserved.
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

import sys
import time

import msgspec

from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixKlineInterval
from nautilus_trader.adapters.phoenix.common.enums import PhoenixSecurityType
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixAggTrade
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixDepth
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixKline
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixTicker24hr
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixTickerBook
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixTickerPrice
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixTime
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixTrade
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbol
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbols
from nautilus_trader.adapters.phoenix.common.types import PhoenixBar
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.endpoint import PhoenixHttpEndpoint
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.datetime import nanos_to_millis
from nautilus_trader.core.nautilus_pyo3 import HttpMethod
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.identifiers import InstrumentId


class PhoenixPingHttp(PhoenixHttpEndpoint):
    """
    Endpoint for testing connectivity to the REST API.

    `GET /api/v3/ping`
    `GET /fapi/v1/ping`
    `GET /dapi/v1/ping`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "ping"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder()

    async def get(self) -> dict:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, None)
        return self._get_resp_decoder.decode(raw)


class PhoenixTimeHttp(PhoenixHttpEndpoint):
    """
    Endpoint for testing connectivity to the REST API and receiving current server time.

    `GET /api/v3/time`
    `GET /fapi/v1/time`
    `GET /dapi/v1/time`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "time"
        super().__init__(client, methods, url_path)
        self._get_resp_decoder = msgspec.json.Decoder(PhoenixTime)

    async def get(self) -> PhoenixTime:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, None)
        return self._get_resp_decoder.decode(raw)


class PhoenixDepthHttp(PhoenixHttpEndpoint):
    """
    Endpoint of orderbook depth.

    `GET /api/v3/depth`
    `GET /fapi/v1/depth`
    `GET /dapi/v1/depth`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "depth"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(PhoenixDepth)

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Orderbook depth GET endpoint parameters.

        Parameters
        ----------
        symbol : PhoenixSymbol
            The trading pair.
        limit : int, optional, default 100
            The limit for the response.
            SPOT/MARGIN (GET /api/v3/depth)
                Default 100; max 5000.
            FUTURES (GET /*api/v1/depth)
                Default 500; max 1000.
                Valid limits:[5, 10, 20, 50, 100, 500, 1000].

        """

        symbol: PhoenixSymbol
        limit: int | None = None

    async def get(self, parameters: GetParameters) -> PhoenixDepth:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixTradesHttp(PhoenixHttpEndpoint):
    """
    Endpoint of recent market trades.

    `GET /api/v3/trades`
    `GET /fapi/v1/trades`
    `GET /dapi/v1/trades`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "trades"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(list[PhoenixTrade])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for recent trades.

        Parameters
        ----------
        symbol : PhoenixSymbol
            The trading pair.
        limit : int, optional
            The limit for the response. Default 500; max 1000.

        """

        symbol: PhoenixSymbol
        limit: int | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixTrade]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixHistoricalTradesHttp(PhoenixHttpEndpoint):
    """
    Endpoint of older market historical trades.

    `GET /api/v3/historicalTrades`
    `GET /fapi/v1/historicalTrades`
    `GET /dapi/v1/historicalTrades`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.MARKET_DATA,
        }
        url_path = base_endpoint + "historicalTrades"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(list[PhoenixTrade])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for historical trades.

        Parameters
        ----------
        symbol : PhoenixSymbol
            The trading pair.
        limit : int, optional
            The limit for the response. Default 500; max 1000.
        fromId : int, optional
            Trade id to fetch from. Default gets most recent trades

        """

        symbol: PhoenixSymbol
        limit: int | None = None
        fromId: int | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixTrade]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixAggTradesHttp(PhoenixHttpEndpoint):
    """
    Endpoint of compressed and aggregated market trades. Market trades that fill in
    100ms with the same price and same taking side will have the quantity aggregated.

    `GET /api/v3/aggTrades`
    `GET /fapi/v1/aggTrades`
    `GET /dapi/v1/aggTrades`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "aggTrades"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(list[PhoenixAggTrade])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for aggregate trades.

        Parameters
        ----------
        symbol : PhoenixSymbol
            The trading pair.
        limit : int, optional
            The limit for the response. Default 500; max 1000.
        fromId : int, optional
            Trade id to fetch from INCLUSIVE.
        startTime : int, optional
            Timestamp in ms to get aggregate trades from INCLUSIVE.
        endTime : int, optional
            Timestamp in ms to get aggregate trades until INCLUSIVE.

        """

        symbol: PhoenixSymbol
        limit: int | None = None
        fromId: int | None = None
        startTime: int | None = None
        endTime: int | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixAggTrade]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixKlinesHttp(PhoenixHttpEndpoint):
    """
    Endpoint of Kline/candlestick bars for a symbol. Klines are uniquely identified by
    their open time.

    `GET /api/v3/klines`
    `GET /fapi/v1/klines`
    `GET /dapi/v1/klines`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "klines"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(list[PhoenixKline])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for klines.

        Parameters
        ----------
        symbol : PhoenixSymbol
            The trading pair.
        interval : str
            The interval of kline, e.g 1m, 5m, 1h, 1d, etc.
        limit : int, optional
            The limit for the response. Default 500; max 1000.
        startTime : int, optional
            Timestamp in ms to get klines from INCLUSIVE.
        endTime : int, optional
            Timestamp in ms to get klines until INCLUSIVE.

        """

        symbol: PhoenixSymbol
        interval: PhoenixKlineInterval
        limit: int | None = None
        startTime: int | None = None
        endTime: int | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixKline]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixTicker24hrHttp(PhoenixHttpEndpoint):
    """
    Endpoint of 24-hour rolling window price change statistics.

    `GET /api/v3/ticker/24hr`
    `GET /fapi/v1/ticker/24hr`
    `GET /dapi/v1/ticker/24hr`

    Warnings
    --------
    Care should be taken when accessing this endpoint with no symbol specified.
    The weight usage can be very large, which may cause rate limits to be hit.

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "ticker/24hr"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_obj_resp_decoder = msgspec.json.Decoder(PhoenixTicker24hr)
        self._get_arr_resp_decoder = msgspec.json.Decoder(list[PhoenixTicker24hr])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for 24hr ticker.

        Parameters
        ----------
        symbol : PhoenixSymbol
            The trading pair. When given, endpoint will return a single PhoenixTicker24hr
            When omitted, endpoint will return a list of PhoenixTicker24hr for all trading pairs.
        symbols : PhoenixSymbols
            SPOT/MARGIN only!
            List of trading pairs. When given, endpoint will return a list of PhoenixTicker24hr.
        type : str
            SPOT/MARGIN only!
            Select between FULL and MINI 24hr ticker responses to save bandwidth.

        """

        symbol: PhoenixSymbol | None = None
        symbols: PhoenixSymbols | None = None  # SPOT/MARGIN only
        type: str | None = None  # SPOT/MARIN only

    async def _get(self, parameters: GetParameters) -> list[PhoenixTicker24hr]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        if parameters.symbol is not None:
            return [self._get_obj_resp_decoder.decode(raw)]
        else:
            return self._get_arr_resp_decoder.decode(raw)


class PhoenixTickerPriceHttp(PhoenixHttpEndpoint):
    """
    Endpoint of latest price for a symbol or symbols.

    `GET /api/v3/ticker/price`
    `GET /fapi/v1/ticker/price`
    `GET /dapi/v1/ticker/price`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "ticker/price"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_obj_resp_decoder = msgspec.json.Decoder(PhoenixTickerPrice)
        self._get_arr_resp_decoder = msgspec.json.Decoder(list[PhoenixTickerPrice])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for price ticker.

        Parameters
        ----------
        symbol : PhoenixSymbol
            The trading pair. When given, endpoint will return a single PhoenixTickerPrice.
            When omitted, endpoint will return a list of PhoenixTickerPrice for all trading pairs.
        symbols : str
            SPOT/MARGIN only!
            List of trading pairs. When given, endpoint will return a list of PhoenixTickerPrice.

        """

        symbol: PhoenixSymbol | None = None
        symbols: PhoenixSymbols | None = None  # SPOT/MARGIN only

    async def _get(self, parameters: GetParameters) -> list[PhoenixTickerPrice]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        if parameters.symbol is not None:
            return [self._get_obj_resp_decoder.decode(raw)]
        else:
            return self._get_arr_resp_decoder.decode(raw)


class PhoenixTickerBookHttp(PhoenixHttpEndpoint):
    """
    Endpoint of best price/qty on the order book for a symbol or symbols.

    `GET /api/v3/ticker/bookTicker`
    `GET /fapi/v1/ticker/bookTicker`
    `GET /dapi/v1/ticker/bookTicker`

    References
    ----------
    TODO

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        base_endpoint: str,
    ):
        methods = {
            HttpMethod.GET: PhoenixSecurityType.NONE,
        }
        url_path = base_endpoint + "ticker/price"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_arr_resp_decoder = msgspec.json.Decoder(list[PhoenixTickerBook])
        self._get_obj_resp_decoder = msgspec.json.Decoder(PhoenixTickerBook)

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for order book ticker.

        Parameters
        ----------
        symbol : str
            The trading pair. When given, endpoint will return a single PhoenixTickerBook
            When omitted, endpoint will return a list of PhoenixTickerBook for all trading pairs.
        symbols : str
            SPOT/MARGIN only!
            List of trading pairs. When given, endpoint will return a list of PhoenixTickerBook.

        """

        symbol: PhoenixSymbol | None = None
        symbols: PhoenixSymbols | None = None  # SPOT/MARGIN only

    async def _get(self, parameters: GetParameters) -> list[PhoenixTickerBook]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        if parameters.symbol is not None:
            return [self._get_obj_resp_decoder.decode(raw)]
        else:
            return self._get_arr_resp_decoder.decode(raw)


class PhoenixMarketHttpAPI:
    """
    Provides access to the Phoenix Market HTTP REST API.

    Parameters
    ----------
    client : PhoenixHttpClient
        The Phoenix REST API client.
    account_type : PhoenixAccountType
        The Phoenix account type, used to select the endpoint prefix.

    Warnings
    --------
    This class should not be used directly, but through a concrete subclass.

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        account_type: PhoenixAccountType,
    ):
        PyCondition.not_none(client, "client")
        self.client = client

        if account_type.is_spot_or_margin:
            self.base_endpoint = "/api/v3/"
        elif account_type == PhoenixAccountType.USDT_FUTURE:
            self.base_endpoint = "/fapi/v1/"
        elif account_type == PhoenixAccountType.COIN_FUTURE:
            self.base_endpoint = "/dapi/v1/"
        else:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"invalid `PhoenixAccountType`, was {account_type}",  # pragma: no cover
            )

        # Create Endpoints
        self._endpoint_ping = PhoenixPingHttp(client, self.base_endpoint)
        self._endpoint_time = PhoenixTimeHttp(client, self.base_endpoint)
        self._endpoint_depth = PhoenixDepthHttp(client, self.base_endpoint)
        self._endpoint_trades = PhoenixTradesHttp(client, self.base_endpoint)
        self._endpoint_historical_trades = PhoenixHistoricalTradesHttp(client, self.base_endpoint)
        self._endpoint_agg_trades = PhoenixAggTradesHttp(client, self.base_endpoint)
        self._endpoint_klines = PhoenixKlinesHttp(client, self.base_endpoint)
        self._endpoint_ticker_24hr = PhoenixTicker24hrHttp(client, self.base_endpoint)
        self._endpoint_ticker_price = PhoenixTickerPriceHttp(client, self.base_endpoint)
        self._endpoint_ticker_book = PhoenixTickerBookHttp(client, self.base_endpoint)

    async def ping(self) -> dict:
        """
        Ping Phoenix REST API.
        """
        return await self._endpoint_ping.get()

    async def request_server_time(self) -> int:
        """
        Request server time from Phoenix.
        """
        response = await self._endpoint_time.get()
        return response.serverTime

    async def query_depth(
        self,
        symbol: str,
        limit: int | None = None,
    ) -> PhoenixDepth:
        """
        Query order book depth for a symbol.
        """
        return await self._endpoint_depth.get(
            parameters=self._endpoint_depth.GetParameters(
                symbol=PhoenixSymbol(symbol),
                limit=limit,
            ),
        )

    async def request_order_book_snapshot(
        self,
        instrument_id: InstrumentId,
        ts_init: int,
        limit: int | None = None,
    ) -> OrderBookDeltas:
        """
        Request snapshot of order book depth.
        """
        depth = await self.query_depth(instrument_id.symbol.value, limit)
        return depth.parse_to_order_book_snapshot(
            instrument_id=instrument_id,
            ts_init=ts_init,
        )

    async def query_trades(
        self,
        symbol: str,
        limit: int | None = None,
    ) -> list[PhoenixTrade]:
        """
        Query trades for symbol.
        """
        return await self._endpoint_trades.get(
            parameters=self._endpoint_trades.GetParameters(
                symbol=PhoenixSymbol(symbol),
                limit=limit,
            ),
        )

    async def request_trade_ticks(
        self,
        instrument_id: InstrumentId,
        ts_init: int,
        limit: int | None = None,
    ) -> list[TradeTick]:
        """
        Request TradeTicks from Phoenix.
        """
        trades = await self.query_trades(instrument_id.symbol.value, limit)
        return [
            trade.parse_to_trade_tick(
                instrument_id=instrument_id,
                ts_init=ts_init,
            )
            for trade in trades
        ]

    async def query_agg_trades(
        self,
        symbol: str,
        limit: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        from_id: int | None = None,
    ) -> list[PhoenixAggTrade]:
        """
        Query aggregated trades for symbol.
        """
        return await self._endpoint_agg_trades.get(
            parameters=self._endpoint_agg_trades.GetParameters(
                symbol=PhoenixSymbol(symbol),
                limit=limit,
                startTime=start_time,
                endTime=end_time,
                fromId=from_id,
            ),
        )

    async def request_agg_trade_ticks(
        self,
        instrument_id: InstrumentId,
        ts_init: int,
        limit: int | None = 1000,
        start_time: int | None = None,
        end_time: int | None = None,
        from_id: int | None = None,
    ) -> list[TradeTick]:
        """
        Request TradeTicks from Phoenix aggregated trades.

        If start_time and end_time are both specified, will fetch *all* TradeTicks in
        the interval, making multiple requests if necessary.

        """
        ticks: list[TradeTick] = []
        next_start_time = start_time

        if end_time is None:
            end_time = sys.maxsize

        if from_id is not None and (start_time or end_time) is not None:
            raise RuntimeError(
                "Cannot specify both fromId and startTime or endTime.",
            )

        # Only split into separate requests if both start_time and end_time are specified
        max_interval = (1000 * 60 * 60) - 1  # 1ms under an hour, as specified in Futures docs.
        last_id = 0
        interval_limited = False

        def _calculate_next_end_time(start_time: int, end_time: int) -> tuple[int, bool]:
            next_interval = start_time + max_interval
            interval_limited = next_interval < end_time
            next_end_time = next_interval if interval_limited is True else end_time
            return next_end_time, interval_limited

        if start_time is not None and end_time is not None:
            next_end_time, interval_limited = _calculate_next_end_time(start_time, end_time)
        else:
            next_end_time = end_time

        while True:
            response = await self.query_agg_trades(
                instrument_id.symbol.value,
                limit,
                start_time=next_start_time,
                end_time=next_end_time,
                from_id=from_id,
            )

            for trade in response:
                if not trade.a > last_id:
                    # Skip duplicate trades
                    continue
                ticks.append(
                    trade.parse_to_trade_tick(
                        instrument_id=instrument_id,
                        ts_init=ts_init,
                    ),
                )

            if limit and len(response) < limit and interval_limited is False:
                # end loop regardless when limit is not hit
                break
            if (
                start_time is None
                or end_time is None
                or next_end_time >= nanos_to_millis(time.time_ns())
            ):
                break
            else:
                last = response[-1]
                last_id = last.a
                next_start_time = last.T
                next_end_time, interval_limited = _calculate_next_end_time(
                    next_start_time,
                    end_time,
                )
                continue

        return ticks

    async def query_historical_trades(
        self,
        symbol: str,
        limit: int | None = None,
        from_id: int | None = None,
    ) -> list[PhoenixTrade]:
        """
        Query historical trades for symbol.
        """
        return await self._endpoint_historical_trades.get(
            parameters=self._endpoint_historical_trades.GetParameters(
                symbol=PhoenixSymbol(symbol),
                limit=limit,
                fromId=from_id,
            ),
        )

    async def request_historical_trade_ticks(
        self,
        instrument_id: InstrumentId,
        ts_init: int,
        limit: int | None = None,
        from_id: int | None = None,
    ) -> list[TradeTick]:
        """
        Request historical TradeTicks from Phoenix.
        """
        historical_trades = await self.query_historical_trades(
            symbol=instrument_id.symbol.value,
            limit=limit,
            from_id=from_id,
        )
        return [
            trade.parse_to_trade_tick(
                instrument_id=instrument_id,
                ts_init=ts_init,
            )
            for trade in historical_trades
        ]

    async def query_klines(
        self,
        symbol: str,
        interval: PhoenixKlineInterval,
        limit: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[PhoenixKline]:
        """
        Query klines for a symbol over an interval.
        """
        return await self._endpoint_klines.get(
            parameters=self._endpoint_klines.GetParameters(
                symbol=PhoenixSymbol(symbol),
                interval=interval,
                limit=limit,
                startTime=start_time,
                endTime=end_time,
            ),
        )

    async def request_phoenix_bars(
        self,
        bar_type: BarType,
        ts_init: int,
        interval: PhoenixKlineInterval,
        limit: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[PhoenixBar]:
        """
        Request Phoenix Bars from Klines.
        """
        end_time_ms = int(end_time) if end_time is not None else sys.maxsize
        all_bars: list[PhoenixBar] = []
        while True:
            klines = await self.query_klines(
                symbol=bar_type.instrument_id.symbol.value,
                interval=interval,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )
            bars: list[PhoenixBar] = [
                kline.parse_to_phoenix_bar(bar_type, ts_init) for kline in klines
            ]
            all_bars.extend(bars)

            # Update the start_time to fetch the next set of bars
            if klines:
                next_start_time = klines[-1].open_time + 1
            else:
                # Handle the case when klines is empty
                break

            # No more bars to fetch
            if (limit and len(klines) < limit) or next_start_time >= end_time_ms:
                break

            start_time = next_start_time

        return all_bars

    async def query_ticker_24hr(
        self,
        symbol: str | None = None,
        symbols: list[str] | None = None,
        response_type: str | None = None,
    ) -> list[PhoenixTicker24hr]:
        """
        Query 24hr ticker for symbol or symbols.
        """
        if symbol is not None and symbols is not None:
            raise RuntimeError(
                "Cannot specify both symbol and symbols parameters.",
            )
        return await self._endpoint_ticker_24hr._get(
            parameters=self._endpoint_ticker_24hr.GetParameters(
                symbol=PhoenixSymbol(symbol),
                symbols=PhoenixSymbols(symbols),
                type=response_type,
            ),
        )

    async def query_ticker_price(
        self,
        symbol: str | None = None,
        symbols: list[str] | None = None,
    ) -> list[PhoenixTickerPrice]:
        """
        Query price ticker for symbol or symbols.
        """
        if symbol is not None and symbols is not None:
            raise RuntimeError(
                "Cannot specify both symbol and symbols parameters.",
            )
        return await self._endpoint_ticker_price._get(
            parameters=self._endpoint_ticker_price.GetParameters(
                symbol=PhoenixSymbol(symbol),
                symbols=PhoenixSymbols(symbols),
            ),
        )

    async def query_ticker_book(
        self,
        symbol: str | None = None,
        symbols: list[str] | None = None,
    ) -> list[PhoenixTickerBook]:
        """
        Query book ticker for symbol or symbols.
        """
        if symbol is not None and symbols is not None:
            raise RuntimeError(
                "Cannot specify both symbol and symbols parameters.",
            )
        return await self._endpoint_ticker_book._get(
            parameters=self._endpoint_ticker_book.GetParameters(
                symbol=PhoenixSymbol(symbol),
                symbols=PhoenixSymbols(symbols),
            ),
        )

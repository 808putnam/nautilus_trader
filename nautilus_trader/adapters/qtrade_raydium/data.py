# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2024 qtrade. All rights reserved.
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
import decimal
from decimal import Decimal

import pandas as pd

from nautilus_trader.adapters.qtrade_raydium.common.constants import RAYDIUM_VENUE
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.adapters.qtrade_raydium.config import RaydiumDataClientConfig
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.adapters.qtrade_raydium.error import RaydiumError
from nautilus_trader.adapters.qtrade_raydium.common.enums import RaydiumEnumParser
from nautilus_trader.adapters.qtrade_raydium.common.enums import RaydiumErrorCode



import bxsolana
from bxsolana import provider

# The 'pragma: no cover' comment excludes a method from test coverage.
# https://coverage.readthedocs.io/en/coverage-4.3.3/excluding.html
# The reason for their use is to reduce redundant/needless tests which simply
# assert that a `NotImplementedError` is raised when calling abstract methods.
# These tests are expensive to maintain (as they must be kept in line with any
# refactorings), and offer little to no benefit in return. However, the intention
# is for all method implementations to be fully covered by tests.

# *** THESE PRAGMA: NO COVER COMMENTS MUST BE REMOVED IN ANY IMPLEMENTATION. ***


class RaydiumLiveMarketDataClient(LiveMarketDataClient):
    """
    Provides a data client for the `Raydium` exchange.

    A live market data client general handles market data feeds and requests.

    +----------------------------------------+-------------+
    | Method                                 | Requirement |
    +----------------------------------------+-------------+
    | _connect                               | required    |
    | _disconnect                            | required    |
    | reset                                  | optional    |
    | dispose                                | optional    |
    +----------------------------------------+-------------+
    | _subscribe (adapter specific types)    | optional    |
    | _subscribe_instruments                 | optional    |
    | _subscribe_instrument                  | optional    |
    | _subscribe_order_book_deltas           | optional    |
    | _subscribe_order_book_snapshots        | optional    |
    | _subscribe_quote_ticks                 | optional    |
    | _subscribe_trade_ticks                 | optional    |
    | _subscribe_bars                        | optional    |
    | _subscribe_instrument_status           | optional    |
    | _subscribe_instrument_close            | optional    |
    | _unsubscribe (adapter specific types)  | optional    |
    | _unsubscribe_instruments               | optional    |
    | _unsubscribe_instrument                | optional    |
    | _unsubscribe_order_book_deltas         | optional    |
    | _unsubscribe_order_book_snapshots      | optional    |
    | _unsubscribe_quote_ticks               | optional    |
    | _unsubscribe_trade_ticks               | optional    |
    | _unsubscribe_bars                      | optional    |
    | _unsubscribe_instrument_status         | optional    |
    | _unsubscribe_instrument_close          | optional    |
    +----------------------------------------+-------------+
    | _request                               | optional    |
    | _request_instrument                    | optional    |
    | _request_instruments                   | optional    |
    | _request_quote_ticks                   | optional    |
    | _request_trade_ticks                   | optional    |
    | _request_bars                          | optional    |
    +----------------------------------------+-------------+

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    client : provider.Provider
        The Raydium client.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : InstrumentProvider
        The instrument provider.
    name : str, optional
        The custom client ID.
    config : RaydiumDataClientConfig
        The configuration for the client.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: provider.Provider,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: InstrumentProvider,
        name: str | None,
        config: RaydiumDataClientConfig,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=ClientId(name or RAYDIUM_VENUE.value),
            venue=RAYDIUM_VENUE,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
        )

        # Configuration
        self._update_instrument_interval: int = 60 * 60  # Once per hour (hardcode)
        self._update_instruments_task: asyncio.Task | None = None

        # HTTP API
        self._http_client = client

        # Enum parser
        # Currently no enum parser is required for the Raydium client.

        # WebSocket API
        self._ws_client = provider.ws()

        # Hot caches
        self._instrument_ids: dict[str, InstrumentId] = {}
        # TODO: Add more hot caches
        # See adapters.binance.common.data.BinanceLiveMarketDataClient

        # Register common WebSocket message handlers
        # TODO: See adapters.binance.common.data.BinanceLiveMarketDataClient

        # WebSocket msgspec decoders
        # TODO: See adapters.binance.common.data.BinanceLiveMarketDataClient

        # Retry logic (hard coded for now)
        self._max_retries: int = 3
        self._retry_delay: float = 1.0
        # TODO: See adapters.binance.common.data.BinanceLiveMarketDataClient
        # self._retry_errors: set[BinanceErrorCode] = {
        #     BinanceErrorCode.DISCONNECTED,
        #     BinanceErrorCode.TOO_MANY_REQUESTS,  # Short retry delays may result in bans
        #     BinanceErrorCode.TIMEOUT,
        #     BinanceErrorCode.INVALID_TIMESTAMP,
        #     BinanceErrorCode.ME_RECVWINDOW_REJECT,
        # }

    async def _connect(self) -> None:
        self._log.info("Initializing instruments...")
        
        await self._instrument_provider.initialize()

        self._send_all_instruments_to_data_engine()
        self._update_instruments_task = self.create_task(self._update_instruments())

    async def _update_instruments(self) -> None:
        while True:
            retries = 0
            while True:
                try:
                    self._log.debug(
                        f"Scheduled `update_instruments` to run in "
                        f"{self._update_instrument_interval}s",
                    )
                    await asyncio.sleep(self._update_instrument_interval)
                    await self._instrument_provider.load_all_async()
                    self._send_all_instruments_to_data_engine()
                    break
                except RaydiumError as e:
                    error_code = RaydiumErrorCode(e.message["code"])
                    retries += 1

                    if not self._should_retry(error_code, retries):
                        self._log.error(f"Error updating instruments: {e}")
                        break

                    self._log.warning(
                        f"{error_code.name}: retrying update instruments "
                        f"{retries}/{self._max_retries} in {self._retry_delay}s",
                    )
                    await asyncio.sleep(self._retry_delay)
                except asyncio.CancelledError:
                    self._log.debug("Canceled `update_instruments` task")
                    return

    async def _reconnect(self) -> None:
        # TODO: See adapters.binance.common.data.BinanceLiveMarketDataClient
        # coros = []
        # for instrument_id in self._book_depths:
        #     coros.append(self._order_book_snapshot_then_deltas(instrument_id))
        # 
        # await asyncio.gather(*coros)
        pass

    async def _disconnect(self) -> None:
        # Cancel update instruments task
        if self._update_instruments_task:
            self._log.debug("Canceling `update_instruments` task")
            self._update_instruments_task.cancel()
            self._update_instruments_task = None

        # TODO
        # await self._ws_client.disconnect()

    def _should_retry(self, error_code: RaydiumErrorCode, retries: int) -> bool:
        if (
            error_code not in self._retry_errors
            or not self._max_retries
            or retries > self._max_retries
        ):
            return False
        return True

    def _send_all_instruments_to_data_engine(self) -> None:
        for instrument in self._instrument_provider.get_all().values():
            self._handle_data(instrument)

        for currency in self._instrument_provider.currencies().values():
            self._cache.add_currency(currency)

    # -- SUBSCRIPTIONS ----------------------------------------------------------------------------
    # TODO: See adapters.binance.common.data.BinanceLiveMarketDataClient
    
    # -- REQUESTS ---------------------------------------------------------------------------------
    # TODO: See adapters.binance.common.data.BinanceLiveMarketDataClient

    # -- WEBSOCKET HANDLERS ---------------------------------------------------------------------------------
    # TODO: See adapters.binance.common.data.BinanceLiveMarketDataClient

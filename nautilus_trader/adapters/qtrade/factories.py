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
from functools import lru_cache

from nautilus_trader.adapters.qtrade.common.credentials import get_auth_header
from nautilus_trader.adapters.qtrade.common.credentials import get_private_key
from nautilus_trader.adapters.qtrade.config import QtradeExecClientConfig
from nautilus_trader.adapters.qtrade.execution import QtradeLiveExecutionClient 
from nautilus_trader.adapters.qtrade.providers import QtradeInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.live.factories import LiveExecClientFactory

import bxsolana
from bxsolana import provider

QTRADE_HTTP_CLIENTS: dict[str, provider.Provider] = {}


@lru_cache(1)
def get_cached_qtrade_http_client(
    auth_header: str | None = None,
    private_key: str | None = None,
) -> provider.Provider:
    """
    Cache and return a Qtrade HTTP client with the given auth_header and private_key.

    If a cached client with matching auth_header and private_key already exists, then that
    cached client will be returned.

    Parameters
    ----------
    auth_header : str, optional
        The bloXroute authentication header.
    private_key : str, optional
        The user's private key.

    Returns
    -------
    provider.Provider

    """
    global QTRADE_HTTP_CLIENTS

    auth_header = auth_header or get_auth_header()
    private_key = private_key or get_private_key()

    client_key: str = "|".join((auth_header, private_key))
    if client_key not in QTRADE_HTTP_CLIENTS:
        client = provider.http()
        QTRADE_HTTP_CLIENTS[client_key] = client
    return QTRADE_HTTP_CLIENTS[client_key]


@lru_cache(1)
def get_cached_qtrade_instrument_provider(
    client: provider.Provider,
    clock: LiveClock,
    config: InstrumentProviderConfig,
) -> QtradeInstrumentProvider:
    """
    Cache and return an instrument provider for the `Qtrade` exchange.

    If a cached provider already exists, then that provider will be returned.

    Parameters
    ----------
    client : provider.Provider
        The client for the instrument provider.
    clock : LiveClock
        The clock for the instrument provider.
    config : InstrumentProviderConfig
        The configuration for the instrument provider.

    Returns
    -------
    QtradeInstrumentProvider

    """
    return QtradeInstrumentProvider(
        api=client,
        clock=clock,
        config=config,
    )


class QtradeLiveExecClientFactory(LiveExecClientFactory):
    """
    Provides a `Qtrade` live execution client factory.
    """

    @staticmethod
    def create(  # type: ignore
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: QtradeExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> QtradeLiveExecutionClient:
        """
        Create a new Qtrade execution client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : QtradeExecClientConfig
            The configuration for the client.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        QtradeExecutionClient

        """
        # Get HTTP client singleton
        client: provider.Provider = get_cached_qtrade_http_client(
            auth_header=config.auth_header,
            private_key=config.private_key,
        )


        # Get instrument provider singleton
        instrument_provider = get_cached_qtrade_instrument_provider(
            client=client,
            clock=clock,
            config=config.instrument_provider,
        )

        return QtradeLiveExecutionClient(
            loop=loop,
            client=client,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            name=name,
            config=config,
        )

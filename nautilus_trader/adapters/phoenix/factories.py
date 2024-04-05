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
from functools import lru_cache

from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.adapters.phoenix.config import PhoenixDataClientConfig
from nautilus_trader.adapters.phoenix.config import PhoenixExecClientConfig
from nautilus_trader.adapters.phoenix.futures.data import PhoenixFuturesDataClient
from nautilus_trader.adapters.phoenix.futures.execution import PhoenixFuturesExecutionClient
from nautilus_trader.adapters.phoenix.futures.providers import PhoenixFuturesInstrumentProvider
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.spot.data import PhoenixSpotDataClient
from nautilus_trader.adapters.phoenix.spot.execution import PhoenixSpotExecutionClient
from nautilus_trader.adapters.phoenix.spot.providers import PhoenixSpotInstrumentProvider
from nautilus_trader.adapters.env import get_env_key
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.core.nautilus_pyo3 import Quota
from nautilus_trader.live.factories import LiveDataClientFactory
from nautilus_trader.live.factories import LiveExecClientFactory


PHOENIX_HTTP_CLIENTS: dict[str, PhoenixHttpClient] = {}


@lru_cache(1)
def get_cached_phoenix_http_client(
    clock: LiveClock,
    account_type: PhoenixAccountType,
    base_url: str | None = None,
    is_testnet: bool = False,
    is_us: bool = False,
) -> PhoenixHttpClient:
    """
    Cache and return a Phoenix HTTP client with the given key and secret.

    If a cached client with matching key and secret already exists, then that
    cached client will be returned.

    Parameters
    ----------
    clock : LiveClock
        The clock for the client.
    account_type : PhoenixAccountType
        The account type for the client.
    base_url : str, optional
        The base URL for the API endpoints.        
    is_testnet : bool, default False
        If the client is connecting to the testnet API.
    is_us : bool, default False
        If the client is connecting to Phoenix US.

    Returns
    -------
    PhoenixHttpClient

    """
    global PHOENIX_HTTP_CLIENTS

    key = key or _get_api_key(account_type, is_testnet)
    secret = secret or _get_api_secret(account_type, is_testnet)
    default_http_base_url = _get_http_base_url(account_type, is_testnet, is_us)

    # Setup rate limit quotas
    if account_type.is_spot:
        # Spot
        ratelimiter_default_quota = Quota.rate_per_minute(6000)
        ratelimiter_quotas: list[tuple[str, Quota]] = [
            ("order", Quota.rate_per_minute(3000)),
            ("allOrders", Quota.rate_per_minute(int(3000 / 20))),
        ]
    else:
        # Futures
        ratelimiter_default_quota = Quota.rate_per_minute(2400)
        ratelimiter_quotas = [
            ("order", Quota.rate_per_minute(1200)),
            ("allOrders", Quota.rate_per_minute(int(1200 / 20))),
        ]

    client_key: str = "|".join((key, secret))
    if client_key not in PHOENIX_HTTP_CLIENTS:
        client = PhoenixHttpClient(
            clock=clock,
            key=key,
            secret=secret,
            base_url=base_url or default_http_base_url,
            ratelimiter_quotas=ratelimiter_quotas,
            ratelimiter_default_quota=ratelimiter_default_quota,
        )
        PHOENIX_HTTP_CLIENTS[client_key] = client
    return PHOENIX_HTTP_CLIENTS[client_key]


@lru_cache(1)
def get_cached_phoenix_spot_instrument_provider(
    client: PhoenixHttpClient,
    clock: LiveClock,
    account_type: PhoenixAccountType,
    is_testnet: bool,
    config: InstrumentProviderConfig,
) -> PhoenixSpotInstrumentProvider:
    """
    Cache and return an instrument provider for the `Phoenix Spot/Margin` exchange.

    If a cached provider already exists, then that provider will be returned.

    Parameters
    ----------
    client : PhoenixHttpClient
        The client for the instrument provider.
    clock : LiveClock
        The clock for the instrument provider.
    account_type : PhoenixAccountType
        The Phoenix account type for the instrument provider.
    is_testnet : bool, default False
        If the provider is for the Spot testnet.
    config : InstrumentProviderConfig
        The configuration for the instrument provider.

    Returns
    -------
    PhoenixSpotInstrumentProvider

    """
    return PhoenixSpotInstrumentProvider(
        client=client,
        clock=clock,
        account_type=account_type,
        is_testnet=is_testnet,
        config=config,
    )


@lru_cache(1)
def get_cached_phoenix_futures_instrument_provider(
    client: PhoenixHttpClient,
    clock: LiveClock,
    account_type: PhoenixAccountType,
    config: InstrumentProviderConfig,
) -> PhoenixFuturesInstrumentProvider:
    """
    Cache and return an instrument provider for the `Phoenix Futures` exchange.

    If a cached provider already exists, then that provider will be returned.

    Parameters
    ----------
    client : PhoenixHttpClient
        The client for the instrument provider.
    clock : LiveClock
        The clock for the instrument provider.
    account_type : PhoenixAccountType
        The Phoenix account type for the instrument provider.
    config : InstrumentProviderConfig
        The configuration for the instrument provider.

    Returns
    -------
    PhoenixFuturesInstrumentProvider

    """
    return PhoenixFuturesInstrumentProvider(
        client=client,
        clock=clock,
        account_type=account_type,
        config=config,
    )


class PhoenixLiveDataClientFactory(LiveDataClientFactory):
    """
    Provides a `Phoenix` live data client factory.
    """

    @staticmethod
    def create(  # type: ignore
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: PhoenixDataClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> PhoenixSpotDataClient | PhoenixFuturesDataClient:
        """
        Create a new Phoenix data client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The client name.
        config : PhoenixDataClientConfig
            The client configuration.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        PhoenixSpotDataClient or PhoenixFuturesDataClient

        Raises
        ------
        ValueError
            If `config.account_type` is not a valid `PhoenixAccountType`.

        """
        # Get HTTP client singleton
        client: PhoenixHttpClient = get_cached_phoenix_http_client(
            clock=clock,
            account_type=config.account_type,
            key=config.api_key,
            secret=config.api_secret,
            base_url=config.base_url_http,
            is_testnet=config.testnet,
            is_us=config.us,
        )

        default_base_url_ws: str = _get_ws_base_url(
            account_type=config.account_type,
            is_testnet=config.testnet,
            is_us=config.us,
        )

        provider: PhoenixSpotInstrumentProvider | PhoenixFuturesInstrumentProvider
        if config.account_type.is_spot_or_margin:
            # Get instrument provider singleton
            provider = get_cached_phoenix_spot_instrument_provider(
                client=client,
                clock=clock,
                account_type=config.account_type,
                is_testnet=config.testnet,
                config=config.instrument_provider,
            )

            return PhoenixSpotDataClient(
                loop=loop,
                client=client,
                msgbus=msgbus,
                cache=cache,
                clock=clock,
                instrument_provider=provider,
                account_type=config.account_type,
                base_url_ws=config.base_url_ws or default_base_url_ws,
                config=config,
            )
        else:
            # Get instrument provider singleton
            provider = get_cached_phoenix_futures_instrument_provider(
                client=client,
                clock=clock,
                account_type=config.account_type,
                config=config.instrument_provider,
            )

            return PhoenixFuturesDataClient(
                loop=loop,
                client=client,
                msgbus=msgbus,
                cache=cache,
                clock=clock,
                instrument_provider=provider,
                account_type=config.account_type,
                base_url_ws=config.base_url_ws or default_base_url_ws,
                config=config,
            )


class PhoenixLiveExecClientFactory(LiveExecClientFactory):
    """
    Provides a `Phoenix` live execution client factory.
    """

    @staticmethod
    def create(  # type: ignore
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: PhoenixExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> PhoenixSpotExecutionClient | PhoenixFuturesExecutionClient:
        """
        Create a new Phoenix execution client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The client name.
        config : PhoenixExecClientConfig
            The configuration for the client.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        PhoenixExecutionClient

        Raises
        ------
        ValueError
            If `config.account_type` is not a valid `PhoenixAccountType`.

        """
        # Get HTTP client singleton
        client: PhoenixHttpClient = get_cached_phoenix_http_client(
            clock=clock,
            account_type=config.account_type,
            key=config.api_key,
            secret=config.api_secret,
            base_url=config.base_url_http,
            is_testnet=config.testnet,
            is_us=config.us,
        )

        default_base_url_ws: str = _get_ws_base_url(
            account_type=config.account_type,
            is_testnet=config.testnet,
            is_us=config.us,
        )

        provider: PhoenixSpotInstrumentProvider | PhoenixFuturesInstrumentProvider
        if config.account_type.is_spot or config.account_type.is_margin:
            # Get instrument provider singleton
            provider = get_cached_phoenix_spot_instrument_provider(
                client=client,
                clock=clock,
                account_type=config.account_type,
                is_testnet=config.testnet,
                config=config.instrument_provider,
            )

            return PhoenixSpotExecutionClient(
                loop=loop,
                client=client,
                msgbus=msgbus,
                cache=cache,
                clock=clock,
                instrument_provider=provider,
                base_url_ws=config.base_url_ws or default_base_url_ws,
                account_type=config.account_type,
                config=config,
            )
        else:
            # Get instrument provider singleton
            provider = get_cached_phoenix_futures_instrument_provider(
                client=client,
                clock=clock,
                account_type=config.account_type,
                config=config.instrument_provider,
            )

            return PhoenixFuturesExecutionClient(
                loop=loop,
                client=client,
                msgbus=msgbus,
                cache=cache,
                clock=clock,
                instrument_provider=provider,
                base_url_ws=config.base_url_ws or default_base_url_ws,
                account_type=config.account_type,
                config=config,
            )


def _get_api_key(account_type: PhoenixAccountType, is_testnet: bool) -> str:
    if is_testnet:
        if account_type.is_spot_or_margin:
            return get_env_key("PHOENIX_TESTNET_API_KEY")
        else:
            return get_env_key("PHOENIX_FUTURES_TESTNET_API_KEY")

    if account_type.is_spot_or_margin:
        return get_env_key("PHOENIX_API_KEY")
    else:
        return get_env_key("PHOENIX_FUTURES_API_KEY")


def _get_api_secret(account_type: PhoenixAccountType, is_testnet: bool) -> str:
    if is_testnet:
        if account_type.is_spot_or_margin:
            return get_env_key("PHOENIX_TESTNET_API_SECRET")
        else:
            return get_env_key("PHOENIX_FUTURES_TESTNET_API_SECRET")

    if account_type.is_spot_or_margin:
        return get_env_key("PHOENIX_API_SECRET")
    else:
        return get_env_key("PHOENIX_FUTURES_API_SECRET")


def _get_http_base_url(account_type: PhoenixAccountType, is_testnet: bool, is_us: bool) -> str:
    # Testnet base URLs
    if is_testnet:
        if account_type.is_spot_or_margin:
            return "https://testnet.phoenix.vision"
        elif account_type == PhoenixAccountType.USDT_FUTURE:
            return "https://testnet.phoenixfuture.com"
        elif account_type == PhoenixAccountType.COIN_FUTURE:
            return "https://testnet.phoenixfuture.com"
        else:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"invalid `PhoenixAccountType`, was {account_type}",  # pragma: no cover
            )

    # Live base URLs
    top_level_domain: str = "us" if is_us else "com"
    if account_type.is_spot:
        return f"https://api.phoenix.{top_level_domain}"
    elif account_type.is_margin:
        return f"https://sapi.phoenix.{top_level_domain}"
    elif account_type == PhoenixAccountType.USDT_FUTURE:
        return f"https://fapi.phoenix.{top_level_domain}"
    elif account_type == PhoenixAccountType.COIN_FUTURE:
        return f"https://dapi.phoenix.{top_level_domain}"
    else:
        raise RuntimeError(  # pragma: no cover (design-time error)
            f"invalid `PhoenixAccountType`, was {account_type}",  # pragma: no cover
        )


def _get_ws_base_url(account_type: PhoenixAccountType, is_testnet: bool, is_us: bool) -> str:
    # Testnet base URLs
    if is_testnet:
        if account_type.is_spot_or_margin:
            return "wss://testnet.phoenix.vision"
        elif account_type == PhoenixAccountType.USDT_FUTURE:
            return "wss://stream.phoenixfuture.com"
        elif account_type == PhoenixAccountType.COIN_FUTURE:
            raise ValueError("no testnet for COIN-M futures")
        else:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"invalid `PhoenixAccountType`, was {account_type}",  # pragma: no cover
            )

    # Live base URLs
    top_level_domain: str = "us" if is_us else "com"
    if account_type.is_spot_or_margin:
        return f"wss://stream.phoenix.{top_level_domain}:9443"
    elif account_type == PhoenixAccountType.USDT_FUTURE:
        return f"wss://fstream.phoenix.{top_level_domain}"
    elif account_type == PhoenixAccountType.COIN_FUTURE:
        return f"wss://dstream.phoenix.{top_level_domain}"
    else:
        raise RuntimeError(
            f"invalid `PhoenixAccountType`, was {account_type}",
        )  # pragma: no cover (design-time error)

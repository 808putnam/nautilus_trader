# -------------------------------------------------------------------------------------------------
#  Copyright (C) qtrade. All rights reserved.
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

from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.model.identifiers import InstrumentId

import asyncio
import os

import bxsolana
from bxsolana import provider
from bxsolana_trader_proto import api as proto

# The 'pragma: no cover' comment excludes a method from test coverage.
# https://coverage.readthedocs.io/en/coverage-4.3.3/excluding.html
# The reason for their use is to reduce redundant/needless tests which simply
# assert that a `NotImplementedError` is raised when calling abstract methods.
# These tests are expensive to maintain (as they must be kept in line with any
# refactorings), and offer little to no benefit in return. However, the intention
# is for all method implementations to be fully covered by tests.

# *** THESE PRAGMA: NO COVER COMMENTS MUST BE REMOVED IN ANY IMPLEMENTATION. ***


class RaydiumInstrumentProvider(InstrumentProvider):
    """
    Provides a means of loading instruments from the Raydium exchange.

    Parameters
    ----------
    api : APIClient
        The client for the provider.
    config : InstrumentProviderConfig, optional
        The configuration for the provider.

    """

    def __init__(
        self,
        api: provider.Provider,
        config: InstrumentProviderConfig | None = None,
    ):
        super().__init__(config=config)

        self._api = api

    async def load_all_async(
        self,
        filters: dict | None = None,
    ) -> None:
        filters_str = "..." if not filters else f" with filters {filters}..."
        self._log.info(f"Loading all instruments{filters_str}")

        getRaydiumPoolReserveResponse = await self._api.get_raydium_pool_reserve(
            get_raydium_pool_reserve_request=proto.GetRaydiumPoolReserveRequest(
                    pairs_or_addresses=[
                        "HZ1znC9XBasm9AMDhGocd9EHSyH8Pyj1EUdiPb4WnZjo",
                        "D8wAxwpH2aKaEGBKfeGdnQbCc2s54NrRvTDXCK98VAeT",
                        "DdpuaJgjB2RptGMnfnCZVmC4vkKsMV6ytRa2gggQtCWt",
                    ]
                )
            )
        
        print("token1 reserves: " + getRaydiumPoolReserveResponse.pools[0].token1_reserves)

    async def load_ids_async(
        self,
        instrument_ids: list[InstrumentId],
        filters: dict | None = None,
    ) -> None:
        raise NotImplementedError(
            "method `load_ids_async` must be implemented in the subclass",
        )  # pragma: no cover

    async def load_async(
        self,
        instrument_id: InstrumentId,
        filters: dict | None = None,
    ) -> None:
        raise NotImplementedError(
            "method `load_async` must be implemented in the subclass",
        )  # pragma: no cover

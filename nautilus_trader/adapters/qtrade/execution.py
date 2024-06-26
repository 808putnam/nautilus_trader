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
import pandas as pd

from nautilus_trader.execution.messages import CancelAllOrders
from nautilus_trader.execution.messages import CancelOrder
from nautilus_trader.execution.messages import ModifyOrder
from nautilus_trader.execution.messages import QueryOrder
from nautilus_trader.execution.messages import SubmitOrder
from nautilus_trader.execution.messages import SubmitOrderList
from nautilus_trader.execution.reports import FillReport
from nautilus_trader.execution.reports import OrderStatusReport
from nautilus_trader.execution.reports import PositionStatusReport
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType

from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.cache.cache import Cache

from nautilus_trader.adapters.qtrade.providers import QtradeInstrumentProvider
from nautilus_trader.adapters.qtrade.config import QtradeExecClientConfig
from nautilus_trader.adapters.qtrade.common.constants import QTRADE_VENUE

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


class QtradeLiveExecutionClient(LiveExecutionClient):
    """
    Provides an execution client for the `Qtrade` exchange.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    client : provider.Provider
        The Qtrade HTTP client.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : QtradeInstrumentProvider
        The instrument provider.
    config : QtradeExecClientConfig
        The configuration for the client.
    name : str, optional
        The custom client ID.

    +--------------------------------------------+-------------+
    | Method                                     | Requirement |
    +--------------------------------------------+-------------+
    | _connect                                   | required    |
    | _disconnect                                | required    |
    | reset                                      | optional    |
    | dispose                                    | optional    |
    +--------------------------------------------+-------------+
    | _submit_order                              | required    |
    | _submit_order_list                         | required    |
    | _modify_order                              | required    |
    | _cancel_order                              | required    |
    | _cancel_all_orders                         | required    |
    | generate_order_status_report               | required    |
    | generate_order_status_reports              | required    |
    | generate_fill_reports                      | required    |
    | generate_position_status_reports           | required    |
    +--------------------------------------------+-------------+

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: provider.Provider,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: QtradeInstrumentProvider,
        config: QtradeExecClientConfig,
        name: str | None = None,
    ):
        super().__init__(
            loop=loop,
            client_id=ClientId(name or QTRADE_VENUE.value),
            venue=QTRADE_VENUE,
            oms_type=OmsType.NETTING,
            instrument_provider=instrument_provider,
            account_type=AccountType.CASH,
            base_currency=None,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )

    async def _connect(self) -> None:
        # Initialize instrument provider
        await self._instrument_provider.initialize()

    async def _disconnect(self) -> None:
        raise NotImplementedError(
            "method `_disconnect` must be implemented in the subclass",
        )  # pragma: no cover

    def reset(self) -> None:
        raise NotImplementedError(
            "method `reset` must be implemented in the subclass",
        )  # pragma: no cover

    def dispose(self) -> None:
        raise NotImplementedError(
            "method `dispose` must be implemented in the subclass",
        )  # pragma: no cover

    # -- EXECUTION REPORTS ------------------------------------------------------------------------
    # TODO: See nautilus_tader.adapters.binance.common.execution.py

    # -- COMMAND HANDLERS -------------------------------------------------------------------------
    # TODO: See nautilus_tader.adapters.binance.common.execution.py

    async def _submit_order(self, command: SubmitOrder) -> None:
        raise NotImplementedError(
            "method `_submit_order` must be implemented in the subclass",
        )  # pragma: no cover

    async def _submit_order_list(self, command: SubmitOrderList) -> None:
        raise NotImplementedError(
            "method `_submit_order_list` must be implemented in the subclass",
        )  # pragma: no cover

    async def _modify_order(self, command: ModifyOrder) -> None:
        raise NotImplementedError(
            "method `_modify_order` must be implemented in the subclass",
        )  # pragma: no cover

    async def _cancel_order(self, command: CancelOrder) -> None:
        raise NotImplementedError(
            "method `_cancel_order` must be implemented in the subclass",
        )  # pragma: no cover

    async def _cancel_all_orders(self, command: CancelAllOrders) -> None:
        raise NotImplementedError(
            "method `_cancel_all_orders` must be implemented in the subclass",
        )  # pragma: no cover

    async def _query_order(self, command: QueryOrder) -> None:
        raise NotImplementedError(
            "method `_query_order` must be implemented in the subclass",
        )  # pragma: no cover

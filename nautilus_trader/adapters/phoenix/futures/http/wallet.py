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


import msgspec

from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixSecurityType
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbol
from nautilus_trader.adapters.phoenix.futures.schemas.wallet import PhoenixFuturesCommissionRate
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.endpoint import PhoenixHttpEndpoint
from nautilus_trader.common.component import LiveClock
from nautilus_trader.core.nautilus_pyo3 import HttpMethod


class PhoenixFuturesCommissionRateHttp(PhoenixHttpEndpoint):
    """
    Endpoint of maker/taker commission rate information.

    `GET /fapi/v1/commissionRate`
    `GET /dapi/v1/commissionRate`

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
            HttpMethod.GET: PhoenixSecurityType.USER_DATA,
        }
        super().__init__(
            client,
            methods,
            base_endpoint + "commissionRate",
        )
        self._get_resp_decoder = msgspec.json.Decoder(PhoenixFuturesCommissionRate)

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for fetching commission rate.

        Parameters
        ----------
        symbol : PhoenixSymbol
            Receive commission rate of the provided symbol.
        timestamp : str
            Millisecond timestamp of the request.
        recvWindow : str, optional
            The number of milliseconds after timestamp the request is valid.

        """

        timestamp: str
        symbol: PhoenixSymbol
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> PhoenixFuturesCommissionRate:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixFuturesWalletHttpAPI:
    """
    Provides access to the `Phoenix Futures` Wallet HTTP REST API.

    Parameters
    ----------
    client : PhoenixHttpClient
        The Phoenix REST API client.

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        clock: LiveClock,
        account_type: PhoenixAccountType = PhoenixAccountType.USDT_FUTURE,
    ):
        self.client = client
        self._clock = clock

        if account_type == PhoenixAccountType.USDT_FUTURE:
            self.base_endpoint = "/fapi/v1/"
        elif account_type == PhoenixAccountType.COIN_FUTURE:
            self.base_endpoint = "/dapi/v1/"

        if not account_type.is_futures:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"`PhoenixAccountType` not USDT_FUTURE or COIN_FUTURE, was {account_type}",  # pragma: no cover
            )

        self._endpoint_futures_commission_rate = PhoenixFuturesCommissionRateHttp(
            client,
            self.base_endpoint,
        )

    def _timestamp(self) -> str:
        """
        Create Phoenix timestamp from internal clock.
        """
        return str(self._clock.timestamp_ms())

    async def query_futures_commission_rate(
        self,
        symbol: str,
        recv_window: str | None = None,
    ) -> PhoenixFuturesCommissionRate:
        """
        Get Futures commission rates for a given symbol.
        """
        rate = await self._endpoint_futures_commission_rate.get(
            parameters=self._endpoint_futures_commission_rate.GetParameters(
                timestamp=self._timestamp(),
                symbol=PhoenixSymbol(symbol),
                recvWindow=recv_window,
            ),
        )
        return rate

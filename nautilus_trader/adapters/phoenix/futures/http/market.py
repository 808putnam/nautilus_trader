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
from nautilus_trader.adapters.phoenix.futures.schemas.market import PhoenixFuturesExchangeInfo
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.endpoint import PhoenixHttpEndpoint
from nautilus_trader.adapters.phoenix.http.market import PhoenixMarketHttpAPI
from nautilus_trader.core.nautilus_pyo3 import HttpMethod


class PhoenixFuturesExchangeInfoHttp(PhoenixHttpEndpoint):
    """
    Endpoint of FUTURES exchange trading rules and symbol information.

    `GET /fapi/v1/exchangeInfo`
    `GET /dapi/v1/exchangeInfo`

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
        url_path = base_endpoint + "exchangeInfo"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(PhoenixFuturesExchangeInfo)

    async def get(self) -> PhoenixFuturesExchangeInfo:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, None)
        return self._get_resp_decoder.decode(raw)


class PhoenixFuturesMarketHttpAPI(PhoenixMarketHttpAPI):
    """
    Provides access to the `Phoenix Futures` HTTP REST API.

    Parameters
    ----------
    client : PhoenixHttpClient
        The Phoenix REST API client.
    account_type : PhoenixAccountType
        The Phoenix account type, used to select the endpoint.

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        account_type: PhoenixAccountType = PhoenixAccountType.USDT_FUTURE,
    ):
        super().__init__(
            client=client,
            account_type=account_type,
        )

        if not account_type.is_futures:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"`PhoenixAccountType` not USDT_FUTURE or COIN_FUTURE, was {account_type}",  # pragma: no cover
            )

        self._endpoint_futures_exchange_info = PhoenixFuturesExchangeInfoHttp(
            client,
            self.base_endpoint,
        )

    async def query_futures_exchange_info(self) -> PhoenixFuturesExchangeInfo:
        """
        Retrieve Phoenix Futures exchange information.
        """
        return await self._endpoint_futures_exchange_info.get()

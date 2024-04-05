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
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbols
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.endpoint import PhoenixHttpEndpoint
from nautilus_trader.adapters.phoenix.http.market import PhoenixMarketHttpAPI
from nautilus_trader.adapters.phoenix.spot.enums import PhoenixSpotPermissions
from nautilus_trader.adapters.phoenix.spot.schemas.market import PhoenixSpotAvgPrice
from nautilus_trader.adapters.phoenix.spot.schemas.market import PhoenixSpotExchangeInfo
from nautilus_trader.core.nautilus_pyo3 import HttpMethod


class PhoenixSpotExchangeInfoHttp(PhoenixHttpEndpoint):
    """
    Endpoint of SPOT/MARGIN exchange trading rules and symbol information.

    `GET /api/v3/exchangeInfo`

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
        self._get_resp_decoder = msgspec.json.Decoder(PhoenixSpotExchangeInfo)

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET exchangeInfo parameters.

        Parameters
        ----------
        symbol : PhoenixSymbol, optional
            The specify trading pair to get exchange info for.
        symbols : PhoenixSymbols, optional
            The specify list of trading pairs to get exchange info for.
        permissions : PhoenixSpotPermissions, optional
            The filter symbols list by supported permissions.

        """

        symbol: PhoenixSymbol | None = None
        symbols: PhoenixSymbols | None = None
        permissions: PhoenixSpotPermissions | None = None

    async def get(self, parameters: GetParameters | None = None) -> PhoenixSpotExchangeInfo:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixSpotAvgPriceHttp(PhoenixHttpEndpoint):
    """
    Endpoint of current average price of a symbol.

    `GET /api/v3/avgPrice`

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
        url_path = base_endpoint + "avgPrice"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(PhoenixSpotAvgPrice)

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET avgPrice parameters.

        Parameters
        ----------
        symbol : PhoenixSymbol
            Specify trading pair to get average price for.

        """

        symbol: PhoenixSymbol = None

    async def get(self, parameters: GetParameters) -> PhoenixSpotAvgPrice:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixSpotMarketHttpAPI(PhoenixMarketHttpAPI):
    """
    Provides access to the `Phoenix Spot` Market HTTP REST API.

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
        account_type: PhoenixAccountType = PhoenixAccountType.SPOT,
    ):
        super().__init__(
            client=client,
            account_type=account_type,
        )

        if not account_type.is_spot_or_margin:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"`PhoenixAccountType` not SPOT, MARGIN or ISOLATED_MARGIN, was {account_type}",  # pragma: no cover
            )

        self._endpoint_spot_exchange_info = PhoenixSpotExchangeInfoHttp(client, self.base_endpoint)
        self._endpoint_spot_average_price = PhoenixSpotAvgPriceHttp(client, self.base_endpoint)

    async def query_spot_exchange_info(
        self,
        symbol: str | None = None,
        symbols: list[str] | None = None,
        permissions: PhoenixSpotPermissions | None = None,
    ) -> PhoenixSpotExchangeInfo:
        """
        Check Phoenix Spot exchange information.
        """
        if symbol and symbols:
            raise ValueError("`symbol` and `symbols` cannot be sent together")
        return await self._endpoint_spot_exchange_info.get(
            parameters=self._endpoint_spot_exchange_info.GetParameters(
                symbol=PhoenixSymbol(symbol),
                symbols=PhoenixSymbols(symbols),
                permissions=permissions,
            ),
        )

    async def query_spot_average_price(self, symbol: str) -> PhoenixSpotAvgPrice:
        """
        Check average price for a provided symbol on the Spot exchange.
        """
        return await self._endpoint_spot_average_price.get(
            parameters=self._endpoint_spot_average_price.GetParameters(
                symbol=PhoenixSymbol(symbol),
            ),
        )

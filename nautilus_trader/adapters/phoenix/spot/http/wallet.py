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
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.endpoint import PhoenixHttpEndpoint
from nautilus_trader.adapters.phoenix.spot.schemas.wallet import PhoenixSpotTradeFee
from nautilus_trader.common.component import LiveClock
from nautilus_trader.core.nautilus_pyo3 import HttpMethod


class PhoenixSpotTradeFeeHttp(PhoenixHttpEndpoint):
    """
    Endpoint of maker/taker trade fee information.

    `GET /sapi/v1/asset/tradeFee`

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
            base_endpoint + "tradeFee",
        )
        self._get_obj_resp_decoder = msgspec.json.Decoder(PhoenixSpotTradeFee)
        self._get_arr_resp_decoder = msgspec.json.Decoder(list[PhoenixSpotTradeFee])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        GET parameters for fetching trade fees.

        Parameters
        ----------
        symbol : PhoenixSymbol
            Optional symbol to receive individual trade fee
        recvWindow : str
            Optional number of milliseconds after timestamp the request is valid
        timestamp : str
            Millisecond timestamp of the request

        """

        timestamp: str
        symbol: PhoenixSymbol | None = None
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixSpotTradeFee]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        if parameters.symbol is not None:
            return [self._get_obj_resp_decoder.decode(raw)]
        else:
            return self._get_arr_resp_decoder.decode(raw)


class PhoenixSpotWalletHttpAPI:
    """
    Provides access to the `Phoenix Spot/Margin` Wallet HTTP REST API.

    Parameters
    ----------
    client : PhoenixHttpClient
        The Phoenix REST API client.

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        clock: LiveClock,
        account_type: PhoenixAccountType = PhoenixAccountType.SPOT,
    ):
        self.client = client
        self._clock = clock
        self.base_endpoint = "/sapi/v1/asset/"

        if not account_type.is_spot_or_margin:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"`PhoenixAccountType` not SPOT, MARGIN or ISOLATED_MARGIN, was {account_type}",  # pragma: no cover
            )

        self._endpoint_spot_trade_fee = PhoenixSpotTradeFeeHttp(client, self.base_endpoint)

    def _timestamp(self) -> str:
        """
        Create Phoenix timestamp from internal clock.
        """
        return str(self._clock.timestamp_ms())

    async def query_spot_trade_fees(
        self,
        symbol: str | None = None,
        recv_window: str | None = None,
    ) -> list[PhoenixSpotTradeFee]:
        fees = await self._endpoint_spot_trade_fee.get(
            parameters=self._endpoint_spot_trade_fee.GetParameters(
                timestamp=self._timestamp(),
                symbol=PhoenixSymbol(symbol) if symbol is not None else None,
                recvWindow=recv_window,
            ),
        )
        return fees

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

from typing import Any

import msgspec

from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixSecurityType
from nautilus_trader.adapters.phoenix.common.schemas.account import PhoenixOrder
from nautilus_trader.adapters.phoenix.common.schemas.account import PhoenixStatusCode
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbol
from nautilus_trader.adapters.phoenix.futures.schemas.account import PhoenixFuturesAccountInfo
from nautilus_trader.adapters.phoenix.futures.schemas.account import PhoenixFuturesDualSidePosition
from nautilus_trader.adapters.phoenix.futures.schemas.account import PhoenixFuturesPositionRisk
from nautilus_trader.adapters.phoenix.http.account import PhoenixAccountHttpAPI
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.endpoint import PhoenixHttpEndpoint
from nautilus_trader.common.component import LiveClock
from nautilus_trader.core.nautilus_pyo3 import HttpMethod


class PhoenixFuturesPositionModeHttp(PhoenixHttpEndpoint):
    """
    Endpoint of user's position mode for every FUTURES symbol.

    `GET /fapi/v1/positionSide/dual`
    `GET /dapi/v1/positionSide/dual`

    `POST /fapi/v1/positionSide/dual`
    `POST /dapi/v1/positionSide/dual`

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
            HttpMethod.POST: PhoenixSecurityType.TRADE,
        }
        url_path = base_endpoint + "positionSide/dual"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(PhoenixFuturesDualSidePosition)
        self._post_resp_decoder = msgspec.json.Decoder(PhoenixStatusCode)

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of positionSide/dual GET request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        recvWindow: str | None = None

    class PostParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of positionSide/dual POST request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        dualSidePosition : str ('true', 'false')
            The dual side position mode to set...
            `true`: Hedge Mode, `false`: One-way mode.
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        dualSidePosition: str
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> PhoenixFuturesDualSidePosition:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)

    async def post(self, parameters: PostParameters) -> PhoenixStatusCode:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._post_resp_decoder.decode(raw)


class PhoenixFuturesAllOpenOrdersHttp(PhoenixHttpEndpoint):
    """
    Endpoint of all open FUTURES orders.

    `DELETE /fapi/v1/allOpenOrders`
    `DELETE /dapi/v1/allOpenOrders`

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
            HttpMethod.DELETE: PhoenixSecurityType.TRADE,
        }
        url_path = base_endpoint + "allOpenOrders"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._delete_resp_decoder = msgspec.json.Decoder(PhoenixStatusCode)

    class DeleteParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of allOpenOrders DELETE request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        symbol : PhoenixSymbol
            The symbol of the request
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        symbol: PhoenixSymbol
        recvWindow: str | None = None

    async def delete(self, parameters: DeleteParameters) -> PhoenixStatusCode:
        method_type = HttpMethod.DELETE
        raw = await self._method(method_type, parameters)
        return self._delete_resp_decoder.decode(raw)


class PhoenixFuturesCancelMultipleOrdersHttp(PhoenixHttpEndpoint):
    """
    Endpoint of cancel multiple FUTURES orders.

    `DELETE /fapi/v1/batchOrders`
    `DELETE /dapi/v1/batchOrders`

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
            HttpMethod.DELETE: PhoenixSecurityType.TRADE,
        }
        url_path = base_endpoint + "batchOrders"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._delete_resp_decoder = msgspec.json.Decoder(
            list[PhoenixOrder] | dict[str, Any],
            strict=False,
        )

    class DeleteParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of batchOrders DELETE request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        symbol : PhoenixSymbol
            The symbol of the request
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        symbol: PhoenixSymbol
        orderIdList: str | None = None
        origClientOrderIdList: str | None = None
        recvWindow: str | None = None

    async def delete(self, parameters: DeleteParameters) -> list[PhoenixOrder]:
        method_type = HttpMethod.DELETE
        raw = await self._method(method_type, parameters)
        return self._delete_resp_decoder.decode(raw)


class PhoenixFuturesAccountHttp(PhoenixHttpEndpoint):
    """
    Endpoint of current FUTURES account information.

    `GET /fapi/v2/account`
    `GET /dapi/v1/account`

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
        url_path = base_endpoint + "account"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._resp_decoder = msgspec.json.Decoder(PhoenixFuturesAccountInfo)

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of account GET request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> PhoenixFuturesAccountInfo:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._resp_decoder.decode(raw)


class PhoenixFuturesPositionRiskHttp(PhoenixHttpEndpoint):
    """
    Endpoint of information of all FUTURES positions.

    `GET /fapi/v2/positionRisk`
    `GET /dapi/v1/positionRisk`

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
        url_path = base_endpoint + "positionRisk"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._get_resp_decoder = msgspec.json.Decoder(list[PhoenixFuturesPositionRisk])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of positionRisk GET request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        symbol : PhoenixSymbol, optional
            The symbol of the request.
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        symbol: PhoenixSymbol | None = None
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixFuturesPositionRisk]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._get_resp_decoder.decode(raw)


class PhoenixFuturesAccountHttpAPI(PhoenixAccountHttpAPI):
    """
    Provides access to the `Phoenix Futures` Account/Trade HTTP REST API.

    Parameters
    ----------
    client : PhoenixHttpClient
        The Phoenix REST API client.
    account_type : PhoenixAccountType
        The Phoenix account type.

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        clock: LiveClock,
        account_type: PhoenixAccountType = PhoenixAccountType.USDT_FUTURE,
    ):
        super().__init__(
            client=client,
            clock=clock,
            account_type=account_type,
        )
        if not account_type.is_futures:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"`PhoenixAccountType` not USDT_FUTURE or COIN_FUTURE, was {account_type}",  # pragma: no cover
            )
        v2_endpoint_base = self.base_endpoint
        if account_type == PhoenixAccountType.USDT_FUTURE:
            v2_endpoint_base = "/fapi/v2/"

        # Create endpoints
        self._endpoint_futures_position_mode = PhoenixFuturesPositionModeHttp(
            client,
            self.base_endpoint,
        )
        self._endpoint_futures_all_open_orders = PhoenixFuturesAllOpenOrdersHttp(
            client,
            self.base_endpoint,
        )
        self._endpoint_futures_cancel_multiple_orders = PhoenixFuturesCancelMultipleOrdersHttp(
            client,
            self.base_endpoint,
        )
        self._endpoint_futures_account = PhoenixFuturesAccountHttp(client, v2_endpoint_base)
        self._endpoint_futures_position_risk = PhoenixFuturesPositionRiskHttp(
            client,
            v2_endpoint_base,
        )

    async def query_futures_hedge_mode(
        self,
        recv_window: str | None = None,
    ) -> PhoenixFuturesDualSidePosition:
        """
        Check Phoenix Futures hedge mode (dualSidePosition).
        """
        return await self._endpoint_futures_position_mode.get(
            parameters=self._endpoint_futures_position_mode.GetParameters(
                timestamp=self._timestamp(),
                recvWindow=recv_window,
            ),
        )

    async def set_futures_hedge_mode(
        self,
        dual_side_position: bool,
        recv_window: str | None = None,
    ) -> PhoenixStatusCode:
        """
        Set Phoenix Futures hedge mode (dualSidePosition).
        """
        return await self._endpoint_futures_position_mode.post(
            parameters=self._endpoint_futures_position_mode.PostParameters(
                timestamp=self._timestamp(),
                dualSidePosition=str(dual_side_position).lower(),
                recvWindow=recv_window,
            ),
        )

    async def cancel_all_open_orders(
        self,
        symbol: str,
        recv_window: str | None = None,
    ) -> bool:
        """
        Delete all Futures open orders.

        Returns whether successful.

        """
        response = await self._endpoint_futures_all_open_orders.delete(
            parameters=self._endpoint_futures_all_open_orders.DeleteParameters(
                timestamp=self._timestamp(),
                symbol=PhoenixSymbol(symbol),
                recvWindow=recv_window,
            ),
        )
        return response.code == 200

    async def cancel_multiple_orders(
        self,
        symbol: str,
        client_order_ids: list[str],
        recv_window: str | None = None,
    ) -> bool:
        """
        Delete multiple Futures orders.

        Returns whether successful.

        """
        stringified_client_order_ids = str(client_order_ids).replace(" ", "").replace("'", '"')
        await self._endpoint_futures_cancel_multiple_orders.delete(
            parameters=self._endpoint_futures_cancel_multiple_orders.DeleteParameters(
                timestamp=self._timestamp(),
                symbol=PhoenixSymbol(symbol),
                origClientOrderIdList=stringified_client_order_ids,
                recvWindow=recv_window,
            ),
        )
        return True

    async def query_futures_account_info(
        self,
        recv_window: str | None = None,
    ) -> PhoenixFuturesAccountInfo:
        """
        Check Phoenix Futures account information.
        """
        return await self._endpoint_futures_account.get(
            parameters=self._endpoint_futures_account.GetParameters(
                timestamp=self._timestamp(),
                recvWindow=recv_window,
            ),
        )

    async def query_futures_position_risk(
        self,
        symbol: str | None = None,
        recv_window: str | None = None,
    ) -> list[PhoenixFuturesPositionRisk]:
        """
        Check all Futures position's info for a symbol.
        """
        return await self._endpoint_futures_position_risk.get(
            parameters=self._endpoint_futures_position_risk.GetParameters(
                timestamp=self._timestamp(),
                symbol=PhoenixSymbol(symbol),
                recvWindow=recv_window,
            ),
        )

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
from nautilus_trader.adapters.phoenix.common.enums import PhoenixNewOrderRespType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixOrderSide
from nautilus_trader.adapters.phoenix.common.enums import PhoenixSecurityType
from nautilus_trader.adapters.phoenix.common.enums import PhoenixTimeInForce
from nautilus_trader.adapters.phoenix.common.schemas.market import PhoenixRateLimit
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbol
from nautilus_trader.adapters.phoenix.http.account import PhoenixAccountHttpAPI
from nautilus_trader.adapters.phoenix.http.account import PhoenixOpenOrdersHttp
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.endpoint import PhoenixHttpEndpoint
from nautilus_trader.adapters.phoenix.spot.schemas.account import PhoenixSpotAccountInfo
from nautilus_trader.adapters.phoenix.spot.schemas.account import PhoenixSpotOrderOco
from nautilus_trader.common.component import LiveClock
from nautilus_trader.core.nautilus_pyo3 import HttpMethod


class PhoenixSpotOpenOrdersHttp(PhoenixOpenOrdersHttp):
    """
    Endpoint of all SPOT/MARGIN open orders on a symbol.

    `GET /api/v3/openOrders` (inherited)

    `DELETE /api/v3/openOrders`

    Warnings
    --------
    Care should be taken when accessing this endpoint with no symbol specified.
    The weight usage can be very large, which may cause rate limits to be hit.

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
            HttpMethod.DELETE: PhoenixSecurityType.TRADE,
        }
        super().__init__(
            client,
            base_endpoint,
            methods,
        )
        self._delete_resp_decoder = msgspec.json.Decoder()

    class DeleteParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of openOrders SPOT/MARGIN DELETE request. Includes OCO orders.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request
        symbol : PhoenixSymbol
            The symbol of the orders
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        symbol: PhoenixSymbol
        recvWindow: str | None = None

    async def _delete(self, parameters: DeleteParameters) -> list[dict[str, Any]]:
        method_type = HttpMethod.DELETE
        raw = await self._method(method_type, parameters)
        return self._delete_resp_decoder.decode(raw)


class PhoenixSpotOrderOcoHttp(PhoenixHttpEndpoint):
    """
    Endpoint for creating SPOT/MARGIN OCO orders.

    `POST /api/v3/order/oco`

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
            HttpMethod.POST: PhoenixSecurityType.TRADE,
        }
        url_path = base_endpoint + "order/oco"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._resp_decoder = msgspec.json.Decoder(PhoenixSpotOrderOco)

    class PostParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        OCO order creation POST endpoint parameters.

        Parameters
        ----------
        symbol : PhoenixSymbol
            The symbol of the order.
        timestamp : str
            The millisecond timestamp of the request.
        side : PhoenixOrderSide
            The market side of the order (BUY, SELL).
        quantity : str
            The order quantity in base asset units for the request.
        price : str
            The order price for the request.
        stopPrice : str
            The order stop price for the request.
        listClientOrderId : str, optional
            A unique Id for the entire orderList
        limitClientOrderId : str, optional
            The client order ID for the limit request. A unique ID among open orders.
            Automatically generated if not provided.
        limitStrategyId : int,  optional
            The client strategy ID for the limit request.
        limitStrategyType : int, optional
            The client strategy type for the limit request. Cannot be less than 1000000
        limitIcebergQty : str, optional
            Create a limit iceberg order.
        trailingDelta : str, optional
            Can be used in addition to stopPrice.
            The order trailing delta of the request.
        stopClientOrderId : str, optional
            The client order ID for the stop request. A unique ID among open orders.
            Automatically generated if not provided.
        stopStrategyId : int,  optional
            The client strategy ID for the stop request.
        stopStrategyType : int, optional
            The client strategy type for the stop request. Cannot be less than 1000000.
        stopLimitPrice : str, optional
            Limit price for the stop order request.
            If provided, stopLimitTimeInForce is required.
        stopIcebergQty : str, optional
            Create a stop iceberg order.
        stopLimitTimeInForce : PhoenixTimeInForce, optional
            The time in force of the stop limit order.
            Valid values: (GTC, FOK, IOC).
        newOrderRespType : PhoenixNewOrderRespType, optional
            The response type for the order request.
        recvWindow : str, optional
            The response receive window in milliseconds for the request.
            Cannot exceed 60000.

        """

        symbol: PhoenixSymbol
        timestamp: str
        side: PhoenixOrderSide
        quantity: str
        price: str
        stopPrice: str
        listClientOrderId: str | None = None
        limitClientOrderId: str | None = None
        limitStrategyId: int | None = None
        limitStrategyType: int | None = None
        limitIcebergQty: str | None = None
        trailingDelta: str | None = None
        stopClientOrderId: str | None = None
        stopStrategyId: int | None = None
        stopStrategyType: int | None = None
        stopLimitPrice: str | None = None
        stopIcebergQty: str | None = None
        stopLimitTimeInForce: PhoenixTimeInForce | None = None
        newOrderRespType: PhoenixNewOrderRespType | None = None
        recvWindow: str | None = None

    async def _post(self, parameters: PostParameters) -> PhoenixSpotOrderOco:
        method_type = HttpMethod.POST
        raw = await self._method(method_type, parameters)
        return self._resp_decoder.decode(raw)


class PhoenixSpotOrderListHttp(PhoenixHttpEndpoint):
    """
    Endpoint for querying and deleting SPOT/MARGIN OCO orders.

    `GET /api/v3/orderList`
    `DELETE /api/v3/orderList`

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
            HttpMethod.DELETE: PhoenixSecurityType.TRADE,
        }
        url_path = base_endpoint + "orderList"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._resp_decoder = msgspec.json.Decoder(PhoenixSpotOrderOco)

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        OrderList (OCO) GET endpoint parameters.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        orderListId : str, optional
            The unique identifier of the order list to retrieve.
        origClientOrderId : str, optional
            The client specified identifier of the order list to retrieve.
        recvWindow : str, optional
            The response receive window in milliseconds for the request.
            Cannot exceed 60000.

        NOTE: Either orderListId or origClientOrderId must be provided.

        """

        timestamp: str
        orderListId: str | None = None
        origClientOrderId: str | None = None
        recvWindow: str | None = None

    class DeleteParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        OrderList (OCO) DELETE endpoint parameters.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        symbol : PhoenixSymbol
            The symbol of the order.
        orderListId : str, optional
            The unique identifier of the order list to retrieve.
        listClientOrderId : str, optional
            The client specified identifier of the order list to retrieve.
        newClientOrderId : str, optional
            Used to uniquely identify this cancel. Automatically generated
            by default.
        recvWindow : str, optional
            The response receive window in milliseconds for the request.
            Cannot exceed 60000.

        NOTE: Either orderListId or listClientOrderId must be provided.

        """

        timestamp: str
        symbol: PhoenixSymbol
        orderListId: str | None = None
        listClientOrderId: str | None = None
        newClientOrderId: str | None = None
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> PhoenixSpotOrderOco:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._resp_decoder.decode(raw)

    async def delete(self, parameters: DeleteParameters) -> PhoenixSpotOrderOco:
        method_type = HttpMethod.DELETE
        raw = await self._method(method_type, parameters)
        return self._resp_decoder.decode(raw)


class PhoenixSpotAllOrderListHttp(PhoenixHttpEndpoint):
    """
    Endpoint for querying all SPOT/MARGIN OCO orders.

    `GET /api/v3/allOrderList`

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
        url_path = base_endpoint + "allOrderList"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._resp_decoder = msgspec.json.Decoder(list[PhoenixSpotOrderOco])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of allOrderList GET request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        fromId : int, optional
            The order ID for the request.
            If included, request will return orders from this orderId INCLUSIVE.
        startTime : int, optional
            The start time (UNIX milliseconds) filter for the request.
        endTime : int, optional
            The end time (UNIX milliseconds) filter for the request.
        limit : int, optional
            The limit for the response.
            Default 500, max 1000
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        Warnings
        --------
        If fromId is specified, neither startTime endTime can be provided.

        """

        timestamp: str
        fromId: int | None = None
        startTime: int | None = None
        endTime: int | None = None
        limit: int | None = None
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixSpotOrderOco]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._resp_decoder.decode(raw)


class PhoenixSpotOpenOrderListHttp(PhoenixHttpEndpoint):
    """
    Endpoint for querying all SPOT/MARGIN OPEN OCO orders.

    `GET /api/v3/openOrderList`

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
        url_path = base_endpoint + "openOrderList"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._resp_decoder = msgspec.json.Decoder(list[PhoenixSpotOrderOco])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of allOrderList GET request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixSpotOrderOco]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._resp_decoder.decode(raw)


class PhoenixSpotAccountHttp(PhoenixHttpEndpoint):
    """
    Endpoint of current SPOT/MARGIN account information.

    `GET /api/v3/account`

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
        self._resp_decoder = msgspec.json.Decoder(PhoenixSpotAccountInfo)

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

    async def get(self, parameters: GetParameters) -> PhoenixSpotAccountInfo:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._resp_decoder.decode(raw)


class PhoenixSpotOrderRateLimitHttp(PhoenixHttpEndpoint):
    """
    Endpoint of current SPOT/MARGIN order count usage for all intervals.

    `GET /api/v3/rateLimit/order`

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
            HttpMethod.GET: PhoenixSecurityType.TRADE,
        }
        url_path = base_endpoint + "rateLimit/order"
        super().__init__(
            client,
            methods,
            url_path,
        )
        self._resp_decoder = msgspec.json.Decoder(list[PhoenixRateLimit])

    class GetParameters(msgspec.Struct, omit_defaults=True, frozen=True):
        """
        Parameters of rateLimit/order GET request.

        Parameters
        ----------
        timestamp : str
            The millisecond timestamp of the request.
        recvWindow : str, optional
            The response receive window for the request (cannot be greater than 60000).

        """

        timestamp: str
        recvWindow: str | None = None

    async def get(self, parameters: GetParameters) -> list[PhoenixRateLimit]:
        method_type = HttpMethod.GET
        raw = await self._method(method_type, parameters)
        return self._resp_decoder.decode(raw)


class PhoenixSpotAccountHttpAPI(PhoenixAccountHttpAPI):
    """
    Provides access to the `Phoenix Spot/Margin` Account/Trade HTTP REST API.

    Parameters
    ----------
    client : PhoenixHttpClient
        The Phoenix REST API client.
    clock : LiveClock,
        The clock for the API client.
    account_type : PhoenixAccountType
        The Phoenix account type, used to select the endpoint prefix.

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        clock: LiveClock,
        account_type: PhoenixAccountType = PhoenixAccountType.SPOT,
    ):
        super().__init__(
            client=client,
            clock=clock,
            account_type=account_type,
        )

        if not account_type.is_spot_or_margin:
            raise RuntimeError(  # pragma: no cover (design-time error)
                f"`PhoenixAccountType` not SPOT, MARGIN or ISOLATED_MARGIN, was {account_type}",  # pragma: no cover
            )

        # Create endpoints
        self._endpoint_spot_open_orders = PhoenixSpotOpenOrdersHttp(client, self.base_endpoint)
        self._endpoint_spot_order_oco = PhoenixSpotOrderOcoHttp(client, self.base_endpoint)
        self._endpoint_spot_order_list = PhoenixSpotOrderListHttp(client, self.base_endpoint)
        self._endpoint_spot_all_order_list = PhoenixSpotAllOrderListHttp(client, self.base_endpoint)
        self._endpoint_spot_open_order_list = PhoenixSpotOpenOrderListHttp(
            client,
            self.base_endpoint,
        )
        self._endpoint_spot_account = PhoenixSpotAccountHttp(client, self.base_endpoint)
        self._endpoint_spot_order_rate_limit = PhoenixSpotOrderRateLimitHttp(
            client,
            self.base_endpoint,
        )

    async def new_spot_oco(
        self,
        symbol: str,
        side: PhoenixOrderSide,
        quantity: str,
        price: str,
        stop_price: str,
        list_client_order_id: str | None = None,
        limit_client_order_id: str | None = None,
        limit_strategy_id: int | None = None,
        limit_strategy_type: int | None = None,
        limit_iceberg_qty: str | None = None,
        trailing_delta: str | None = None,
        stop_client_order_id: str | None = None,
        stop_strategy_id: int | None = None,
        stop_strategy_type: int | None = None,
        stop_limit_price: str | None = None,
        stop_iceberg_qty: str | None = None,
        stop_limit_time_in_force: PhoenixTimeInForce | None = None,
        new_order_resp_type: PhoenixNewOrderRespType | None = None,
        recv_window: str | None = None,
    ) -> PhoenixSpotOrderOco:
        """
        Send in a new spot OCO order to Phoenix.
        """
        if stop_limit_price is not None and stop_limit_time_in_force is None:
            raise RuntimeError(
                "stopLimitPrice cannot be provided without stopLimitTimeInForce.",
            )
        if stop_limit_time_in_force == PhoenixTimeInForce.GTX:
            raise RuntimeError(
                "stopLimitTimeInForce, Good Till Crossing (GTX) not supported.",
            )
        return await self._endpoint_spot_order_oco._post(
            parameters=self._endpoint_spot_order_oco.PostParameters(
                symbol=PhoenixSymbol(symbol),
                timestamp=self._timestamp(),
                side=side,
                quantity=quantity,
                price=price,
                stopPrice=stop_price,
                listClientOrderId=list_client_order_id,
                limitClientOrderId=limit_client_order_id,
                limitStrategyId=limit_strategy_id,
                limitStrategyType=limit_strategy_type,
                limitIcebergQty=limit_iceberg_qty,
                trailingDelta=trailing_delta,
                stopClientOrderId=stop_client_order_id,
                stopStrategyId=stop_strategy_id,
                stopStrategyType=stop_strategy_type,
                stopLimitPrice=stop_limit_price,
                stopIcebergQty=stop_iceberg_qty,
                stopLimitTimeInForce=stop_limit_time_in_force,
                newOrderRespType=new_order_resp_type,
                recvWindow=recv_window,
            ),
        )

    async def query_spot_oco(
        self,
        order_list_id: str | None = None,
        orig_client_order_id: str | None = None,
        recv_window: str | None = None,
    ) -> PhoenixSpotOrderOco:
        """
        Check single spot OCO order information.
        """
        if order_list_id is None and orig_client_order_id is None:
            raise RuntimeError(
                "Either orderListId or origClientOrderId must be provided.",
            )
        return await self._endpoint_spot_order_list.get(
            parameters=self._endpoint_spot_order_list.GetParameters(
                timestamp=self._timestamp(),
                orderListId=order_list_id,
                origClientOrderId=orig_client_order_id,
                recvWindow=recv_window,
            ),
        )

    async def cancel_all_open_orders(
        self,
        symbol: str,
        recv_window: str | None = None,
    ) -> bool:
        """
        Cancel all active orders on a symbol, including OCO.

        Returns whether successful.

        """
        await self._endpoint_spot_open_orders._delete(
            parameters=self._endpoint_spot_open_orders.DeleteParameters(
                timestamp=self._timestamp(),
                symbol=PhoenixSymbol(symbol),
                recvWindow=recv_window,
            ),
        )
        return True

    async def cancel_spot_oco(
        self,
        symbol: str,
        order_list_id: str | None = None,
        list_client_order_id: str | None = None,
        new_client_order_id: str | None = None,
        recv_window: str | None = None,
    ) -> PhoenixSpotOrderOco:
        """
        Delete spot OCO order from Phoenix.
        """
        if order_list_id is None and list_client_order_id is None:
            raise RuntimeError(
                "Either orderListId or listClientOrderId must be provided.",
            )
        return await self._endpoint_spot_order_list.delete(
            parameters=self._endpoint_spot_order_list.DeleteParameters(
                timestamp=self._timestamp(),
                symbol=PhoenixSymbol(symbol),
                orderListId=order_list_id,
                listClientOrderId=list_client_order_id,
                newClientOrderId=new_client_order_id,
                recvWindow=recv_window,
            ),
        )

    async def query_spot_all_oco(
        self,
        from_id: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
        recv_window: str | None = None,
    ) -> list[PhoenixSpotOrderOco]:
        """
        Check all spot OCO orders' information, matching provided filter parameters.
        """
        if from_id is not None and (start_time or end_time) is not None:
            raise RuntimeError(
                "Cannot specify both fromId and a startTime/endTime.",
            )
        return await self._endpoint_spot_all_order_list.get(
            parameters=self._endpoint_spot_all_order_list.GetParameters(
                timestamp=self._timestamp(),
                fromId=from_id,
                startTime=start_time,
                endTime=end_time,
                limit=limit,
                recvWindow=recv_window,
            ),
        )

    async def query_spot_all_open_oco(
        self,
        recv_window: str | None = None,
    ) -> list[PhoenixSpotOrderOco]:
        """
        Check all OPEN spot OCO orders' information.
        """
        return await self._endpoint_spot_open_order_list.get(
            parameters=self._endpoint_spot_open_order_list.GetParameters(
                timestamp=self._timestamp(),
                recvWindow=recv_window,
            ),
        )

    async def query_spot_account_info(
        self,
        recv_window: str | None = None,
    ) -> PhoenixSpotAccountInfo:
        """
        Check SPOT/MARGIN Phoenix account information.
        """
        return await self._endpoint_spot_account.get(
            parameters=self._endpoint_spot_account.GetParameters(
                timestamp=self._timestamp(),
                recvWindow=recv_window,
            ),
        )

    async def query_spot_order_rate_limit(
        self,
        recv_window: str | None = None,
    ) -> list[PhoenixRateLimit]:
        """
        Check SPOT/MARGIN order count/rateLimit.
        """
        return await self._endpoint_spot_order_rate_limit.get(
            parameters=self._endpoint_spot_order_rate_limit.GetParameters(
                timestamp=self._timestamp(),
                recvWindow=recv_window,
            ),
        )

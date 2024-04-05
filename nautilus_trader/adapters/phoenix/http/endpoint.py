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

from nautilus_trader.adapters.phoenix.common.enums import PhoenixSecurityType
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbol
from nautilus_trader.adapters.phoenix.common.schemas.symbol import PhoenixSymbols
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.core.nautilus_pyo3 import HttpMethod


def enc_hook(obj: Any) -> Any:
    if isinstance(obj, PhoenixSymbol):
        return str(obj)  # serialize PhoenixSymbol as string.
    elif isinstance(obj, PhoenixSymbols):
        return str(obj)  # serialize PhoenixSymbols as string.
    else:
        raise TypeError(f"Objects of type {type(obj)} are not supported")


class PhoenixHttpEndpoint:
    """
    Base functionality of endpoints connecting to the Phoenix REST API.

    Warnings
    --------
    This class should not be used directly, but through a concrete subclass.

    """

    def __init__(
        self,
        client: PhoenixHttpClient,
        methods_desc: dict[HttpMethod, PhoenixSecurityType],
        url_path: str,
    ):
        self.client = client
        self.methods_desc = methods_desc
        self.url_path = url_path

        self.decoder = msgspec.json.Decoder()
        self.encoder = msgspec.json.Encoder(enc_hook=enc_hook)

        self._method_request = {
            PhoenixSecurityType.NONE: self.client.send_request,
            PhoenixSecurityType.USER_STREAM: self.client.send_request,
            PhoenixSecurityType.MARKET_DATA: self.client.send_request,
            PhoenixSecurityType.TRADE: self.client.sign_request,
            PhoenixSecurityType.MARGIN: self.client.sign_request,
            PhoenixSecurityType.USER_DATA: self.client.sign_request,
        }

    async def _method(
        self,
        method_type: HttpMethod,
        parameters: Any,
        ratelimiter_keys: list[str] | None = None,
    ) -> bytes:
        payload: dict = self.decoder.decode(self.encoder.encode(parameters))
        if self.methods_desc[method_type] is None:
            raise RuntimeError(
                f"{method_type.name} not available for {self.url_path}",
            )
        raw: bytes = await self._method_request[self.methods_desc[method_type]](
            http_method=method_type,
            url_path=self.url_path,
            payload=payload,
            ratelimiter_keys=ratelimiter_keys,
        )
        return raw

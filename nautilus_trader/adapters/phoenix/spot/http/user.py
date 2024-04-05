# -------------------------------------------------------------------------------------------------
#  Copyright (C) 808putnam All rights reserved.
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


from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.adapters.phoenix.http.client import PhoenixHttpClient
from nautilus_trader.adapters.phoenix.http.user import PhoenixUserDataHttpAPI


class PhoenixSpotUserDataHttpAPI(PhoenixUserDataHttpAPI):
    """
    Provides access to the `Phoenix Spot/Margin` User Data HTTP REST API.

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
                f"`PhoenixAccountType` not SPOT, MARGIN or ISOLATED_MARGIN, was {account_type}",  # pragma: no cover (design-time error)
            )

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


from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.config import LiveDataClientConfig
from nautilus_trader.config import LiveExecClientConfig
from nautilus_trader.config import PositiveFloat
from nautilus_trader.config import PositiveInt


class PhoenixDataClientConfig(LiveDataClientConfig, frozen=True):
    """
    Configuration for ``PhoenixDataClient`` instances.

    Parameters
    ----------
    account_type : PhoenixAccountType, default PhoenixAccountType.SPOT
        The account type for the client.
    testnet : bool, default False
        If the client is connecting to a Solana testnet.

    """

    account_type: PhoenixAccountType = PhoenixAccountType.SPOT
    testnet: bool = False


class PhoenixExecClientConfig(LiveExecClientConfig, frozen=True):
    """
    Configuration for ``PhoenixExecutionClient`` instances.

    Parameters
    ----------
    account_type : PhoenixAccountType, default PhoenixAccountType.SPOT
        The account type for the client.
    testnet : bool, default False
        If the client is connecting to a Phoenix testnet.

    """

    account_type: PhoenixAccountType = PhoenixAccountType.SPOT
    testnet: bool = False

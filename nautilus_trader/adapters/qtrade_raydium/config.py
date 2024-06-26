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


from nautilus_trader.config import LiveDataClientConfig


class RaydiumDataClientConfig(LiveDataClientConfig, frozen=True):
    """
    Configuration for ``RaydiumDataClient`` instances.

    Parameters
    ----------
    auth_header : str, optional
        The bloXroute authentication header.
        If ``None`` then will source the system environment variable`AUTH_HEADER`.
    private_key : str, optional
        The user's private key.
        If ``None`` then will source the system environment variable `PRIVATE_KEY`.
    public_key : str, optional
        The user's public key.
        If ``None`` then will source the system environment variable `PUBLIC_KEY`.
    """

    auth_header: str | None = None
    private_key: str | None = None
    public_key: str | None = None
    
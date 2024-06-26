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


class RaydiumError(Exception):
    """
    The base class for all `Raydium` specific errors.
    """

    def __init__(self, status, message, headers):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers


class RaydiumServerError(RaydiumError):
    """
    Represents a `Raydium` specific 500 series HTTP error.
    """

    def __init__(self, status, message, headers):
        super().__init__(status, message, headers)


class RaydiumClientError(RaydiumError):
    """
    Represents a `Raydium` specific 400 series HTTP error.
    """

    def __init__(self, status, message, headers):
        super().__init__(status, message, headers)

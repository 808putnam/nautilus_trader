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

import json

from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType


################################################################################
# HTTP responses
################################################################################


class PhoenixSymbol(str):
    """
    Phoenix compatible symbol.
    """

    def __new__(cls, symbol: str | None):
        if symbol is not None:
            # Format the string on construction to be Phoenix compatible
            return super().__new__(
                cls,
                symbol.upper().replace(" ", "").replace("/", "").replace("-PERP", ""),
            )

    def parse_as_nautilus(self, account_type: PhoenixAccountType) -> str:
        if account_type.is_spot_or_margin:
            return str(self)

        # Parse Futures symbol
        if self[-1].isdigit():
            return str(self)  # Deliverable
        if self.endswith("_PERP"):
            return str(self).replace("_", "-")
        else:
            return str(self) + "-PERP"


class PhoenixSymbols(str):
    """
    Phoenix compatible list of symbols.
    """

    def __new__(cls, symbols: list[str] | None):
        if symbols is not None:
            phoenix_symbols: list[PhoenixSymbol] = [PhoenixSymbol(symbol) for symbol in symbols]
            return super().__new__(cls, json.dumps(phoenix_symbols).replace(" ", ""))

    def parse_str_to_list(self) -> list[PhoenixSymbol]:
        phoenix_symbols: list[PhoenixSymbol] = json.loads(self)
        return phoenix_symbols

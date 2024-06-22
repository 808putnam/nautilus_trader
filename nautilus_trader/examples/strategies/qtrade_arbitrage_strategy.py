# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2024 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
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

import pandas as pd

from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.trading.strategy import Strategy

# https://gist.githubusercontent.com/noxx3xxon/11fd224d7b99b78ee1e4a914bf0cbd22/raw/376a854183d4f2fc27e06058cfda2c5ea8e32efc/arbitrage.py
import numpy as np
import cvxpy as cp
import itertools


class QtradeArbitrageStrategyConfig(StrategyConfig, frozen=True):
    """
    Configuration for ``QtradeArbitrageStrategy`` instances.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.

    """

    # instrument_id: InstrumentId


class QtradeArbitrageStrategy(Strategy):
    """
    A qtrade arbitrage strategy.

    Parameters
    ----------
    config : QtradeArbitrageStrategyConfig
        The configuration for the instance.

    """

    def __init__(self, config: QtradeArbitrageStrategyConfig) -> None:
        super().__init__(config)

        # Configuration
        # self.instrument_id = config.instrument_id

    def on_start(self) -> None:
        """
        Actions to be performed when the strategy is started.
        """
        # Set a timer to fire at regular intervals
        self.clock.set_timer(
            name="MyTimer1",
            interval=pd.Timedelta(seconds=10),
        )

    def on_stop(self) -> None:
        """
        Actions to be performed when the strategy is stopped.
        """
        # Optionally implement

    def on_reset(self) -> None:
        """
        Actions to be performed when the strategy is reset.
        """
        # Optionally implement

    def on_dispose(self) -> None:
        """
        Actions to be performed when the strategy is disposed.

        Cleanup any resources used by the strategy here.

        """
        # Optionally implement

    def on_save(self) -> dict[str, bytes]:
        """
        Actions to be performed when the strategy is saved.

        Create and return a state dictionary of values to be saved.

        Returns
        -------
        dict[str, bytes]
            The strategy state dictionary.

        """
        return {}  # Optionally implement

    def on_load(self, state: dict[str, bytes]) -> None:
        """
        Actions to be performed when the strategy is loaded.

        Saved state values will be contained in the give state dictionary.

        Parameters
        ----------
        state : dict[str, bytes]
            The strategy state dictionary.

        """
        # Optionally implement

    def on_instrument(self, instrument: Instrument) -> None:
        """
        Actions to be performed when the strategy is running and receives an instrument.

        Parameters
        ----------
        instrument : Instrument
            The instrument received.

        """
        # https://nautilustrader.io/docs/latest/concepts/instruments
        # When an update to the instrument(s) is received by the DataEngine, 
        # the object(s) will be passed to the actors/strategies on_instrument() method. 
        # A user can override this method with actions to take upon receiving an instrument update.
        self.log.info(f"Instrument: {instrument}")

    def on_quote_tick(self, tick: QuoteTick) -> None:
        """
        Actions to be performed when the strategy is running and receives a quote tick.

        Parameters
        ----------
        tick : QuoteTick
            The tick received.

        """
        # Optionally implement

    def on_trade_tick(self, tick: TradeTick) -> None:
        """
        Actions to be performed when the strategy is running and receives a trade tick.

        Parameters
        ----------
        tick : TradeTick
            The tick received.

        """
        # Optionally implement

    def on_bar(self, bar: Bar) -> None:
        """
        Actions to be performed when the strategy is running and receives a bar.

        Parameters
        ----------
        bar : Bar
            The bar received.

        """
        # Optionally implement

    def buy(self) -> None:
        """
        Users simple buy method (example).
        """
        # Optionally implement

    def sell(self) -> None:
        """
        Users simple sell method (example).
        """
        # Optionally implement

    def on_data(self, data: Data) -> None:
        """
        Actions to be performed when the strategy is running and receives data.

        Parameters
        ----------
        data : Data
            The data received.

        """
        # Optionally implement

    def on_event(self, event: Event) -> None:
        """
        Actions to be performed when the strategy is running and receives an event.

        Parameters
        ----------
        event : Event
            The event received.

        """
        if event.name == "MyTimer1":
            self.log.info("MyTimer1 fired")
            # self.solve()
        else:
            self.log.info(f"Event name: {event.name}")

    # https://gist.githubusercontent.com/noxx3xxon/11fd224d7b99b78ee1e4a914bf0cbd22/raw/376a854183d4f2fc27e06058cfda2c5ea8e32efc/arbitrage.py
    def solve(self) -> None:
        # Problem data
        global_indices = list(range(4))

        # 0 = TOKEN-0
        # 1 = TOKEN-1
        # 2 = TOKEN-2
        # 3 = TOKEN-3

        local_indices = [
            [0, 1, 2, 3], # TOKEN-0/TOKEN-1/TOKEN-2/TOKEN-3
            [0, 1], # TOKEN-0/TOKEN-1
            [1, 2], # TOKEN-1/TOKEN-2
            [2, 3], # TOKEN-2/TOKEN-3
            [2, 3] # TOKEN-2/TOKEN-3
        ]

        reserves = list(map(np.array, [
            [4, 4, 4, 4], # balancer with 4 assets in pool TOKEN-0, TOKEN-1, TOKEN-2, TOKEN-3 (4 TOKEN-0, 4 TOKEN-1, 4 TOKEN-2 & 4 TOKEN-3 IN POOL)
            [10, 1], # uniswapV2 TOKEN-0/TOKEN-1 (10 TOKEN-0 & 1 TOKEN-1 IN POOL)
            [1, 5], # uniswapV2 TOKEN-1/TOKEN-2 (1 TOKEN-1 & 5 TOKEN-2 IN POOL)
            [40, 50], # uniswapV2 TOKEN-2/TOKEN-3  (40 TOKEN-2 & 50 TOKEN-3 IN POOL)
            [10, 10] # constant_sum TOKEN-2/TOKEN-3 (10 TOKEN-2 & 10 TOKEN-3 IN POOL)
        ]))

        fees = [
            .998, # balancer fees
            .997, # uniswapV2 fees
            .997, # uniswapV2 fees
            .997, # uniswapV2 fees
            .999 # constant_sum fees
        ]

        # "Market value" of tokens (say, in a centralized exchange)
        market_value = [
            1.5, # TOKEN-0
            10, # TOKEN-1
            2, # TOKEN-2
            3 # TOKEN-3
        ] 

        # Build local-global matrices
        n = len(global_indices)
        m = len(local_indices)

        A = []
        for l in local_indices: # for each CFMM
            n_i = len(l) # n_i = number of tokens avaiable for CFMM i
            A_i = np.zeros((n, n_i)) # Create matrix of 0's
            for i, idx in enumerate(l):
                A_i[idx, i] = 1
            A.append(A_i)

        # Build variables

        # tender delta
        deltas = [cp.Variable(len(l), nonneg=True) for l in local_indices]

        # receive lambda
        lambdas = [cp.Variable(len(l), nonneg=True) for l in local_indices]

        psi = cp.sum([A_i @ (L - D) for A_i, D, L in zip(A, deltas, lambdas)])

        # Objective is to maximize "total market value" of coins out
        obj = cp.Maximize(market_value @ psi) # matrix multiplication

        # Reserves after trade
        new_reserves = [R + gamma_i*D - L for R, gamma_i, D, L in zip(reserves, fees, deltas, lambdas)]

        # Trading function constraints
        cons = [
            # Balancer pool with weights 4, 3, 2, 1
            cp.geo_mean(new_reserves[0], p=np.array([4, 3, 2, 1])) >= cp.geo_mean(reserves[0]),

            # Uniswap v2 pools
            cp.geo_mean(new_reserves[1]) >= cp.geo_mean(reserves[1]),
            cp.geo_mean(new_reserves[2]) >= cp.geo_mean(reserves[2]),
            cp.geo_mean(new_reserves[3]) >= cp.geo_mean(reserves[3]),

            # Constant sum pool
            cp.sum(new_reserves[4]) >= cp.sum(reserves[4]),
            new_reserves[4] >= 0,

            # Arbitrage constraint
            psi >= 0
        ]

        # Set up and solve problem
        prob = cp.Problem(obj, cons)
        prob.solve()


        # Trade Execution Ordering

        current_tokens = [0, 0, 0, 0]
        new_current_tokens = [0, 0, 0, 0]
        tokens_required_arr = []
        tokens_required_value_arr = []

        pool_names = ["BALANCER 0/1/2/3", "UNIV2 0/1", "UNIV2 1/2", "UNIV2 2/3", "CONSTANT SUM 2/3"]

        permutations = itertools.permutations(list(range(len(local_indices))), len(local_indices))
        permutations2 = []
        for permutation in permutations:
            permutations2.append(permutation)
            current_tokens = [0, 0, 0, 0]
            new_current_tokens = [0, 0, 0, 0]   
            tokens_required = [0, 0, 0, 0]
            for pool_id in permutation:
                pool = local_indices[pool_id]
                for global_token_id in pool:
                    local_token_index = pool.index(global_token_id)
                    new_current_tokens[global_token_id] = current_tokens[global_token_id] + (lambdas[pool_id].value[local_token_index] - deltas[pool_id].value[local_token_index])

                    if new_current_tokens[global_token_id] < 0 and new_current_tokens[global_token_id] < current_tokens[global_token_id]:
                        if current_tokens[global_token_id] < 0:
                            tokens_required[global_token_id] += (current_tokens[global_token_id] - new_current_tokens[global_token_id])
                            new_current_tokens[global_token_id] = 0
                        else:
                            tokens_required[global_token_id] += (-new_current_tokens[global_token_id])
                            new_current_tokens[global_token_id] = 0
                    current_tokens[global_token_id] = new_current_tokens[global_token_id]

            tokens_required_value = []
            for i1, i2 in zip(tokens_required, market_value):
                tokens_required_value.append(i1*i2)

            tokens_required_arr.append(tokens_required)
            tokens_required_value_arr.append(sum(tokens_required_value))

        min_value = min(tokens_required_value_arr)
        min_value_index = tokens_required_value_arr.index(min_value)


        print("\n-------------------- ARBITRAGE TRADES + EXECUTION ORDER --------------------\n")
        for pool_id in permutations2[min_value_index]:
            pool = local_indices[pool_id]
            print(f"\nTRADE POOL = {pool_names[pool_id]}")

            for global_token_id in pool:
                local_token_index = pool.index(global_token_id)
                if (lambdas[pool_id].value[local_token_index] - deltas[pool_id].value[local_token_index]) < 0:  
                    print(f"\tTENDERING {-(lambdas[pool_id].value[local_token_index] - deltas[pool_id].value[local_token_index])} TOKEN {global_token_id}")
            
            for global_token_id in pool:
                local_token_index = pool.index(global_token_id)
                if (lambdas[pool_id].value[local_token_index] - deltas[pool_id].value[local_token_index]) >= 0:  
                    print(f"\tRECEIVEING {(lambdas[pool_id].value[local_token_index] - deltas[pool_id].value[local_token_index])} TOKEN {global_token_id}")


        print("\n-------------------- REQUIRED TOKENS TO KICK-START ARBITRAGE --------------------\n")
        print(f"TOKEN-0 = {tokens_required_arr[min_value_index][0]}")
        print(f"TOKEN-1 = {tokens_required_arr[min_value_index][1]}")
        print(f"TOKEN-2 = {tokens_required_arr[min_value_index][2]}")
        print(f"TOKEN-3 = {tokens_required_arr[min_value_index][3]}")

        print(f"\nUSD VALUE REQUIRED = ${min_value}")

        print("\n-------------------- TOKENS & VALUE RECEIVED FROM ARBITRAGE --------------------\n")
        net_network_trade_tokens = [0, 0, 0, 0]
        net_network_trade_value = [0, 0, 0, 0]

        for pool_id in permutations2[min_value_index]:
            pool = local_indices[pool_id]
            for global_token_id in pool:
                local_token_index = pool.index(global_token_id)
                net_network_trade_tokens[global_token_id] += lambdas[pool_id].value[local_token_index]
                net_network_trade_tokens[global_token_id] -= deltas[pool_id].value[local_token_index]

        for i in range(0, len(net_network_trade_tokens)):
            net_network_trade_value[i] = net_network_trade_tokens[i] * market_value[i]

        print(f"RECEIVED {net_network_trade_tokens[0]} TOKEN-0 = ${net_network_trade_value[0]}")
        print(f"RECEIVED {net_network_trade_tokens[1]} TOKEN-1 = ${net_network_trade_value[1]}")
        print(f"RECEIVED {net_network_trade_tokens[2]} TOKEN-2 = ${net_network_trade_value[2]}")
        print(f"RECEIVED {net_network_trade_tokens[3]} TOKEN-3 = ${net_network_trade_value[3]}")

        print(f"\nSUM OF RECEIVED TOKENS USD VALUE = ${sum(net_network_trade_value)}")
        print(f"CONVEX OPTIMISATION SOLVER RESULT: ${prob.value}\n")


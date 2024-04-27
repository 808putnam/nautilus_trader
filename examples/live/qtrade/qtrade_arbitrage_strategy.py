#!/usr/bin/env python3
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

from decimal import Decimal

from nautilus_trader.adapters.phoenix.common.enums import PhoenixAccountType
from nautilus_trader.adapters.phoenix.config import PhoenixDataClientConfig
from nautilus_trader.adapters.phoenix.config import PhoenixExecClientConfig
from nautilus_trader.adapters.phoenix.factories import PhoenixLiveDataClientFactory
from nautilus_trader.adapters.phoenix.factories import PhoenixLiveExecClientFactory
from nautilus_trader.config import CacheConfig
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LiveExecEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.examples.strategies.arbitrage_orderbook_imbalance_rust import ArbitrageOrderBookImbalance
from nautilus_trader.examples.strategies.arbitrage_orderbook_imbalance_rust import ArbitrageOrderBookImbalanceConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TraderId

# qtrade: bloxroute
# import asyncio
# import base58
# import bxsolana
# from bxsolana import provider

# *** THIS IS A TEST STRATEGY WITH NO ALPHA ADVANTAGE WHATSOEVER. ***
# *** IT IS NOT INTENDED TO BE USED TO TRADE LIVE WITH REAL MONEY. ***


# qtrade: bloxroute
# key_array = <insert from ~/.config/solana/id.json>
# full_key = key_array[0:64]
# secret_key = key_array[0:32]
# public_key = key_array[32:64]
# key = base58.b58encode(bytes(full_key)).decode()
# sk = base58.b58encode(bytes(secret_key)).decode()
# pk = base58.b58encode(bytes(public_key)).decode()
# print(key)
# print(sk)
# print(pk)


# Configure the trading node
config_node = TradingNodeConfig(
    trader_id=TraderId("TESTER-001"),
    logging=LoggingConfig(
        log_level="INFO",
        # log_level_file="DEBUG",
        # log_file_format="json",
    ),
    exec_engine=LiveExecEngineConfig(
        reconciliation=True,
        reconciliation_lookback_mins=1440,
        filter_position_reports=True,
    ),
    cache=CacheConfig(
        database=None,
        timestamps_as_iso8601=True,
        flush_on_start=False,
    ),
    # snapshot_orders=True,
    # snapshot_positions=True,
    # snapshot_positions_interval=5.0,
    # See adapters/phoenix/factories.py for listing of urls
    data_clients={
        "PHOENIX": PhoenixDataClientConfig(
            account_type=PhoenixAccountType.SPOT,
            testnet=True,  # If client uses the Solana testnet
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
    exec_clients={
        "PHOENIX": PhoenixExecClientConfig(
            account_type=PhoenixAccountType.SPOT,
            testnet=True,  # If client uses the Solana testnet
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
    timeout_connection=20.0,
    timeout_reconciliation=10.0,
    timeout_portfolio=10.0,
    timeout_disconnection=10.0,
    timeout_post_stop=5.0,
)

# qtrade: bloxroute
# async def prep_bxsolana():
#     # async with provider.http() as api:
#     #     print(await api.get_orderbook(market="ETHUSDT"))
# 
#     p = provider.grpc_testnet()
#     api = await bxsolana.trader_api(p)
# # 
#     try:
#         await api.get_orderbook(market="ETHUSDT")
#     finally:
#         p.close()
# 
# asyncio.run(prep_bxsolana())

# Instantiate the node with a configuration
node = TradingNode(config=config_node)

# Configure your strategy
strat_config = ArbitrageOrderBookImbalanceConfig(
    instrument_id=InstrumentId.from_str("ETHUSDT.BINANCE"),
    external_order_claims=[InstrumentId.from_str("ETHUSDT.BINANCE")],
    max_trade_size=Decimal("0.010"),
)

# Instantiate your strategy
strategy = ArbitrageOrderBookImbalance(config=strat_config)

# Add your strategies and modules
node.trader.add_strategy(strategy)

# Register your client factories with the node (can take user defined factories)
node.add_data_client_factory("PHOENIX", PhoenixLiveDataClientFactory)
node.add_exec_client_factory("PHOENIX", PhoenixLiveExecClientFactory)
node.build()


# Stop and dispose of the node with SIGINT/CTRL+C
if __name__ == "__main__":
    try:
        node.run()
    finally:
        node.dispose()

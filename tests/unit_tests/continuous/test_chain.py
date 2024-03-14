from pathlib import Path

import pandas as pd
from nautilus_trader.backtest.data_client import BacktestMarketDataClient
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import TestClock
from nautilus_trader.common.component import Logger
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.enums import LogLevel
from nautilus_trader.config import DataEngineConfig
from nautilus_trader.core.nautilus_pyo3.persistence import DataBackendSession
from nautilus_trader.core.nautilus_pyo3.persistence import NautilusDataType
from nautilus_trader.data.engine import DataEngine
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import capsule_to_list
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.portfolio.portfolio import Portfolio
from nautilus_trader.test_kit.stubs.identifiers import TestIdStubs

from nautilus_trader import PACKAGE_ROOT
from nautilus_trader.continuous.chain import ContractChain
from nautilus_trader.continuous.config import ContractChainConfig
from nautilus_trader.continuous.config import RollConfig
from nautilus_trader.continuous.contract_month import ContractMonth
from nautilus_trader.continuous.cycle import RollCycle
from nautilus_trader.continuous.contract_month import MONTH_LIST


class TestMultipleData:
    def setup(self):
        
        self.clock = TestClock()
        self.logger = Logger(
            clock=self.clock,
            level_stdout=LogLevel.DEBUG,
            # bypass=True,
        )

        self.msgbus = MessageBus(
            trader_id=TestIdStubs.trader_id(),
            clock=self.clock,
            logger=self.logger,
        )

        self.cache = Cache(logger=self.logger)

        self.portfolio = Portfolio(
            self.msgbus,
            self.cache,
            self.clock,
            self.logger,
        )

        self.data_engine = DataEngine(
            msgbus=self.msgbus,
            cache=self.cache,
            clock=self.clock,
            logger=self.logger,
            config=DataEngineConfig(debug=True),
        )

        self.chain_config = ContractChainConfig(
            bar_type=BarType.from_str("MES=MES=FUT.SIM-1-DAY-MID-EXTERNAL"),
            roll_config=RollConfig(
                hold_cycle=RollCycle("HMUZ"),
                priced_cycle=RollCycle("HMUZ"),
                roll_offset=-5,
                approximate_expiry_offset=14,
                carry_offset=1,
            ),
            start_month=ContractMonth("2021H"),
        )
        
        self.chain = ContractChain(config=config)
        
        self.chain.register_base(
            portfolio=self.portfolio,
            msgbus=self.msgbus,
            cache=self.cache,
            clock=self.clock,
        )
        self.chain.start()

        self._data_engine.start()
        
        folder = Path(PACKAGE_ROOT) / "tests/unit_tests/continuous/data"
        paths = [
            folder / "MES=MES=FUT=2021H.SIM-1-DAY-MID-EXTERNAL-0.parquet",
            folder / "MES=MES=FUT=2021M.SIM-1-DAY-MID-EXTERNAL-0.parquet",
            folder / "MES=MES=FUT=2021U.SIM-1-DAY-MID-EXTERNAL-0.parquet",
            folder / "MES=MES=FUT=2021Z.SIM-1-DAY-MID-EXTERNAL-0.parquet",
            
        ]
        
        session = DataBackendSession()

        for i, path in enumerate(paths):
            session.add_file(NautilusDataType.Bar, f"data{i}", str(path))

        self.bars = []

        for chunk in session.to_query_result():
            self.bars.extend(capsule_to_list(chunk))

        self.bars = sorted(
            self.bars,
            key=lambda x: (
                x.ts_init,
                MONTH_LIST.index(x.bar_type.instrument_id.symbol.value[-1]),
            ),
        )

    def test_chain_adds_rolls(self):
        
        for bar in self.bars:
            self.data_engine.process(bar)
            
            
#         chain = ContractChain(
#             bar_type=BarType.from_str("MES.IB-1-DAY-MID-EXTERNAL"),
#             config=self.chain_config,
#             instrument_provider=self.instrument_provider,
#         )

#         data_d1 = MultipleData(
#             bar_type=BarType.from_str("MES.IB-1-DAY-MID-EXTERNAL"),
#             chain=chain,
#         )
#         data_m1 = MultipleData(
#             bar_type=BarType.from_str("MES.IB-1-MINUTE-MID-EXTERNAL"),
#             chain=chain,
#         )

#         for actor in [chain, data_d1, data_m1]:
#             actor.register_base(
#                 portfolio=self.portfolio,
#                 msgbus=self.msgbus,
#                 cache=self.cache,
#                 clock=self.clock,
#                 logger=self.logger,
#             )
#             actor.start()

#         self.data_engine.start()

#         prices_d1 = []
#         self.msgbus.subscribe(
#             topic=data_d1.topic,
#             handler=prices_d1.append,
#         )

#         prices_m1 = []
#         self.msgbus.subscribe(
#             topic=data_m1.topic,
#             handler=prices_m1.append,
#         )

#         for bar in self.bars:
#             self.data_engine.process(bar)

#         assert len(prices_d1) == 111
#         assert len(prices_m1) == 3803

#         assert prices_d1[-1].current_month == ContractMonth("1998M")
#         assert prices_m1[-1].current_month == ContractMonth("1998M")

#         assert chain.rolls.iloc[0].month.value == "1998M"
#         assert chain.rolls.iloc[0].timestamp == pd.Timestamp("1998-03-10", tz="UTC")

#     def test_chain_for_each_data(self):
#         chain_d1 = ContractChain(
#             bar_type=BarType.from_str("MES.IB-1-DAY-MID-EXTERNAL"),
#             config=self.chain_config,
#             instrument_provider=self.instrument_provider,
#         )
#         data_d1 = MultipleData(
#             bar_type=BarType.from_str("MES.IB-1-DAY-MID-EXTERNAL"),
#             chain=chain_d1,
#         )

#         chain_m1 = ContractChain(
#             bar_type=BarType.from_str("MES.IB-1-MINUTE-MID-EXTERNAL"),
#             config=self.chain_config,
#             instrument_provider=self.instrument_provider,
#         )
#         data_m1 = MultipleData(
#             bar_type=BarType.from_str("MES.IB-1-MINUTE-MID-EXTERNAL"),
#             chain=chain_m1,
#         )

#         for actor in [chain_m1, chain_d1, data_d1, data_m1]:
#             actor.register_base(
#                 portfolio=self.portfolio,
#                 msgbus=self.msgbus,
#                 cache=self.cache,
#                 clock=self.clock,
#                 logger=self.logger,
#             )
#             actor.start()

#         self.data_engine.start()

#         prices_d1 = []
#         self.msgbus.subscribe(
#             topic=data_d1.topic,
#             handler=prices_d1.append,
#         )

#         prices_m1 = []
#         self.msgbus.subscribe(
#             topic=data_m1.topic,
#             handler=prices_m1.append,
#         )

#         for bar in self.bars:
#             self.data_engine.process(bar)

#         assert len(prices_d1) == 111
#         assert len(prices_m1) == 3756

#         assert prices_d1[-1].current_month == ContractMonth("1998M")
#         assert prices_m1[-1].current_month == ContractMonth("1998M")

#         assert chain_d1.rolls.iloc[0].month.value == "1998M"
#         assert chain_d1.rolls.iloc[0].timestamp == pd.Timestamp("1998-03-10", tz="UTC")

#         assert chain_m1.rolls.iloc[0].month.value == "1998M"
#         assert chain_m1.rolls.iloc[0].timestamp == pd.Timestamp("1998-03-10 13:17", tz="UTC")

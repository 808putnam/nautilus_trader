from nautilus_trader.backtest.data_client import BacktestMarketDataClient
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.component import TestClock
from nautilus_trader.config import DataEngineConfig
from nautilus_trader.data.engine import DataEngine
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.portfolio.portfolio import Portfolio
from nautilus_trader.test_kit.stubs.identifiers import TestIdStubs
from nautilus_trader.continuous.config import ContractChainConfig
from nautilus_trader.common.component import TimeEvent
from nautilus_trader.continuous.contract_month import ContractMonth
from nautilus_trader.continuous.chain import ContractChain
from nautilus_trader.core.uuid import UUID4

import itertools

class ContinuousBarWrangler:
    def __init__(
        self,
        config: ContractChainConfig,
        end_month: ContractMonth,
    ):
        
        assert isinstance(end_month, ContractMonth)
        
        self._clock = TestClock()
        
        self._msgbus = MessageBus(
            trader_id=TestIdStubs.trader_id(),
            clock=self._clock,
        )

        cache = Cache()

        portfolio = Portfolio(
            self._msgbus,
            cache,
            self._clock,
        )
        self._chain = ContractChain(config=config)
        
        self._chain.register_base(
            portfolio=portfolio,
            msgbus=self._msgbus,
            cache=cache,
            clock=self._clock,
        )
        
        self._data_engine = DataEngine(
            msgbus=self._msgbus,
            cache=cache,
            clock=self._clock,
        )
        
        self._data_engine.start()
        
        self._end_month = end_month

    def process(self, bars: list[Bar]) -> dict[int, list[Bar]]:
        
        # TODO assert bar_type format
        # TODO assert same bar_spec
        # TODO: assert sorted
        # TODO: assert same venue
        
        bars = sorted(bars, key=lambda x: x.ts_init)
        
        last = {k: list(g)[-1].ts_init for k, g in \
            itertools.groupby(bars, key=lambda x: x.bar_type.instrument_id.symbol.value.split("=")[-1].split(".")[0])}
        
        self._clock.set_time(bars[0].ts_init)
        
        self._chain.start()
        
        results = {}
        
        results[-1] = []
        self._msgbus.subscribe(
            topic=f"{self._chain.bar_type}-1",
            handler=results[-1].append,
        )
        
        results[0] = []
        self._msgbus.subscribe(
            topic=f"{self._chain.bar_type}",
            handler=results[0].append,
        )
        
        results[1] = []
        self._msgbus.subscribe(
            topic=f"{self._chain.bar_type}-1",
            handler=results[1].append,
        )
        
        previous_timestamp = None
        
        for bar in bars:
            
            is_next = previous_timestamp is not None and bar.ts_init > previous_timestamp
            if is_next:
                self._chain.handle_time_event(
                    TimeEvent(
                        name=f"chain_{self._chain.bar_type}",
                        event_id=UUID4(),
                        ts_event=0,
                        ts_init=0,
                    )
                )
                
            self._data_engine.process(bar)
            
            last_timestamp = last[str(self._chain.current_month)]
            if bar.ts_init > last_timestamp:
                raise RuntimeError("Failed to roll: last bar received for current contract")
            
            if self._chain.current_month == self._end_month:
                break
            
            previous_timestamp = bar.ts_init
            
            
        return results
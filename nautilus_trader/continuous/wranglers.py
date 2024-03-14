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

from nautilus_trader.continuous.contract_month import ContractMonth
from nautilus_trader.continuous.chain import ContractChain
from nautilus_trader.continuous.cycle import MONTH_LIST

class ContinuousBarWrangler:
    def __init__(
        self,
        config: ContractChainConfig,
        end_month: ContractMonth,
    ):
        
        assert isinstance(end_month, ContractMonth)
        
        clock = TestClock()

        self._msgbus = MessageBus(
            trader_id=TestIdStubs.trader_id(),
            clock=clock,
        )

        cache = Cache()

        portfolio = Portfolio(
            self._msgbus,
            cache,
            clock,
        )
        chain = ContractChain(config=config)
        
        chain.register_base(
            portfolio=portfolio,
            msgbus=self._msgbus,
            cache=cache,
            clock=clock,
        )
        chain.start()

        self._data_engine.start()
        
        self._end_month = end_month

    def process(self, bars: list[Bar], sort: bool = True) -> dict[int, list[Bar]]:
        
        # TODO assert bar_type format
        # TODO assert same bar_spec
        
        # Group the data by the key
        
        # sort bars by previous -> current -> forward
        if sort:
            bars = sorted(
                bars,
                key=lambda x: (
                    x.ts_init,
                    MONTH_LIST.index(x.bar_type.instrument_id.symbol.value[-1]),
                ),
            )
        
        grouped = groupby(data, key=lambda x: x.bar_type.instrument_id.symbol.value[-1])
        for key, bars in grouped:
            print(key, len(bars))
            exit()
        
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
    
        for bar in bars:
            self._data_engine.process(bar)
            
            if self._chain.current_month == self._end_month:
                break
            
            # if bar is last in the contract and current bar_type
            
            
        return results
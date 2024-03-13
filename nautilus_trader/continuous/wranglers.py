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

class ContinuousBarWrangler:
    def __init__(
        self,
        config: ContractChainConfig,
        end_month: ContractMonth,
    ):
        
        assert isinstance(end_month, ContractMonth)
        
        clock = TestClock()

        msgbus = MessageBus(
            trader_id=TestIdStubs.trader_id(),
            clock=clock,
        )

        cache = Cache()

        portfolio = Portfolio(
            msgbus,
            cache,
            clock,
        )
        chain = ContractChain(config=config)
        
        chain.register_base(
            portfolio=portfolio,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )
        chain.start()

        self.data_engine.start()
        
        self._end_month = end_month

    def process_bars(self, bars: list[Bar]) -> dict[int, list[Bar]]:
        # TODO: sort bars carry -> forward -> current
        results = {}
        
        results[-1] = []
        msgbus.subscribe(
            topic=f"{self.chain.bar_type}-1",
            handler=results[-1].append,
        )
        
        results[0] = []
        msgbus.subscribe(
            topic=f"{self.chain.bar_type}",
            handler=results[0].append,
        )
        
        results[1] = []
        msgbus.subscribe(
            topic=f"{self.chain.bar_type}-1",
            handler=results[1].append,
        )
        
        for bar in bars:
            self.data_engine.process(bar)
            
            if self._chain.current_month == self._end_month:
                break

        return results
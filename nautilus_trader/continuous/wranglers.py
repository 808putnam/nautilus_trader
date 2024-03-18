import pandas as pd
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
from nautilus_trader.continuous.chain import ContractExpired
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.core.datetime import dt_to_unix_nanos

import itertools

class ContinuousBarWrangler:
    """
    end_month: ContractMonth
        The end month in the hold cycle the wrangler should stop at. The data
        returned from the wrangler will include the end month (inclusive).
    """
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

        self._cache = Cache()

        portfolio = Portfolio(
            self._msgbus,
            self._cache,
            self._clock,
        )
        self._chain_config = config
        self._chain = ContractChain(config=self._chain_config)
        
        self._chain.register_base(
            portfolio=portfolio,
            msgbus=self._msgbus,
            cache=self._cache,
            clock=self._clock,
        )
        
        self._data_engine = DataEngine(
            msgbus=self._msgbus,
            cache=self._cache,
            clock=self._clock,
        )
        
        self._data_engine.start()
        
        self._end_month = end_month
        
        self._start_month = self._chain_config.start_month
        assert self._start_month is not None
        assert self._end_month > self._start_month
        
        self._roll_config = self._chain_config.roll_config
        self._expiry_offset = self._roll_config.approximate_expiry_offset
        self._roll_offset = self._roll_config.roll_offset
            
    def process(self, bars: list[Bar]) -> dict[int, list[Bar]]:
        
        # TODO assert bar_type format
        # TODO assert same bar_spec
        # TODO: assert sorted
        # TODO: assert same venue
        # TODO: check end_month has forward month, otherwise fail to roll to end_month
        
        bars = sorted(bars, key=lambda x: x.ts_init)
        
        bars_by_month = {k: list(g) for k, g in \
            itertools.groupby(bars, key=lambda x: x.bar_type.instrument_id.symbol.value.split("=")[-1].split(".")[0])}
        
        last_timestamps = {month: bars[-1].ts_init for month, bars in bars_by_month.items()}
        
        self._clock.set_time(bars[0].ts_init)
        
        self._chain.start()
        
        results = {}
        
        results["0"] = []
        self._msgbus.subscribe(
            topic=f"{self._chain.bar_type}",
            handler=results["0"].append,
        )
        
        results["+1"] = []
        self._msgbus.subscribe(
            topic=f"{self._chain.bar_type}+1",
            handler=results["+1"].append,
        )
        
        results["c"] = []
        self._msgbus.subscribe(
            topic=f"{self._chain.bar_type}c",
            handler=results["c"].append,
        )
        
        previous_timestamp = None
        
        for bar in bars:
            
            self._cache.add_bar(bar)
            
            is_next = previous_timestamp is not None and bar.ts_init > previous_timestamp
            if is_next:
                try:
                    self._chain.handle_time_event(
                        TimeEvent(
                            name=f"chain_{self._chain.bar_type}",
                            event_id=UUID4(),
                            ts_event=0,
                            ts_init=0,
                        )
                    )
                except ContractExpired:
                    print(
                        f"""
                        The chain failed to roll from {self._chain.current_month} to {self._chain.forward_month}.
                        
                        This could be caused by:
                        
                        The current contract and forward contract bars do not overlap and therefore a matching timestamp from each
                        dataset is not found to satisfy the roll.
                        The current contract or forward contract bars end before the roll date.
                        The current contract or forward contract bars start after the expiry date.
                        """
                    )
                    raise
                
                if self._chain.current_month == self._end_month:
                    break
                    
            self._data_engine.process(bar)
            
            # last_timestamp = last_timestamps[self._chain.current_month.value]
            # if bar.ts_init > last_timestamp:
            #     raise RuntimeError(
            #         f"The chain did not roll after receiving the last current contract bar for {self._chain.current_month}."
            #     )
            
            
            previous_timestamp = bar.ts_init
        
        return results
    
    
    def validate(self, bars: list[Bar]) -> None:
        
        bars = sorted(bars, key=lambda x: x.ts_init)
        
        timestamps_by_month = {k: [b.ts_init for b in g] for k, g in \
            itertools.groupby(bars, key=lambda x: x.bar_type.instrument_id.symbol.value.split("=")[-1].split(".")[0])}
        
        hold_cycle = self._chain_config.roll_config.hold_cycle
        
        months = list(hold_cycle.iterate(
            start=self._start_month,
            end=self._end_month,
            direction=1,
        ))

        missing = [
            m.value for m in months + [self._end_month]
            if timestamps_by_month.get(m.value) is None
        ]
        if len(missing) > 0:
            raise ValueError(f"Data validation failed: months {missing} have no timestamps")
        
        for current_month in months:
            
            start, end = current_month.roll_window(
                approximate_expiry_offset=self._expiry_offset,
                roll_offset=self._roll_offset
            )
            
            start_ns = dt_to_unix_nanos(start)
            end_ns = dt_to_unix_nanos(end)
            
            # check current contract timestamps exist in roll window
            current_timestamps = {
                t for t in timestamps_by_month[current_month.value] if t >= start_ns and t < end_ns
            }
            if len(current_timestamps) == 0:
                raise ValueError(f"Data validation failed: {current_month} has no timestamps in roll window {start} to {end}")
            
            # check forward contract timestamps exist in roll window
            forward_month = hold_cycle.next_month(current_month)
            forward_timestamps = {
                t for t in timestamps_by_month[forward_month.value] if t >= start_ns and t < end_ns
            }
            if len(forward_timestamps) == 0:
                raise ValueError(f"Data validation failed: {forward_month} has no timestamps in roll window {start} to {end}")
            
            
            # check matching timestamps for current and forward contract exist in roll window
            is_matching = len(current_timestamps & forward_timestamps) > 0
            if not is_matching:
                raise ValueError(f"Data validation failed: {current_month} and {forward_month} have no matching timestamps in roll window {start} to {end}")
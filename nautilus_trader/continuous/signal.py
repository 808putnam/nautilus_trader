from typing import Callable

import pandas as pd

from nautilus_trader.common.actor import Actor
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.continuous.chain import ContractChain
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.continuous.actor import ChainActor

class RollSignal(ChainActor):
    """
    Listens to contract bars and triggers a roll event
    """
    def __init__(
        self,
        bar_type: BarType,
        chain: ContractChain,
        raise_expired: bool = True,
        ignore_expiry_date: bool = False,
    ):
        
        super().__init__(
            bar_type=bar_type,
            chain=chain,
        )
        self._raise_expired = raise_expired
        self._ignore_expiry_date = ignore_expiry_date
    
    def on_bar(self, bar: Bar) -> None:
        
        # self.msgbus.topics
        
        current_bar_type = self.current_bar_type
        forward_bar_type = self.forward_bar_type
        
        if bar.bar_type != current_bar_type and bar.bar_type != forward_bar_type:
            return False
        
        current_bar = self.cache.bar(current_bar_type)
        forward_bar = self.cache.bar(forward_bar_type)
        
        # next bar arrived before current or vice versa
        if current_bar is None or forward_bar is None:
            return
        
        current_timestamp = unix_nanos_to_dt(current_bar.ts_event)
        forward_timestamp = unix_nanos_to_dt(forward_bar.ts_event)
        
        expiry_day = self._chain.expiry_date.floor("D")
        roll_date = self._chain.roll_date
        
        if self._raise_expired:
            is_expired = unix_nanos_to_dt(bar.ts_event) >= (expiry_day + pd.Timedelta(days=1))
            if is_expired:
                # TODO: wait for next forward bar != last timestamp
                raise ValueError(f"ContractExpired {self._bar_type}")
        
        
        if self._ignore_expiry_date:
            in_roll_window = (current_timestamp >= roll_date)
        else:
            current_day = current_timestamp.floor("D")
            in_roll_window = (current_timestamp >= roll_date) and (current_day <= expiry_day)
        
        # a valid roll time is where both timestamps are equal
        should_roll = in_roll_window and current_timestamp == forward_timestamp
        if should_roll:
            self._chain.roll()
     
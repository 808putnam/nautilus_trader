from __future__ import annotations

from collections.abc import Callable

import pandas as pd
from nautilus_trader.model.objects import Price
from nautilus_trader.common.actor import Actor
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.model.data.bar import Bar
from nautilus_trader.model.data.bar import BarType
from nautilus_trader.model.continuous.price import ContinuousPrice

class ContinuousData(Actor):
    def __init__(
        self,
        bar_type: BarType,
        start: str | None = None,
        handler: Callable | None = None,
    ):
        super().__init__()

        self._bar_type = bar_type
        self._current_id = start
        self._handler = handler
        self._instrument_id = bar_type.instrument_id

        self._current_contract = None
        self._forward_contract = None
        self._carry_contract = None

    def on_start(self) -> None:
        pass

    def on_bar(self, bar: Bar) -> None:
        
        if bar.bar_type == self._current_bar_type or bar.bar_type == self._forward_bar_type:
            self._try_roll()

        if bar.bar_type == self._current_bar_type:
            self._send_continous_price()

    def _send_continous_price(self) -> None:
        
        current_bar = self.cache.bar(self._current_bar_type)
        forward_bar = self.cache.bar(self._forward_bar_type)
        carry_bar = self.cache.bar(self._carry_bar_type)

        continuous_price = ContinuousPrice(
            instrument_id=self._instrument_id,
            current_price=Price(current_bar.close, current_bar.close.precision),
            current_month=self._current_id,
            forward_price=Price(forward_bar.close, forward_bar.close.precision)
                if forward_bar is not None else None,
            forward_id=self._forward_id,
            carry_price=Price(carry_bar.close, carry_bar.close.precision)
                if carry_bar is not None else None,
            carry_month=self._carry_id,
            ts_event=current_bar.ts_event,
            ts_init=current_bar.ts_init,
        )
        if self._handler is not None:
            self.handler(continuous_price)

        self._msgbus.publish(topic=f"{self._bar_type}0", msg=continuous_price)

    def _try_roll(self) -> None:
        current_bar = self.cache.bar(self._current_bar_type)
        forward_bar = self.cache.bar(self._forward_bar_type)

        if current_bar is None or forward_bar is None:
            return  # next bar arrived before current or vice versa

        current_timestamp = unix_nanos_to_dt(current_bar.ts_event)
        forward_timestamp = unix_nanos_to_dt(forward_bar.ts_event)

        if current_timestamp >= self._expiry_date:
            # TODO: special handling
            raise ValueError("Contract has expired")
        
        valid_roll_date = self._chain.is_valid_roll_date(current_timestamp)
        if not valid_roll_date:
            return

        if current_timestamp != forward_timestamp:
            return  # a valid roll time is where both timestamps are equal

        self.unsubscribe_bars(self._current_bar_type)
        
        self._current_contract = self._chain.next_contract(self._current_contract)
        self._forward_contract = self._chain.forward_contract(self._current_contract)
        self._carry_contract = self._chain.carry_contract(self._current_contract)
        
        self.subscribe_bars(self._current_bar_type)
        self.subscribe_bars(self._forward_bar_type)
    
    @property
    def current_bar_type(self) -> BarType:
        """
        TODO: implement
        """

    @property
    def forward_bar_type(self) -> BarType:
        """
        TODO: implement
        """
        
    @property
    def carry_bar_type(self) -> BarType:
        """
        TODO: implement
        """
        

from collections import deque
from dataclasses import dataclass

import pandas as pd
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.model.currencies import GBP
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.events.position import PositionClosed
from nautilus_trader.model.events.position import PositionOpened
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments.futures_contract import FuturesContract

from nautilus_trader.continuous.config import ContractChainConfig
from nautilus_trader.continuous.contract_month import ContractMonth

class ContractChain(Actor):
    def __init__(
        self,
        config: ContractChainConfig,
    ):
        
        super().__init__()
        
        self.bar_type = config.bar_type
        self.rolls: pd.DataFrame = pd.DataFrame(columns=["timestamp", "to_month"])

        self._roll_offset = config.roll_config.roll_offset
        self._carry_offset = config.roll_config.carry_offset
        self._priced_cycle = config.roll_config.priced_cycle
        self._start_month = config.start_month
        self._hold_cycle = config.roll_config.hold_cycle
        self._approximate_expiry_offset = config.approximate_expiry_offset
        
        assert self._roll_offset <= 0
        assert self._carry_offset == 1 or self._carry_offset == -1
        assert self._start_month in self._hold_cycle

        self._raise_expired = config.raise_expired
        self._ignore_expiry_date = config.ignore_expiry_date
        self._instrument_id = self._bar_type.instrument_id
        
    def on_start(self) -> None:
        self._roll(to_month=self._start_month)

    def on_bar(self, bar: Bar) -> None:
        is_current = bar.bar_type == self.current_bar_type
        is_forward = bar.bar_type == self.forward_bar_type

        if is_current or is_forward:
            
            self._attempt_roll()
            self._publish()
    
    def _publish(self) -> None:
        current_bar = self.cache.bar(self.current_bar_type)
        forward_bar = self.cache.bar(self.forward_bar_type)
        carry_bar = self.cache.bar(self.carry_bar_type)
        
        self.msgbus.publish(
            topic=f"{self.bar_type}",
            msg=current_bar,
        )
        
        if forward_bar is not None:
            self.msgbus.publish(
                topic=f"{self.bar_type}+1",
                msg=forward_bar,
            )
            
        if carry_bar is not None:
            self.msgbus.publish(
                topic=f"{self.bar_type}c",
                msg=carry_bar,
            )
    
    def roll(self) -> None:
        """
        Roll to the next month in the chain.

        """
        to_month = self._hold_cycle.next_month(self.current_month)
        self._roll(to_month=to_month)
            
    def _attempt_roll(self) -> None:
        
        current_bar = self.cache.bar(self.current_bar_type)
        forward_bar = self.cache.bar(self.forward_bar_type)

        if current_bar is None or forward_bar is None:
            return

        current_timestamp = unix_nanos_to_dt(current_bar.ts_event)
        forward_timestamp = unix_nanos_to_dt(forward_bar.ts_event)
        
        if current_timestamp != forward_timestamp:
            return
        
        is_expired = current_timestamp >= self.expiry_date
        if is_expired and self._raise_expired:
            raise ValueError("ContractExpired")

        if self._ignore_expiry_date:
            in_roll_window = current_timestamp >= self.roll_date
        else:
            current_day = current_timestamp.floor("D")
            in_roll_window = (current_timestamp >= self.roll_date) and current_day <= self.expiry_day

        if not in_roll_window:
            return
        
        self.roll()
        self.rolls.loc[len(self.rolls)] = (current_timestamp, self.current_month)

    def _roll(self, to_month: ContractMonth) -> None:
        self._update_attributes(to_month=to_month)
        self._update_subscriptions()
        self._log.debug(f"Rolled {self.previous_contract.id} > {self.current_contract.id}")

    def _update_subscriptions(self) -> None:
        """
        Updating subscriptions after the roll
        """
        self._log.info("Updating subscriptions...")
        self.unsubscribe_bars(self.previous_bar_type)
        self.subscribe_bars(self.current_bar_type)
        self.subscribe_bars(self.forward_bar_type)

    def _update_attributes(self, to_month: ContractMonth) -> None:
        
        self.current_month: ContractMonth = to_month
        self.previous_month: ContractMonth = self._hold_cycle.previous_month(self.current_month)
        self.forward_month: ContractMonth = self._hold_cycle.next_month(self.current_month)
        if self._carry_offset == 1:
            self.carry_month: ContractMonth = self._priced_cycle.next_month(self.current_month)
        elif self._carry_offset == -1:
            self.carry_month: ContractMonth = self._priced_cycle.previous_month(self.current_month)
        
        self.current_bar_type = self._make_bar_type(self.current_month)
        self.previous_bar_type = self._make_bar_type(self.previous_month)
        self.forward_bar_type = self._make_bar_type(self.forward_month)
        self.carry_bar_type = self._make_bar_type(self.carry_bar_type)
        
        self.expiry_date: pd.Timestamp = self.current_month.timestamp_utc \
                                        + pd.Timedelta(days=self._approximate_expiry_offset)
                                        
        self.roll_date: pd.Timestamp = self.expiry_date + pd.Timedelta(days=self._roll_offset)
    
    def _make_bar_type(self, month: ContractMonth) -> BarType:
        return BarType(
            instrument_id=self._fmt_instrument_id(month),
            bar_spec=self.bar_type.spec,
            aggregation_source=self.bar_type.aggregation_source,
        )
        
    def _fmt_instrument_id(self, month: ContractMonth) -> InstrumentId:
        """
        Format the InstrumentId for contract given the ContractMonth.
        """
        symbol = self._instrument_id.symbol.value
        venue = self._instrument_id.venue.value
        return InstrumentId.from_str(
            f"{symbol}={month.year}{month.letter_month}.{venue}",
        )
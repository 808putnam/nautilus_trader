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

from pyfutures.continuous.config import ContractChainConfig
from pyfutures.continuous.contract_month import ContractMonth

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
        self._instrument_id = InstrumentId.from_str(str(config.roll_config.instrument_id))
        self._start_month = config.start_month
        self._hold_cycle = config.roll_config.hold_cycle
        
        assert self._roll_offset <= 0
        assert self._carry_offset == 1 or self._carry_offset == -1
        assert self._start_month in self._hold_cycle

        self._raise_expired = config.raise_expired
        self._ignore_expiry_date = config.ignore_expiry_date
        
    def on_start(self) -> None:
        self._roll(to_month=self._start_month)

    def on_bar(self, bar: Bar) -> None:
        is_current = bar.bar_type == self.current_bar_type
        is_forward = bar.bar_type == self.forward_bar_type

        if is_current or is_forward:
            self._attempt_roll()
        
            current_bar = self.cache.bar(self.current_bar_type)
            forward_bar = self.cache.bar(self.forward_bar_type)
            previous_bar = self.cache.bar(self.previous_bar_type)
            self.msgbus.publish(
                topic=f"{self.bar_type}",
                msg=current_bar,
            )
            
            if forward_bar is not None:
                self.msgbus.publish(
                    topic=f"{self.bar_type}+1",
                    msg=forward_bar,
                )
                
            if previous_bar is not None:
                self.msgbus.publish(
                    topic=f"{self.bar_type}-1",
                    msg=previous_bar,
                )
        
    def _attempt_roll(self) -> None:
        
        current_bar = self.cache.bar(self.current_bar_type)
        forward_bar = self.cache.bar(self.forward_bar_type)

        if current_bar is None or forward_bar is None:
            return

        current_timestamp = unix_nanos_to_dt(current_bar.ts_event)
        forward_timestamp = unix_nanos_to_dt(forward_bar.ts_event)
        
        if current_timestamp != forward_timestamp:
            return
        
        is_expired = current_timestamp >= (self.expiry_day + pd.Timedelta(days=1))
        if is_expired and self._raise_expired:
            raise ValueError("ContractExpired")

        if self._ignore_expiry_date:
            in_roll_window = current_timestamp >= self.roll_date
        else:
            current_day = current_timestamp.floor("D")
            in_roll_window = (current_timestamp >= self.roll_date) and (current_day <= self.expiry_day)

        if not in_roll_window:
            return
        
        self.roll()
        self.rolls.loc[len(self.rolls)] = (current_timestamp, self.current_month)

    def roll(self):
        to_month = self._hold_cycle.next_month(self.current_month)
        self._roll(to_month=to_month)

    def _roll(self, to_month: ContractMonth) -> None:
        self._log.debug(f"Rolling to month {to_month}...")
        self._update_attributes(to_month=to_month)
        self._update_subscriptions()
        self._log.debug(f"Rolled {self.previous_contract.id} > {self.current_contract.id}")

    def _update_subscriptions(self) -> None:
        """
        Updating subscriptions after the roll
        """
        self._log.debug("Updating subscriptions...")
        self.unsubscribe_bars(self.previous_bar_type)
        self.subscribe_bars(self.current_bar_type)
        self.subscribe_bars(self.forward_bar_type)

    def _update_attributes(self, to_month: ContractMonth) -> None:
        
        self.current_month: ContractMonth = to_month
        self.previous_month: ContractMonth = self._hold_cycle.previous_month(self.current_month)
        self.forward_month: ContractMonth = self._hold_cycle.next_month(self.current_month)
        
        current_id = self._fmt_instrument_id(self.current_month)
        self.current_contract: FuturesContract = self.cache(current_id)
        
        previous_id = self._fmt_instrument_id(self.current_month)
        self.previous_contract: FuturesContract = self._fetch_contract(previous_id)
        
        forward_id = self._fmt_instrument_id(self.current_month)
        self.forward_contract: FuturesContract = self._fetch_contract(forward_id)

        self.expiry_date: pd.Timestamp = unix_nanos_to_dt(self.current_contract.expiration_ns)
        self.expiry_day: pd.Timestamp = self.expiry_date.floor("D")
        self.roll_date: pd.Timestamp = self.expiry_date + pd.Timedelta(days=self._roll_offset)

        self.current_bar_type = BarType(
            instrument_id=self.current_contract.id,
            bar_spec=self.bar_type.spec,
            aggregation_source=self.bar_type.aggregation_source,
        )

        self.previous_bar_type = BarType(
            instrument_id=self.previous_contract.id,
            bar_spec=self.bar_type.spec,
            aggregation_source=self.bar_type.aggregation_source,
        )

        self.forward_bar_type = BarType(
            instrument_id=self.forward_contract.id,
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
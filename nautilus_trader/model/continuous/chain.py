import pandas as pd

from nautilus_trader.model.continuous.contract_month import ContractMonth
from nautilus_trader.model.continuous.cycle import RollCycle
from nautilus_trader.model.continuous.config import FuturesChainConfig


class FuturesChain:
    def __init__(
        self,
        config: FuturesChainConfig,
    ):
        self.hold_cycle = RollCycle(config.hold_cycle)
        self.priced_cycle = RollCycle(config.priced_cycle)
        self.roll_offset = config.roll_offset
        self.approximate_expiry_offset = config.approximate_expiry_offset
        self.carry_offset = config.carry_offset

        assert self.roll_offset <= 0
        assert self.approximate_expiry_offset >= 0
        assert self.carry_offset == 1 or self.carry_offset == -1

    def approximate_expiry_date(self, month: ContractMonth) -> pd.Timestamp:
        """
        Return the approximate expiry date of the month.
        """
        return month.timestamp + pd.Timedelta(days=self.approximate_expiry_offset)

    def roll_date(self, month: ContractMonth) -> pd.Timestamp:
        """
        Return the date the roll should occur at the month.
        """
        return self.approximate_expiry_date(month) + pd.Timedelta(days=self.roll_offset)

    def is_valid_roll_date(self, month: ContractMonth, timestamp: pd.Timestamp) -> bool:
        """
        Return the date the roll should occur at the month.
        """
        expiry_date = self.approximate_expiry_date(month)
        roll_date = self.roll_date(month)
        timestamp = month.timestamp
        in_window = timestamp >= roll_date and timestamp < expiry_date

        return in_window

    def current_month(self, timestamp: pd.Timestamp) -> ContractMonth:
        current = self.hold_cycle.current_month(timestamp)

        while True:
            roll_date = self.roll_date(current.timestamp)

            if roll_date > timestamp:
                break

            current = self.hold_cycle.next_month(current)

        return current

    def forward_month(self, month: ContractMonth) -> ContractMonth:
        return self.hold_cycle.next_month(month)

    def carry_month(self, month: ContractMonth) -> ContractMonth:
        if self.carry_offset == 1:
            return self.priced_cycle.next_month(month)
        elif self.carry_offset == -1:
            return self.priced_cycle.previous_month(month)

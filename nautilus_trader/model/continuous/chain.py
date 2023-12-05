
import pandas as pd

from nautilus_trader.model.continuous.contract_month import ContractMonth
from nautilus_trader.model.continuous.parameters import RollParameters
from nautilus_trader.model.instruments.futures_contract import FuturesContract

class FuturesChain:
    
    def __init__(
        self,
        parameters: RollParameters,
    ):
        
        super().__init__()
        
        self._parameters = parameters
        self._cycle = self._parameters.hold_cycle
    
    def calculate_roll_date(self, timestamp: pd.Timestamp) -> pd.Timestamp:
        """
        return the date the roll should occur at the current timestamp
        """
        expiry_date = timestamp + pd.Timedelta(days=self._parameters.expiry_offset)
        roll_date = expiry_date + pd.Timedelta(days=self._parameters.roll_offset)
        return roll_date
    
    def current_contract(self, timestamp: pd.Timestamp) -> FuturesContract:
        """
        TODO: implement: return the current contract that should be held at the current timestamp
        """
        
    def forward_contract(self, timestamp: pd.Timestamp) -> FuturesContract:
        """
        TODO: implement: return the forward contract at the current timestamp
        """
        
    def carry_contract(self, timestamp: pd.Timestamp) -> FuturesContract:
        """
        TODO: implement: return the carry contract at the current timestamp
        """
        
    def current_month(self, timestamp: pd.Timestamp) -> ContractMonth:
        
        month = self._current_month(timestamp)

        return month

    def forward_month(self, timestamp: pd.Timestamp) -> ContractMonth:
        
        month = self._current_month(timestamp)
        month = self._cycle.next_month(month)
        
        return month

    def carry_month(self, timestamp: pd.Timestamp) -> ContractMonth:
        
        month = self._current_month(timestamp)
        if self._parameters.carry_offset == 1:
            month = self._cycle.next_month(month)
        elif self._parameters.carry_offset == -1:
            month = self._cycle.previous_month(month)
        
        return month

    def _current_month(self, timestamp: pd.Timestamp) -> ContractMonth:
        
        current = self._cycle.current_month(timestamp)

        while True:
            
            roll_date = self.roll_date(current.timestamp)

            if roll_date > timestamp:
                break

            current = self._cycle.next_month(current)

        return current
    
    
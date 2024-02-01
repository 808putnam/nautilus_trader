import pandas as pd

from nautilus_trader.continuous.config import ContractChainConfig
from nautilus_trader.continuous.contract_month import ContractMonth
from nautilus_trader.model.instruments.futures_contract import FuturesContract
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.core.datetime import unix_nanos_to_dt

class ContractChain:
    def __init__(
        self,
        config: ContractChainConfig,
        instrument_provider: InstrumentProvider,
    ):
        
        self.hold_cycle = config.hold_cycle
        
        self._roll_offset = config.roll_offset
        self._instrument_id = InstrumentId.from_str(str(config.instrument_id))
        self._carry_offset = config.carry_offset
        self._priced_cycle = config.priced_cycle
        self._start_month = config.start_month
        
        self._instrument_provider = instrument_provider
        
        assert self._roll_offset <= 0
        assert self._carry_offset == 1 or self._carry_offset == -1
    
        self._current_month = None  # initialized on start
    
    @property
    def instrument_provider(self) -> InstrumentProvider:
        return self._instrument_provider
    
    @property
    def expiry_date(self) -> pd.Timestamp:
        return unix_nanos_to_dt(self.current_contract.expiration_ns)
    
    @property
    def roll_date(self) -> pd.Timestamp:
        # TODO: factor in the trading calendar
        return self.expiry_date + pd.Timedelta(days=self._roll_offset)
    
    @property
    def current_contract(self) -> FuturesContract:
        return self._fetch_contract(self._current_month)
    
    @property
    def forward_contract(self) -> FuturesContract:
        return self._fetch_contract(self.forward_month)
    
    @property
    def carry_contract(self) -> FuturesContract:
        return self._fetch_contract(self.carry_month)
    
    @property
    def current_month(self) -> ContractMonth:
        return self._current_month
    
    @property
    def forward_month(self) -> ContractMonth:
        return self.hold_cycle.next_month(self._current_month)
    
    @property
    def carry_month(self) -> ContractMonth:
        if self._carry_offset == 1:
            return self._priced_cycle.next_month(self._current_month)
        elif self._carry_offset == -1:
            return self._priced_cycle.previous_month(self._current_month)
        else:
            raise ValueError("carry offset must be 1 or -1")
        
    def on_start(self) -> None:
        
        month = self._start_month
        if month not in self.hold_cycle:
            month = self.hold_cycle.next_month(month)
            
        self._current_month = month
    
    def roll(self) -> None:
        self._current_month = self.hold_cycle.next_month(self._current_month)
        print(self._current_month)
    
    def _fetch_contract(self, month: ContractMonth) -> FuturesContract:
        if self._instrument_provider.get_contract(self._instrument_id, month) is None:
            self._instrument_provider.load_contract(instrument_id=self._instrument_id, month=month)
        return self._instrument_provider.get_contract(self._instrument_id, month)
        
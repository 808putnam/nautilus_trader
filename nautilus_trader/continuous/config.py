from typing import Annotated, Literal

from msgspec import Meta
from nautilus_trader.common.config import NautilusConfig
from nautilus_trader.common.config import NonNegativeInt
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId

from pyfutures.continuous.contract_month import ContractMonth
from pyfutures.continuous.cycle import RollCycle


# An integer constrained to values <= 0
NonPositiveInt = Annotated[int, Meta(le=0)]


class RollConfig(NautilusConfig, frozen=True):
    """
    Configuration for rolls

    Parameters
    ----------
    hold_cycle : RollCycle, The contract cycle string we want to hold
    priced_cycle : RollCycle, The contract cycle string of available prices
    roll_offset : NonPositiveInt, The day, relative to the expiry date, when we usually roll
    carry_offset : Literal[1, -1], The number of contracts forward or backwards defines carry in the priced roll cycle
    approximate_expiry_offset : NonNegativeInt, The offset, relative to the first of the contract month that the expiry date approximately occurs
    
    """

    instrument_id: InstrumentId
    hold_cycle: RollCycle
    priced_cycle: RollCycle
    roll_offset: NonPositiveInt
    approximate_expiry_offset: NonNegativeInt
    carry_offset: Literal[1, -1]
    skip_months: list[ContractMonth] | None = None


class ContractChainConfig(NautilusConfig, frozen=True):
    """
    Configuration for contract chain

    Parameters
    ----------
    bar_type : BarType
        The bar type of the bars that execute the rolls of the chain
    roll_config : RollConfig
        The configuration for the rolls
    raise_expired : bool, default True
        If an exception is raised when the contract fails to roll before the contract's expiry date
    ignore_expiry_date : bool, default False
        If the expiry_date of the current contract should be ignored when attempting to roll
    start_month : ContractMonth, optional
        The starting month to roll to when started
        
    """
    bar_type: BarType
    roll_config: RollConfig
    raise_expired: bool = True
    ignore_expiry_date: bool = False
    start_month: ContractMonth | None = None

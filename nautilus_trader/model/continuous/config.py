from dataclasses import dataclass

from nautilus_trader.config.common import NautilusConfig

@dataclass
class FuturesChainConfig(NautilusConfig, frozen=True):
    """
    Represents the config for a FutureChain
    
    hold_cycle: The contract cycle string we want to hold
    priced_cycle: The contract cycle string of available prices
    roll_offset: The day, relative to the expiry date, when we usually roll
    carry_offset: The number of contracts forward or backwards defines carry in the priced roll cycle
    expiry_offset: The offset, relative to the first of the contract month that the expiry date occurs
    """
    
    hold_cycle: str
    priced_cycle: str
    roll_offset: int = 0
    expiry_offset: int = 0
    carry_offset: int = -1
    
        
    @classmethod
    def from_dict(cls, value: dict):
        return cls(
            hold_cycle=value["hold_cycle"],
            priced_cycle=value["priced_cycle"],
            roll_offset=value["roll_offset"],
            expiry_offset=value["expiry_offset"],
            carry_offset=value["carry_offset"],
        )
        
    def to_dict(self) -> dict:
        return {
            "hold_cycle": self.hold_cycle,
            "priced_cycle": self.priced_cycle,
            "roll_offset": self.roll_offset,
            "expiry_offset": self.expiry_offset,
            "carry_offset": self.carry_offset,
        }
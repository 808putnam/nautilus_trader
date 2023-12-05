import pandas as pd

from nautilus_trader.model.continuous.parameters import RollParameters
from nautilus_trader.model.continuous.cycle import RollCycle

class TestRollParameters:
    def setup(self):

        self.params = RollParameters(
            hold_cycle="FGHJKMNQUVXZ",
            priced_cycle="FGHJKMNQUVXZ",
            roll_offset=-45,
            expiry_offset=14,
            carry_offset=1,
        )
    
    def test_to_dict(self):
        
        # Arrange, Act
        values = self.params.to_dict()
        
        # Assert
        assert values == {
            'hold_cycle': RollCycle("FGHJKMNQUVXZ"),
            'priced_cycle': RollCycle("FGHJKMNQUVXZ"),
            'roll_offset': -45,
            'expiry_offset': 14,
            'carry_offset': 1,
        }
        
    def test_from_dict(self):
        
        # Arrange
        value = {
            'hold_cycle': "FGHJKMNQUVXZ",
            'priced_cycle': "FGHJKMNQUVXZ",
            'roll_offset': -45,
            'expiry_offset': 14,
            'carry_offset': 1,
        }
        
        # Act
        parameters = RollParameters.from_dict(value)
        
        # Assert
        assert parameters.hold_cycle == RollCycle("FGHJKMNQUVXZ")
        assert parameters.priced_cycle == RollCycle("FGHJKMNQUVXZ")
        assert parameters.roll_offset == -45
        assert parameters.expiry_offset == 14
        assert parameters.carry_offset == 1
        

from nautilus_trader.test_kit.stubs.identifiers import TestIdStubs
from nautilus_trader.model.continuous.contract_month import ContractMonth
from nautilus_trader.model.continuous.price import ContinuousPrice
from nautilus_trader.model.objects import Price
import pickle

class TestContinuousPrice:
    
    def test_continuous_price_equality(self):
        
        # Arrange
        price1 = ContinuousPrice(
            instrument_id=TestIdStubs.gbpusd_id(),
            forward_price=Price.from_str("1.0"),
            forward_month=ContractMonth("Z21"),
            current_price=Price.from_str("1.1"),
            current_month=ContractMonth("X21"),
            carry_price=Price.from_str("1.0"),
            carry_month=ContractMonth("Z21"),
            ts_event=0,
            ts_init=0,
        )
        price2 = ContinuousPrice(
            instrument_id=TestIdStubs.gbpusd_id(),
            forward_price=Price.from_str("1.0"),
            forward_month=ContractMonth("Z21"),
            current_price=None,
            current_month=ContractMonth("X21"),
            carry_price=None,
            carry_month=ContractMonth("Z21"),
            ts_event=0,
            ts_init=0,
        )
        
        # Act, Assert
        assert price1 == price1
        assert price2 == price2
        
    def test_continuous_price_str_and_repr(self):
        
        # Arrange
        price = ContinuousPrice(
            instrument_id=TestIdStubs.gbpusd_id(),
            current_price=Price.from_str("1.1"),
            current_month=ContractMonth("X21"),
            forward_price=Price.from_str("1.0"),
            forward_month=ContractMonth("Z21"),
            carry_price=Price.from_str("1.0"),
            carry_month=ContractMonth("Z21"),
            ts_event=0,
            ts_init=0,
        )
        
        # Act, Assert
        assert str(price) == "ContinuousPrice(instrument_id=GBP/USD.SIM, current_price=1.1, current_month=X21, forward_price=1.0, forward_month=Z21, carry_price=1.0, carry_month=Z21, ts_event=0, ts_init=0)"
        assert repr(price) == "ContinuousPrice(instrument_id=GBP/USD.SIM, current_price=1.1, current_month=X21, forward_price=1.0, forward_month=Z21, carry_price=1.0, carry_month=Z21, ts_event=0, ts_init=0)"
        
    def test_to_dict(self):
        
        # Arrange
        price = ContinuousPrice(
            instrument_id=TestIdStubs.gbpusd_id(),
            current_price=Price.from_str("1.1"),
            current_month=ContractMonth("X21"),
            forward_price=Price.from_str("1.0"),
            forward_month=ContractMonth("Z21"),
            carry_price=Price.from_str("1.0"),
            carry_month=ContractMonth("Z21"),
            ts_event=0,
            ts_init=0,
        )
        
        # Act
        values = ContinuousPrice.to_dict(price)
        
        # Assert
        assert values == {
            'instrument_id': 'GBP/USD.SIM',
            'current_price': '1.1',
            'current_month': 'X21',
            'forward_price': '1.0',
            'forward_month': 'Z21',
            'carry_price': '1.0',
            'carry_month': 'Z21',
            'ts_event': 0,
            'ts_init': 0
        }
        
    def test_from_dict_returns_expected_price(self):
        
        # Arrange
        price = ContinuousPrice(
            instrument_id=TestIdStubs.gbpusd_id(),
            current_price=Price.from_str("1.1"),
            current_month=ContractMonth("X21"),
            forward_price=Price.from_str("1.0"),
            forward_month=ContractMonth("Z21"),
            carry_price=Price.from_str("1.0"),
            carry_month=ContractMonth("Z21"),
            ts_event=0,
            ts_init=0,
        )

        # Act
        result = ContinuousPrice.from_dict(ContinuousPrice.to_dict(price))

        # Assert
        assert result == price
        
    def test_pickle_bar(self):
        # Arrange
        price = ContinuousPrice(
            instrument_id=TestIdStubs.gbpusd_id(),
            current_price=Price.from_str("1.1"),
            current_month=ContractMonth("X21"),
            forward_price=Price.from_str("1.0"),
            forward_month=ContractMonth("Z21"),
            carry_price=Price.from_str("1.0"),
            carry_month=ContractMonth("Z21"),
            ts_event=0,
            ts_init=0,
        )

        # Act
        pickled = pickle.dumps(price)
        unpickled = pickle.loads(pickled)  # noqa S301 (pickle is safe here)

        # Assert
        assert unpickled == price

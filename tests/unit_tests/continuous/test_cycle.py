import pickle

from pyfutures.continuous.contract_month import ContractMonth
from pyfutures.continuous.cycle import RollCycle
from pyfutures.continuous.cycle_range import RangedRollCycle
from pyfutures.continuous.cycle_range import RollCycleRange


class TestRollCycle:
    def test_cycle_previous_month_returns_expected(self):
        # Arrange
        cycle = RollCycle("HMUX")

        assert cycle.previous_month(ContractMonth("2021Z")) == ContractMonth("2021X")
        assert cycle.previous_month(ContractMonth("2021F")) == ContractMonth("2020X")
        assert cycle.previous_month(ContractMonth("2021V")) == ContractMonth("2021U")

    def test_cycle_next_month_returns_expected(self):
        # Arrange
        cycle = RollCycle("HMUX")

        # Act, Assert
        assert cycle.next_month(ContractMonth("2022V")) == ContractMonth("2022X")
        assert cycle.next_month(ContractMonth("2021Z")) == ContractMonth("2022H")
        assert cycle.next_month(ContractMonth("2021F")) == ContractMonth("2021H")

    def test_cycle_contains(self):
        # Arrange
        cycle = RollCycle("HMUX")

        # Act, Assert
        assert ContractMonth("2020X") in cycle

    def test_cycle_equality(self):
        # Arrange
        cycle = RollCycle("HMUX")

        # Act, Assert
        assert cycle == cycle

    def test_cycle_str_len_repr(self):
        # Arrange
        cycle = RollCycle("HMUX")

        # Act, Assert
        assert len(cycle) == 4
        assert str(cycle) == "HMUX"
        assert repr(cycle) == "RollCycle(HMUX)"

    def test_cycle_next_month_skips_specified_months(self):
        # Arrange
        cycle = RollCycle("HMUX", skip_months=["2022M", "2022U"])

        # Act, Assert
        assert cycle.next_month(ContractMonth("2022H")) == ContractMonth("2022X")
        assert cycle.next_month(ContractMonth("2022X")) == ContractMonth("2023H")

    def test_cycle_previous_month_skips_specified_months(self):
        # Arrange
        cycle = RollCycle("HMUX", skip_months=["2022M", "2022U"])

        # Act, Assert
        assert cycle.previous_month(ContractMonth("2022X")) == ContractMonth("2022H")
        assert cycle.previous_month(ContractMonth("2022H")) == ContractMonth("2021X")

    def test_ranged_cycle_next_month_returns_expected(self):
        # Arrange
        ranges = [
            RollCycleRange(
                start_month=None,
                end_month=ContractMonth("2014X"),
                cycle=RollCycle("X"),
            ),
            RollCycleRange(
                start_month=ContractMonth("2015Z"),
                end_month=None,
                cycle=RollCycle("Z"),
            ),
        ]
        cycle = RangedRollCycle(ranges=ranges)

        # Act, Assert

        assert cycle.next_month(ContractMonth("2013X")) == ContractMonth("2014X")  # in 1st range
        assert cycle.next_month(ContractMonth("2014X")) == ContractMonth("2015Z")  # 1st range end
        assert cycle.next_month(ContractMonth("2014Z")) == ContractMonth("2015Z")  # in between
        assert cycle.next_month(ContractMonth("2015F")) == ContractMonth("2015Z")  # in between
        assert cycle.next_month(ContractMonth("2015Z")) == ContractMonth("2016Z")  # 2nd range start
        assert cycle.next_month(ContractMonth("2016Z")) == ContractMonth("2017Z")  # in 2nd range

    def test_ranged_cycle_previous_month_returns_expected(self):
        # Arrange
        ranges = [
            RollCycleRange(
                start_month=None,
                end_month=ContractMonth("2014X"),
                cycle=RollCycle("X"),
            ),
            RollCycleRange(
                start_month=ContractMonth("2015Z"),
                end_month=None,
                cycle=RollCycle("Z"),
            ),
        ]
        cycle = RangedRollCycle(ranges=ranges)

        # Act, Assert

        # in 1st range
        assert cycle.previous_month(ContractMonth("2013X")) == ContractMonth("2014X")

        # 1st range end
        assert cycle.previous_month(ContractMonth("2014X")) == ContractMonth("2013X")

        # 2nd range start
        assert cycle.previous_month(ContractMonth("2015Z")) == ContractMonth("2014X")

        # in 2nd range
        assert cycle.previous_month(ContractMonth("2016Z")) == ContractMonth("2015Z")

        # in 2nd range
        assert cycle.previous_month(ContractMonth("2017F")) == ContractMonth("2016Z")

        # in between
        assert cycle.previous_month(ContractMonth("2015X")) == ContractMonth("2014X")

    def test_ranged_roll_cycle_from_str(self):
        value = "2014X=X,2015Z=Z"

        cycle = RangedRollCycle.from_str(value)

        assert cycle.ranges == [
            RollCycleRange(
                start_month=None,
                end_month=ContractMonth("2014X"),
                cycle=RollCycle("X"),
            ),
            RollCycleRange(
                start_month=ContractMonth("2015Z"),
                end_month=None,
                cycle=RollCycle("Z"),
            ),
        ]

    def test_cycle_pickle(self):
        cycle = RollCycle("HMUZ")
        pickled = pickle.dumps(cycle)
        unpickled = pickle.loads(pickled)  # noqa S301 (pickle is safe here)

        # Assert
        assert unpickled == cycle

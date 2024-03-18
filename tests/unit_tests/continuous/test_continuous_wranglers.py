import pytest
import pandas as pd
from pathlib import Path
from nautilus_trader.model.data import capsule_to_list
from nautilus_trader.core.nautilus_pyo3 import NautilusDataType
from nautilus_trader.core.nautilus_pyo3 import DataBackendSession
from nautilus_trader import PACKAGE_ROOT
from nautilus_trader.continuous.wranglers import ContinuousBarWrangler
from nautilus_trader.continuous.config import ContractChainConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.continuous.cycle import RollCycle
from nautilus_trader.continuous.chain import ContractChain
from nautilus_trader.continuous.chain import ContractExpired
from nautilus_trader.continuous.config import RollConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.continuous.contract_month import ContractMonth
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos

class TestContinuousWrangler:
    
    def setup_method(self):
        
        self.roll_config = RollConfig(
            hold_cycle=RollCycle("HNUZ"),
            priced_cycle=RollCycle("FHJMNUVZ"),
            roll_offset=-30,
            approximate_expiry_offset=27,
            carry_offset=1,
        )
        
        self.chain_config = ContractChainConfig(
            bar_type=BarType.from_str("HG.SIM-1-DAY-MID-EXTERNAL"),
            roll_config=self.roll_config,
            start_month=ContractMonth("2021H"),
            raise_expired=True,
            ignore_expiry_date=False,
        )
        
    def test_wrangler_outputs_expected(self):
        
        wrangler = ContinuousBarWrangler(
            config=self.chain_config,
            end_month=ContractMonth("2021U"),
        )
        
        bars = self._read_bars()
        
        streams = wrangler.process(bars)
        assert len(streams["0"]) == 1323
        assert len(streams["+1"]) == 1240
        assert len(streams["c"]) == 548
        
        current_months = {
            ContractMonth(b.bar_type.instrument_id.symbol.value.split("=")[-1])
            for b in streams["0"]
        }
        forward_months = {
            ContractMonth(b.bar_type.instrument_id.symbol.value.split("=")[-1])
            for b in streams["+1"]
        }
        carry_months = {
            ContractMonth(b.bar_type.instrument_id.symbol.value.split("=")[-1])
            for b in streams["c"]
        }
        
        assert all(m in self.roll_config.hold_cycle for m in current_months)
        assert all(m in self.roll_config.hold_cycle for m in forward_months)
        assert all(m in self.roll_config.priced_cycle for m in carry_months)
        
    def test_wrangler_stops_at_end_month(self):
        
        wrangler = ContinuousBarWrangler(
            config=self.chain_config,
            end_month=ContractMonth("2021U"),
        )
        
        bars = self._read_bars()
        streams = wrangler.process(bars)
        assert streams["0"][-1].bar_type.instrument_id.symbol.value.endswith("2021N")
        assert streams["0"][-2].bar_type.instrument_id.symbol.value.endswith("2021H")
    
    def test_wrangler_roll_failure_no_overlap_raises(self):
        
        # expiry_date: 2021-03-28 00:00:00+00:00
        data = [
            ("HG=2021H.SIM", "2021-03-25"),
            ("HG=2021H.SIM", "2021-03-26"),
            ("HG=2021H.SIM", "2021-03-27"),
            ("HG=2021H.SIM", "2021-03-29"),
            ("HG=2021N.SIM", "2021-03-30"),
        ]
        
        bars = self._create_bars(data)
        
        wrangler = ContinuousBarWrangler(
            config=self.chain_config,
            end_month=ContractMonth("2021N"),
        )
        
        wrangler.validate(bars)
        
        # with pytest.raises(ContractExpired):
        #     wrangler.process(bars)
        
    def test_wrangler_roll_failure_current_start_after_expiry_date_raises(self):
        # test case of a roll failure where the first bar of the current contract is after the expiry date
        # expiry_date: 2021-03-28 00:00:00+00:00
        data = [
            ("HG=2021H.SIM", "2021-03-30"),
            ("HG=2021H.SIM", "2021-03-31"),
        ]
        
        bars = self._create_bars(data)
        
        wrangler = ContinuousBarWrangler(
            config=self.chain_config,
            end_month=ContractMonth("2021U"),
        )
        with pytest.raises(ContractExpired):
            wrangler.process(bars)
            
    def test_wrangler_roll_failure_forward_start_after_expiry_date_raises(self):
        # test case of a roll failure where the first bar of the forward contract is after the expiry date
        # expiry_date: 2021-03-28 00:00:00+00:00
        data = [
            ("HG=2021N.SIM", "2021-03-30"),
            ("HG=2021N.SIM", "2021-03-31"),
        ]
        
        bars = self._create_bars(data)
        
        wrangler = ContinuousBarWrangler(
            config=self.chain_config,
            end_month=ContractMonth("2021U"),
        )
        with pytest.raises(ContractExpired):
            wrangler.process(bars)
    
    def test_wrangler_roll_failure_last_current_received(self):
        # test case of a roll failure where the last bar of the current contract is received and the contract has failed to roll
        # expiry_date: 2021-03-28 00:00:00+00:00
        data = [
            ("HG=2021H.SIM", "2021-03-23"),
            ("HG=2021N.SIM", "2021-03-24"),
            ("HG=2021H.SIM", "2021-03-25"),
            ("HG=2021N.SIM", "2021-03-26"),
            ("HG=2021N.SIM", "2021-03-27"),
            ("HG=2021N.SIM", "2021-03-28"),
            ("HG=2021N.SIM", "2021-03-29"),
        ]
        
        bars = self._create_bars(data)
        
        for bar in bars:
            print(unix_nanos_to_dt(bar.ts_init))
        
        wrangler = ContinuousBarWrangler(
            config=self.chain_config,
            end_month=ContractMonth("2021U"),
        )
        with pytest.raises(ContractExpired):
            wrangler.process(bars)
        
    def test_wrangler_roll_failure_forward_end_before_roll_date(self):
        
        # test case of a roll failure where the first bar of the current contract is after the expiry date
        # expiry_date: 2021-03-28 00:00:00+00:00
        
        data = [
            ("HG=2021H.SIM", "2021-03-30"),
            ("HG=2021H.SIM", "2021-03-31"),
        ]
        
        bars = self._create_bars(data)
        
        wrangler = ContinuousBarWrangler(
            config=self.chain_config,
            end_month=ContractMonth("2021N"),
        )
        with pytest.raises(ContractExpired):
            wrangler.process(bars)
            
    def _create_bars_no_overlap(self) -> list[Bar]:
        
        test_data_dir = Path(PACKAGE_ROOT) / "tests/unit_tests/continuous/data"
        paths = list(test_data_dir.glob("HG=*.SIM-1-DAY-MID-EXTERNAL*no_overalp.parquet"))
        
        session = DataBackendSession()
        for i, path in enumerate(paths):
            assert path.exists()
            session.add_file(NautilusDataType.Bar, f"data{i}", str(path))

        bars = []
        for chunk in session.to_query_result():
            chunk = capsule_to_list(chunk)
            bars.extend(chunk)
        return bars
    
    def _read_bars(self) -> list[Bar]:
        
        test_data_dir = Path(PACKAGE_ROOT) / "tests/unit_tests/continuous/data"
        paths = list(test_data_dir.glob("HG=*.SIM-1-DAY-MID-EXTERNAL.parquet"))
        session = DataBackendSession()
        for i, path in enumerate(paths):
            assert path.exists()
            session.add_file(NautilusDataType.Bar, f"data{i}", str(path))

        bars = []
        for chunk in session.to_query_result():
            chunk = capsule_to_list(chunk)
            bars.extend(chunk)
        return bars
    
    def _create_bars(self, data: list[tuple]) -> list[Bar]:
        return [
            Bar(
                bar_type=BarType.from_str(f"{row[0]}-1-DAY-MID-EXTERNAL"),
                open=Price.from_str("1.1"),
                high=Price.from_str("1.2"),
                low=Price.from_str("1.0"),
                close=Price.from_str("1.1"),
                volume=Quantity.from_int(1),
                ts_event=dt_to_unix_nanos(pd.Timestamp(row[1], tz="UTC")),
                ts_init=dt_to_unix_nanos(pd.Timestamp(row[1], tz="UTC")),
            )
            for row in data
        ]
if __name__ == "__main__":
    path1 = Path("/Users/g1/BU/projects/continuous/tests/unit_tests/continuous/data/HG=2021H.SIM-1-DAY-MID-EXTERNAL.parquet")
    df1 = pd.read_parquet(path1)
    df1["timestamp"] = df1.ts_init.apply(unix_nanos_to_dt)
    df1 = df1[df1.timestamp < pd.Timestamp("2021-03-28 00:00:00+00:00")]
    
    path2 = Path("/Users/g1/BU/projects/continuous/tests/unit_tests/continuous/data/HG=2021M.SIM-1-DAY-MID-EXTERNAL.parquet")
    df2 = pd.read_parquet(path2)
    df2["timestamp"] = df2.ts_init.apply(unix_nanos_to_dt)
    df2 = df2[df2.timestamp > pd.Timestamp("2021-03-28 00:00:00+00:00")]
    
    path1 = path1.with_stem(path1.stem + "no_overlap")
    path2 = path1.with_stem(path2.stem + "no_overlap")
    
    # del df1.timestamp
    # del df2.timestamp
    
    df1.to_parquet(path1, index=False)
    df2.to_parquet(path2, index=False)
    
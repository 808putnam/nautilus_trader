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
from nautilus_trader.continuous.config import RollConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.continuous.contract_month import ContractMonth

class TestContinuousWrangler:
    
    def setup_method(self):
        
        config = ContractChainConfig(
            bar_type=BarType.from_str("MES.SIM-1-DAY-MID-EXTERNAL"),
            roll_config=RollConfig(
                hold_cycle=RollCycle("HMUZ"),
                priced_cycle=RollCycle("FGHJKMNQUVXZ"),
                roll_offset=-5,
                approximate_expiry_offset=14,
                carry_offset=1,
            ),
            start_month=ContractMonth("2021H"),
        )
        
        self.wrangler = ContinuousBarWrangler(
            config=config,
            end_month=ContractMonth("2021Z"),
        )
        
        
    def test_wrangler_outputs_expected(self):
        
        bars = self._create_bars()
        self.wrangler.process(bars)
        
    def test_wrangler_stops_at_end_month(self):
        pass
    
    def _create_bars(self) -> list[Bar]:
        folder = Path(PACKAGE_ROOT) / "tests/unit_tests/continuous/data"
        session = DataBackendSession()

        filenames = [
            "MES=MES=FUT=2021H.SIM-1-DAY-MID-EXTERNAL-0.parquet",
            "MES=MES=FUT=2021M.SIM-1-DAY-MID-EXTERNAL-0.parquet",
            "MES=MES=FUT=2021U.SIM-1-DAY-MID-EXTERNAL-0.parquet",
            "MES=MES=FUT=2021Z.SIM-1-DAY-MID-EXTERNAL-0.parquet",
        ]

        for i, filename in enumerate(filenames):
            path = folder / filename
            assert path.exists()
            session.add_file(NautilusDataType.Bar, f"data{i}", str(path))

        bars = []
        for chunk in session.to_query_result():
            chunk = capsule_to_list(chunk)
            bars.extend(chunk)
        return bars
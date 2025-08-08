from pathlib import Path

import pytest

from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_onshore_default_system_aep(subtests):
    input_path = str(Path(__file__).parent.absolute() / "inputs" / "h2i_ard.yaml")

    # Create a GreenHEART model
    h2i_model = H2IntegrateModel(input_path)

    # Run the model
    h2i_model.run()

    # Post-process the results
    h2i_model.post_process()

    with subtests.test("AEP_farm"):
        assert h2i_model.prob.get_val("AEP_farm", units="GW*h")[0] == pytest.approx(340.823649)
    with subtests.test("tcc.tcc"):
        assert h2i_model.prob.get_val("tcc.tcc", units="MUSD")[0] == pytest.approx(109.525)
    with subtests.test("BOS capex (landbosse.bos_capex)"):
        assert h2i_model.prob.get_val("bos_capex_kW", units="MUSD/GW")[0] == pytest.approx(
            391.511636
        )
    with subtests.test("BOS capex (landbosse.total_capex)"):
        assert h2i_model.prob.get_val("total_capex", units="MUSD")[0] == pytest.approx(
            41.57835529481917
        )
    with subtests.test("opex.opex"):
        assert h2i_model.prob.get_val("opex.opex", units="MUSD/yr")[0] == pytest.approx(3.707)
    with subtests.test("financese.lcoe"):
        assert h2i_model.prob.get_val("financese.lcoe", units="USD/MW/h")[0] == pytest.approx(
            44.127664498311255
        )

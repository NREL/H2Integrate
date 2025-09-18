import numpy as np
import openmdao.api as om
from pytest import approx

from h2integrate.transporters.electricity_combiner import CombinerPerformanceModel


rng = np.random.default_rng(seed=0)


def test_power_combiner_performance():
    prob = om.Problem()
    comp = CombinerPerformanceModel()
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("electricity_in1", val=np.zeros(8760), units="kW")
    ivc.add_output("electricity_in2", val=np.zeros(8760), units="kW")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    electricity_input1 = rng.random(8760)
    electricity_input2 = rng.random(8760)
    electricity_output = electricity_input1 + electricity_input2

    prob.set_val("electricity_in1", electricity_input1, units="kW")
    prob.set_val("electricity_in2", electricity_input2, units="kW")
    prob.run_model()

    assert prob.get_val("electricity_out", units="kW") == approx(electricity_output, rel=1e-5)

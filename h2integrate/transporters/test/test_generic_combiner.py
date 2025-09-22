import numpy as np
import openmdao.api as om
from pytest import approx, fixture

from h2integrate.transporters.generic_combiner import GenericCombinerPerformanceModel


rng = np.random.default_rng(seed=0)


@fixture
def plant_config():
    plant_dict = {"plant": {"simulation": {"n_timesteps": 8760, "dt": 3600}}}
    return plant_dict


@fixture
def combiner_tech_config_electricity():
    elec_combiner_dict = {
        "model_inputs": {
            "performance_parameters": {"commodity": "electricity", "commodity_units": "kW"}
        }
    }
    return elec_combiner_dict


@fixture
def combiner_tech_config_hydrogen():
    h2_combiner_dict = {
        "model_inputs": {
            "performance_parameters": {"commodity": "hydrogen", "commodity_units": "kg"}
        }
    }
    return h2_combiner_dict


def test_generic_combiner_performance_power(plant_config, combiner_tech_config_electricity):
    prob = om.Problem()
    comp = GenericCombinerPerformanceModel(
        plant_config=plant_config, tech_config=combiner_tech_config_electricity, driver_config={}
    )
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


def test_generic_combiner_performance_hydrogen(plant_config, combiner_tech_config_hydrogen):
    prob = om.Problem()
    comp = GenericCombinerPerformanceModel(
        plant_config=plant_config, tech_config=combiner_tech_config_hydrogen, driver_config={}
    )
    prob.model.add_subsystem("comp", comp, promotes=["*"])
    ivc = om.IndepVarComp()
    ivc.add_output("hydrogen_in1", val=np.zeros(8760), units="kg")
    ivc.add_output("hydrogen_in2", val=np.zeros(8760), units="kg")
    prob.model.add_subsystem("ivc", ivc, promotes=["*"])

    prob.setup()

    hydrogen_input1 = rng.random(8760)
    hydrogen_input2 = rng.random(8760)
    hydrogen_output = hydrogen_input1 + hydrogen_input2

    prob.set_val("hydrogen_in1", hydrogen_input1, units="kg")
    prob.set_val("hydrogen_in2", hydrogen_input2, units="kg")
    prob.run_model()

    assert prob.get_val("hydrogen_out", units="kg") == approx(hydrogen_output, rel=1e-5)

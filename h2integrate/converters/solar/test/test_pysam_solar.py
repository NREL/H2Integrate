import pytest
import openmdao.api as om

from h2integrate import EXAMPLE_DIR
from h2integrate.converters.solar.solar_pysam import PYSAMSolarPlantPerformanceModel


def test_pysam_solar_performance(subtests):
    pv_design_dict = {
        "pv_capacity_kWdc": 250000.0,
        "dc_ac_ratio": 1.23,
        "array_type": 2,
        "azimuth": 180,
        "bifaciality": 0.65,
    }

    pv_resource_dir = EXAMPLE_DIR / "11_hybrid_energy_plant" / "tech_inputs" / "weather" / "solar"
    pv_filename = "30.6617_-101.7096_psmv3_60_2013.csv"
    pv_resource_dict = {
        "latitude": 30.6617,
        "longitude": -101.7096,
        "year": 2013,
        "solar_resource_filepath": pv_resource_dir / pv_filename,
    }

    tech_config_dict = {
        "model_inputs": {
            "performance_parameters": pv_design_dict,
        }
    }

    prob = om.Problem()
    comp = PYSAMSolarPlantPerformanceModel(
        plant_config={"site": pv_resource_dict},
        tech_config=tech_config_dict,
    )
    prob.model.add_subsystem("pv_perf", comp)
    prob.setup()
    prob.run_model()

    aep = prob.get_val("pv_perf.annual_energy")[0]
    capacity_kWac = prob.get_val("pv_perf.capacity_kWac")[0]
    capacity_kWdc = prob.get_val("pv_perf.capacity_kWdc")[0]

    with subtests.test("AEP"):
        assert pytest.approx(aep, rel=1e-6) == 527345996

    with subtests.test("Capacity in kW-AC"):
        assert (
            pytest.approx(capacity_kWac, rel=1e-6) == capacity_kWdc / pv_design_dict["dc_ac_ratio"]
        )

    with subtests.test("Capacity in kW-DC"):
        assert pytest.approx(capacity_kWdc, rel=1e-6) == pv_design_dict["pv_capacity_kWdc"]

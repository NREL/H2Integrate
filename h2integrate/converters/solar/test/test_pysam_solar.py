import pytest
import openmdao.api as om
from pytest import fixture

from h2integrate import EXAMPLE_DIR
from h2integrate.converters.solar.solar_pysam import PYSAMSolarPlantPerformanceModel


@fixture
def solar_resource_dict():
    pv_resource_dir = EXAMPLE_DIR / "11_hybrid_energy_plant" / "tech_inputs" / "weather" / "solar"
    pv_filename = "30.6617_-101.7096_psmv3_60_2013.csv"
    pv_resource_dict = {
        "latitude": 30.6617,
        "longitude": -101.7096,
        "year": 2013,
        "solar_resource_filepath": pv_resource_dir / pv_filename,
    }
    return pv_resource_dict


@fixture
def basic_pysam_options():
    pysam_options = {
        "SystemDesign": {
            "array_type": 2,
            "azimuth": 180,
            "bifaciality": 0.65,
            "inv_eff": 96.0,
            "losses": 14.0757,
            "module_type": 0,
            "rotlim": 45.0,
            "gcr": 0.3,
        },
    }
    return pysam_options


def test_pvwatts_singleowner_notilt(basic_pysam_options, solar_resource_dict, subtests):
    """Test `PYSAMSolarPlantPerformanceModel` with a basic input scenario:

    - `pysam_options` is provided
    - `create_model_from` is set to 'default'
    - `config_name` is 'PVWattsSingleOwner', this is used to create the starting system model
        because `create_model_from` is default.
    - `tilt_angle_func` is "none" and tilt is provided (in two separate places) as zero.
    """

    basic_pysam_options["SystemDesign"].update({"tilt": 0.0})
    pv_design_dict = {
        "pv_capacity_kWdc": 250000.0,
        "dc_ac_ratio": 1.23,
        "create_model_from": "default",
        "config_name": "PVWattsSingleOwner",
        "tilt": 0.0,
        "tilt_angle_func": "none",  # "lat-func",
        "pysam_options": basic_pysam_options,
    }

    tech_config_dict = {
        "model_inputs": {
            "performance_parameters": pv_design_dict,
        }
    }

    plant_info = {
        "simulation": {
            "n_timesteps": 8760,
            "dt": 3600,
        }
    }

    prob = om.Problem()
    comp = PYSAMSolarPlantPerformanceModel(
        plant_config={"site": solar_resource_dict, "plant": plant_info},
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


def test_pvwatts_singleowner_withtilt(basic_pysam_options, solar_resource_dict, subtests):
    """Test PYSAMSolarPlantPerformanceModel with tilt angle calculated using 'lat-func' option.
    The AEP of this test should be higher than the AEP in `test_pvwatts_singleowner_notilt`.
    """

    pv_design_dict = {
        "pv_capacity_kWdc": 250000.0,
        "dc_ac_ratio": 1.23,
        "create_model_from": "default",
        "config_name": "PVWattsSingleOwner",
        "tilt_angle_func": "lat-func",
        "pysam_options": basic_pysam_options,
    }

    tech_config_dict = {
        "model_inputs": {
            "performance_parameters": pv_design_dict,
        }
    }

    plant_info = {
        "simulation": {
            "n_timesteps": 8760,
            "dt": 3600,
        }
    }

    prob = om.Problem()
    comp = PYSAMSolarPlantPerformanceModel(
        plant_config={"site": solar_resource_dict, "plant": plant_info},
        tech_config=tech_config_dict,
    )
    prob.model.add_subsystem("pv_perf", comp)
    prob.setup()
    prob.run_model()

    aep = prob.get_val("pv_perf.annual_energy")[0]
    capacity_kWac = prob.get_val("pv_perf.capacity_kWac")[0]
    capacity_kWdc = prob.get_val("pv_perf.capacity_kWdc")[0]

    with subtests.test("AEP"):
        assert pytest.approx(aep, rel=1e-6) == 556441491

    with subtests.test("Capacity in kW-AC"):
        assert (
            pytest.approx(capacity_kWac, rel=1e-6) == capacity_kWdc / pv_design_dict["dc_ac_ratio"]
        )

    with subtests.test("Capacity in kW-DC"):
        assert pytest.approx(capacity_kWdc, rel=1e-6) == pv_design_dict["pv_capacity_kWdc"]

import numpy as np
import pytest
import openmdao.api as om
from pytest import approx, fixture

from h2integrate.storage.hydrogen.mch_storage import MCHTOLStorageCostModel
from h2integrate.simulation.technologies.hydrogen.h2_storage.mch.mch_cost import MCHStorage


@fixture
def tol_mch_storage():
    # Test values are based on Supplementary Table 3 of
    # https://doi.org/10.1038/s41467-024-53189-2
    Dc_tpd = 304
    Hc_tpd = 304
    As_tpy = 35000
    Ms_tpy = 16200
    in_dict = {
        "max_H2_production_kg_pr_hr": (Hc_tpd + Dc_tpd) * 1e3 / 24,
        "hydrogen_storage_capacity_kg": Ms_tpy * 1e3,
        "hydrogen_demand_kg_pr_hr": Dc_tpd * 1e3 / 24,
        "annual_hydrogen_stored_kg_pr_yr": As_tpy * 1e3,
    }

    mch_storage = MCHStorage(**in_dict)

    return mch_storage


def test_init():
    # Test values are based on Supplementary Table 3 of
    # https://doi.org/10.1038/s41467-024-53189-2
    Dc_tpd = 304
    Hc_tpd = 304
    As_tpy = 35000
    Ms_tpy = 16200
    in_dict = {
        "max_H2_production_kg_pr_hr": (Hc_tpd + Dc_tpd) * 1e3 / 24,
        "hydrogen_storage_capacity_kg": Ms_tpy * 1e3,
        "hydrogen_demand_kg_pr_hr": Dc_tpd * 1e3 / 24,
        "annual_hydrogen_stored_kg_pr_yr": As_tpy * 1e3,
    }
    mch_storage = MCHStorage(**in_dict)

    assert mch_storage.cost_year is not None
    assert mch_storage.occ_coeff is not None


def test_sizing(tol_mch_storage, subtests):
    # Test values are based on Supplementary Table 3 of
    # https://doi.org/10.1038/s41467-024-53189-2
    Dc_tpd = 304
    Hc_tpd = 304
    As_tpy = 35000
    Ms_tpy = 16200
    with subtests.test("Dehydrogenation capacity"):
        assert tol_mch_storage.Dc == approx(Dc_tpd, rel=1e-6)
    with subtests.test("Hydrogenation capacity"):
        assert tol_mch_storage.Hc == approx(Hc_tpd, rel=1e-6)
    with subtests.test("Annual storage capacity"):
        assert tol_mch_storage.As == approx(As_tpy, rel=1e-6)
    with subtests.test("Maximum storage capacity"):
        assert tol_mch_storage.Ms == approx(Ms_tpy, rel=1e-6)


def test_cost_calculation_methods(tol_mch_storage, subtests):
    # Supplementary Table 3
    toc_actual = 639375591
    foc_actual = 10239180
    voc_actual = 17332229

    max_cost_error_rel = 0.06
    capex = tol_mch_storage.calc_cost_value(*tol_mch_storage.occ_coeff)
    fixed_om = tol_mch_storage.calc_cost_value(*tol_mch_storage.foc_coeff)
    var_om = tol_mch_storage.calc_cost_value(*tol_mch_storage.voc_coeff)
    with subtests.test("CapEx"):
        assert capex == approx(toc_actual, rel=max_cost_error_rel)
    with subtests.test("Fixed O&M"):
        assert fixed_om == approx(foc_actual, rel=max_cost_error_rel)
    with subtests.test("Variable O&M"):
        assert var_om == approx(voc_actual, rel=max_cost_error_rel)


def test_run_costs(tol_mch_storage, subtests):
    # Supplementary Table 3
    toc_actual = 639375591
    foc_actual = 10239180
    voc_actual = 17332229

    max_cost_error_rel = 0.06
    cost_res = tol_mch_storage.run_costs()

    with subtests.test("CapEx"):
        assert cost_res["mch_capex"] == approx(toc_actual, rel=max_cost_error_rel)
    with subtests.test("Fixed O&M"):
        assert cost_res["mch_opex"] == approx(foc_actual, rel=max_cost_error_rel)
    with subtests.test("Variable O&M"):
        assert cost_res["mch_variable_om"] == approx(voc_actual, rel=max_cost_error_rel)


def test_run_lcos(tol_mch_storage, subtests):
    """
    This test is to highlight the difference between the LCOS when computed
    using different methods from the same reference.
    Specifically, the estimate_lcos and estimate_lcos_from_costs methods which
    use Eq. 7 and Eq. 5 respectively from the source.

    Sources:
        Breunig, H., Rosner, F., Saqline, S. et al. "Achieving gigawatt-scale green hydrogen
    production and seasonal storage at industrial locations across the U.S." *Nat Commun*
    **15**, 9049 (2024). https://doi.org/10.1038/s41467-024-53189-2
    """
    max_cost_error_rel = 0.06
    lcos_est = tol_mch_storage.estimate_lcos()
    lcos_est_from_costs = tol_mch_storage.estimate_lcos_from_costs()

    with subtests.test("lcos equation"):
        assert lcos_est == approx(2.05, rel=max_cost_error_rel)
    with subtests.test("lcos equation from costs"):
        assert lcos_est_from_costs == approx(2.05, rel=max_cost_error_rel)


@fixture
def plant_config():
    plant_config_dict = {
        "plant": {
            "plant_life": 30,
            "simulation": {
                "n_timesteps": 8760,  # Default number of timesteps for the simulation
            },
        },
    }
    return plant_config_dict


def test_mch_wrapper(plant_config, subtests):
    # Ran Example 1 with MCH storage
    # Annual H2 Stored: 17878378.49459929
    Dc_tpd = 304
    Hc_tpd = 304
    As_tpy = 35000
    Ms_tpy = 16200

    toc_actual = 639375591
    foc_actual = 10239180
    voc_actual = 17332229

    max_cost_error_rel = 0.06

    tech_config_dict = {
        "model_inputs": {
            "shared_parameters": {
                "max_capacity": Ms_tpy * 1e3,
                "max_charge_rate": (Hc_tpd + Dc_tpd) * 1e3 / 24,
                "max_discharge_rate": Dc_tpd * 1e3 / 24,  # 10775.824040553021,
                "charge_equals_discharge": False,
            }
        }
    }

    target_annual_h2_stored = As_tpy * 1e3
    c_max = Ms_tpy * 1e3
    n_fills = target_annual_h2_stored / c_max
    fill_ratio_per_hr = n_fills / (8760 / 2)
    fill_per_hr = fill_ratio_per_hr * c_max
    soc = np.tile([fill_per_hr / c_max, 0], 4380)
    prob = om.Problem()
    comp = MCHTOLStorageCostModel(
        plant_config=plant_config,
        tech_config=tech_config_dict,
        driver_config={},
    )
    prob.model.add_subsystem("sys", comp)
    prob.setup()
    prob.set_val("sys.hydrogen_soc", soc)
    prob.run_model()

    with subtests.test("CapEx"):
        assert pytest.approx(prob.get_val("sys.CapEx")[0], rel=max_cost_error_rel) == toc_actual
    with subtests.test("OpEx"):
        assert pytest.approx(prob.get_val("sys.OpEx")[0], rel=max_cost_error_rel) == foc_actual
    with subtests.test("VarOpEx"):
        assert (
            pytest.approx(np.sum(prob.get_val("sys.VarOpEx")), rel=max_cost_error_rel) == voc_actual
        )
    with subtests.test("Cost year"):
        assert prob.get_val("sys.cost_year") == 2024


def test_mch_wrapper_ex1(plant_config, subtests):
    # Ran Example 1 with MCH storage
    # Annual H2 Stored: 17878378.49459929
    tech_config_dict = {
        "model_inputs": {
            "shared_parameters": {
                "max_capacity": 2081385.9326778147,
                "max_charge_rate": 14118.146788766157,
                "max_discharge_rate": 3342.322748213135,  # 10775.824040553021,
                "charge_equals_discharge": False,
            }
        }
    }

    target_annual_h2_stored = 17878378.49459929
    c_max = 2081385.9326778147
    n_fills = target_annual_h2_stored / c_max
    fill_ratio_per_hr = n_fills / (8760 / 2)
    fill_per_hr = fill_ratio_per_hr * c_max
    soc = np.tile([fill_per_hr / c_max, 0], 4380)
    prob = om.Problem()
    comp = MCHTOLStorageCostModel(
        plant_config=plant_config,
        tech_config=tech_config_dict,
        driver_config={},
    )
    prob.model.add_subsystem("sys", comp)
    prob.setup()
    prob.set_val("sys.hydrogen_soc", soc)
    prob.run_model()

    with subtests.test("CapEx"):
        assert pytest.approx(prob.get_val("sys.CapEx")[0], rel=1e-6) == 2.62304217 * 1e8
    with subtests.test("OpEx"):
        assert pytest.approx(prob.get_val("sys.OpEx")[0], rel=1e-6) == 7406935.548022923
    with subtests.test("VarOpEx"):
        assert pytest.approx(np.sum(prob.get_val("sys.VarOpEx")), rel=1e-6) == 9420636.00753175 * 30
    with subtests.test("Cost year"):
        assert prob.get_val("sys.cost_year") == 2024

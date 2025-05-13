from pytest import approx, fixture

from h2integrate.simulation.technologies.hydrogen.h2_storage.mch.mch_cost import MCHStorage


# Test values are based on Supplementary Table 3 of https://doi.org/10.1038/s41467-024-53189-2
# https://rdcu.be/elUsB
Dc_tpd = 80
Hc_tpd = 80
As_tpy = 1500
Ms_tpy = 1000

in_dict = {
    "max_H2_production_kg_pr_hr": (Hc_tpd + Dc_tpd) * 1e3 / 24,
    "hydrogen_storage_capacity_kg": Ms_tpy * 1e3,
    "hydrogen_demand_kg_pr_hr": Dc_tpd * 1e3 / 24,
    "annual_hydrogen_stored_kg_pr_yr": As_tpy * 1e3,
}


@fixture
def tol_mch_storage():
    mch_storage = MCHStorage(**in_dict)

    return mch_storage


def test_init():
    mch_storage = MCHStorage(**in_dict)

    assert mch_storage.cost_year is not None
    assert mch_storage.occ_coeff is not None


def test_sizing(tol_mch_storage, subtests):
    with subtests.test("Dehydrogenation capacity"):
        assert tol_mch_storage.Dc == approx(Dc_tpd, rel=1e-6)
    with subtests.test("Hydrogenation capacity"):
        assert tol_mch_storage.Hc == approx(Hc_tpd, rel=1e-6)
    with subtests.test("Annual storage capacity"):
        assert tol_mch_storage.As == approx(As_tpy, rel=1e-6)
    with subtests.test("Maximum storage capacity"):
        assert tol_mch_storage.Ms == approx(Ms_tpy, rel=1e-6)


def test_cost_calculation_methods(tol_mch_storage, subtests):
    capex = tol_mch_storage.calc_capex()
    fixed_om = tol_mch_storage.calc_fixed_om()
    var_om = tol_mch_storage.calc_variable_om()
    with subtests.test("CapEx"):
        assert capex == approx(125018316, abs=1)
    with subtests.test("Fixed O&M"):
        assert fixed_om == approx(4622049, abs=1)
    with subtests.test("Variable O&M"):
        assert var_om == approx(6941258, abs=1)


def test_run_costs(tol_mch_storage, subtests):
    cost_res = tol_mch_storage.run_costs()

    with subtests.test("CapEx"):
        assert cost_res["mch_capex"] == approx(125018316, abs=1)
    with subtests.test("Fixed O&M"):
        assert cost_res["mch_opex"] == approx(4622049, abs=1)
    with subtests.test("Variable O&M"):
        assert cost_res["mch_variable_om"] == approx(6941258, abs=1)

import numpy as np
from pytest import approx

from h2integrate import EXAMPLE_DIR
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_natural_geoh2(subtests):
    h2i_nat = H2IntegrateModel(EXAMPLE_DIR / "04_geo_h2" / "04_geo_h2_natural.yaml")
    h2i_nat.run()

    with subtests.test("H2 Production"):
        h2_prod = h2i_nat.plant.geoh2_well_subsurface.simple_natural_geoh2_performance.get_val(
            "hydrogen_out"
        )
        assert np.mean(h2_prod) == approx(603.4286677531819, 1e-6)

    with subtests.test("integrate LCOH"):
        lcoh = h2i_nat.prob.get_val("finance_subgroup_h2.LCOH")
        assert lcoh == approx(1.59307314, 1e-6)

    with subtests.test("subsurface capex"):
        capex = h2i_nat.plant.geoh2_well_subsurface.mathur_modified_geoh2_cost.get_val("CapEx")
        assert capex == approx(7667341.11417252, 1e-6)
    with subtests.test("subsurface fixed Opex"):
        opex = h2i_nat.plant.geoh2_well_subsurface.mathur_modified_geoh2_cost.get_val("OpEx")
        assert opex == approx(215100.7857875, 1e-6)
    with subtests.test("subsurface variable"):
        var = h2i_nat.plant.geoh2_well_subsurface.mathur_modified_geoh2_cost.get_val("VarOpEx")
        assert var == approx(0, 1e-6)
    with subtests.test("subsurface adjusted opex"):
        op = h2i_nat.prob.get_val("finance_subgroup_h2.opex_adjusted_geoh2_well_subsurface")
        assert op == approx(215100.7857875, 1e-6)
    with subtests.test("surface capex"):
        capex = h2i_nat.plant.geoh2_well_surface.aspen_geoh2_cost.get_val("CapEx")
        assert capex == approx(1795733.55, 1e-6)
    with subtests.test("surface fixed Opex"):
        opex = h2i_nat.plant.geoh2_well_surface.aspen_geoh2_cost.get_val("OpEx")
        assert opex == approx(4567464, 1e-6)
    with subtests.test("surface variable"):
        var = h2i_nat.plant.geoh2_well_surface.aspen_geoh2_cost.get_val("VarOpEx")
        assert var == approx(984842.53, 1e-6)
    with subtests.test("surface adjusted opex"):
        op = h2i_nat.prob.get_val("finance_subgroup_h2.opex_adjusted_geoh2_well_surface")
        assert op == approx(4798691.865, 1e-6)


def test_stimulated_geoh2(subtests):
    h2i_stim = H2IntegrateModel(EXAMPLE_DIR / "04_geo_h2" / "04_geo_h2_stimulated.yaml")
    h2i_stim.run()
    prod = (
        h2i_stim.plant.geoh2_well_subsurface.templeton_serpentinization_geoh2_performance.get_val(
            "hydrogen_out"
        )
    )

    with subtests.test("H2 Production"):
        assert np.mean(prod) == approx(155.03934945719536, 1e-6)

    with subtests.test("integrate LCOH"):
        lcoh = h2i_stim.prob.get_val("finance_subgroup_default.LCOH")
        assert lcoh == approx(
            2.29337734, 1e-6
        )  # previous val from custom finance model was 1.74903827

    # failure is expected because we are inflating using general inflation rather than CPI and CEPCI
    with subtests.test("capex"):
        capex = h2i_stim.plant.geoh2_well_subsurface.mathur_modified_geoh2_cost.get_val("CapEx")
        assert capex == approx(19520122.88478073, 1e-6)
    with subtests.test("fixed Opex"):
        opex = h2i_stim.plant.geoh2_well_subsurface.mathur_modified_geoh2_cost.get_val("OpEx")
        assert opex == approx(215100.7857875, 1e-6)
    with subtests.test("variable"):
        var = h2i_stim.plant.geoh2_well_subsurface.mathur_modified_geoh2_cost.get_val("VarOpEx")
        var = var / np.sum(prod)
        assert var == approx(0.32105362, 1e-6)
    with subtests.test("adjusted opex"):
        op = h2i_stim.prob.get_val("finance_subgroup_default.opex_adjusted_geoh2_well_subsurface")
        assert op == approx(215100.7857875, 1e-6)

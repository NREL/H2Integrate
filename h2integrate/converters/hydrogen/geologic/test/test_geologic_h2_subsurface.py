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
        assert np.mean(h2_prod) == approx(117.72509205764842, 1e-6)

    with subtests.test("integrate LCOH"):
        lcoh = h2i_nat.prob.get_val("finance_subgroup_default.LCOH")
        assert lcoh == approx(
            1.72828635, 1e-6
        )  # previous val from custom finance model was 1.2440904


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
            2.35625412, 1e-6
        )  # previous val from custom finance model was 1.74903827

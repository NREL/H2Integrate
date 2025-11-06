import numpy as np
from pytest import approx

from h2integrate import EXAMPLE_DIR
from h2integrate.core.h2integrate_model import H2IntegrateModel


def test_natural_geoh2(subtests):
    h2i_nat = H2IntegrateModel(EXAMPLE_DIR / "04_geo_h2" / "04_geo_h2_natural.yaml")
    h2i_nat.run()

    with subtests.test("H2 Production"):
        h2_prod = h2i_nat.plant.geoh2.natural_geoh2_performance.get_val("hydrogen_out")
        assert np.mean(h2_prod) == approx(117.72509205764842, 1e-6)
    with subtests.test("LCOH"):
        lcoh = h2i_nat.plant.geoh2.geoh2_finance.get_val("LCOH")
        assert lcoh == approx(1.2440904, 1e-6)


def test_stimulated_geoh2(subtests):
    h2i_stim = H2IntegrateModel(EXAMPLE_DIR / "04_geo_h2" / "04_geo_h2_stimulated.yaml")
    h2i_stim.run()

    with subtests.test("H2 Production"):
        h2_prod = h2i_stim.plant.geoh2.stimulated_geoh2_performance.get_val("hydrogen_out")
        assert np.mean(h2_prod) == approx(155.03934945719536, 1e-6)
    with subtests.test("LCOH"):
        lcoh = h2i_stim.plant.geoh2.geoh2_finance.get_val("LCOH")
        assert lcoh == approx(1.74803827, 1e-6)

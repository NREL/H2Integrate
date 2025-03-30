from pathlib import Path

import numpy as np
from pytest import approx, fixture
from ORBIT.core.library import initialize_library

from h2integrate.simulation.h2integrate_simulation import (
    H2IntegrateSimulationConfig,
    run_simulation,
)
from h2integrate.simulation.technologies.hydrogen.electrolysis.PEM_BOP.PEM_BOP import pem_bop


LIBRARY = Path(__file__).parents[1] / "input_files/"

initialize_library(LIBRARY)

turbine_model = "osw_18MW"
filename_turbine_config = LIBRARY / f"turbines/{turbine_model}.yaml"
filename_orbit_config = LIBRARY / f"plant/orbit-config-{turbine_model}-stripped.yaml"
filename_floris_config = LIBRARY / f"floris/floris_input_{turbine_model}.yaml"
filename_h2integrate_config = LIBRARY / "plant/h2integrate_config.yaml"
filename_hopp_config = LIBRARY / "plant/hopp_config.yaml"


@fixture
def bop_energy():
    power_profile_kw = np.array(
        [
            0,
            9999,  # just below turndown ratio
            10000,  # exactly at turndown ratio
            82746,
            93774,  # max power in csv. largest operating ratio
            100000,  # full power
        ]
    )

    electrolyzer_rating_mw = 100  # MW
    turndown_ratio = 0.1

    bop_energy = pem_bop(
        power_profile_to_electrolyzer_kw=power_profile_kw,
        electrolyzer_rated_mw=electrolyzer_rating_mw,
        electrolyzer_turn_down_ratio=turndown_ratio,
    )
    return bop_energy


def test_bop_energy(subtests, bop_energy):
    with subtests.test("No power"):
        assert bop_energy[0] == 0
    with subtests.test("below turndown"):
        assert bop_energy[1] == 0
    with subtests.test("at turndown"):
        assert bop_energy[2] == approx(11917.425640927953, 1e-2)
    with subtests.test("mid-range power"):
        assert bop_energy[3] == approx(7369.486215576719, 1e-2)
    with subtests.test("max power in curve"):
        assert bop_energy[4] == approx(8403.36134509804)
    with subtests.test("full power"):
        assert bop_energy[5] == approx(8403.36134509804)


def test_h2integrate_simulation_pem_bop(subtests):
    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_h2integrate_config=filename_h2integrate_config,
        filename_turbine_config=filename_turbine_config,
        filename_orbit_config=filename_orbit_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=1,
        output_level=3,
    )
    lcoh, _, _, _, _, _, _, annual_energy_breakdown = run_simulation(config)

    # include electrolyzer bop power consumption in h2integrate simulation
    config.h2integrate_config["electrolyzer"]["include_bop_power"] = True

    lcoh2, _, _, _, _, _, _, annual_energy_breakdown2 = run_simulation(config)

    with subtests.test("LCOH not equal"):
        assert lcoh != lcoh2

    with subtests.test("annual_energy_breakdown no electrolyzer bop"):
        assert annual_energy_breakdown["electrolyzer_bop_energy_kwh"] == 0

    with subtests.test("annual_energy_breakdown electrolyzer bop"):
        assert annual_energy_breakdown2["electrolyzer_bop_energy_kwh"] == approx(
            85578390.12022397, 1e-3
        )

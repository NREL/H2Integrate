from pathlib import Path

from pytest import approx

from h2integrate.simulation.h2integrate_simulation import (
    H2IntegrateSimulationConfig,
    run_simulation,
)


INPUTS = Path(__file__).parent / "input"
INPUT_PATH = Path(__file__).parent.parent / "test_greensteel" / "input"
OUTPUTS = Path(__file__).parent / "output"


def test_iron_simulation(subtests):
    # load inputs
    turbine_model = "lbw_6MW"
    filename_turbine_config = INPUT_PATH / f"turbines/{turbine_model}.yaml"
    filename_floris_config = INPUT_PATH / f"floris/floris_input_{turbine_model}.yaml"
    filename_hopp_config = INPUTS / "hopp_config.yaml"
    filename_h2integrate_config = INPUTS / "h2integrate_config_modular.yaml"

    config = H2IntegrateSimulationConfig(
        filename_hopp_config,
        filename_h2integrate_config,
        filename_turbine_config,
        filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        use_profast=True,
        post_processing=False,
        run_full_simulation=True,
        iron_modular=True,
        run_full_simulation_fn=OUTPUTS,
        iron_out_fn=OUTPUTS,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=7,
    )

    lcoe, lcoh, iron_finance, _ = run_simulation(config)
    lcoi = iron_finance.sol["price"]

    with subtests.test("LCOE"):
        assert lcoe * 1e3 == approx(44.90951, 1e-6)
    with subtests.test("LCOH"):
        assert lcoh == approx(5.470888, 1e-6)
    with subtests.test("LCOI"):
        assert lcoi == approx(528.501656, 1e-6)

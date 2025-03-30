import inspect
import warnings
from pathlib import Path

import pandas as pd
from pytest import skip, warns, approx
from hopp.utilities.keys import set_nrel_key_dot_env

from h2integrate.simulation.h2integrate_simulation import (
    H2IntegrateSimulationConfig,
    H2IntegrateSimulationOutput,
    run_simulation,
)


set_nrel_key_dot_env()

from ORBIT.core.library import initialize_library


dirname = Path(__file__).parent
orbit_library_path = dirname / "input_files/"
output_path = Path(__file__).parent / "output/"

initialize_library(orbit_library_path)

turbine_model = "osw_18MW"
filename_turbine_config = orbit_library_path / f"turbines/{turbine_model}.yaml"
filename_orbit_config = orbit_library_path / f"plant/orbit-config-{turbine_model}-stripped.yaml"
filename_floris_config = orbit_library_path / f"floris/floris_input_{turbine_model}.yaml"
filename_h2integrate_config = orbit_library_path / "plant/h2integrate_config.yaml"
filename_h2integrate_config_onshore = orbit_library_path / "plant/h2integrate_config_onshore.yaml"
filename_hopp_config = orbit_library_path / "plant/hopp_config.yaml"
filename_hopp_config_wind_wave = orbit_library_path / "plant/hopp_config_wind_wave.yaml"
filename_hopp_config_wind_wave_solar = orbit_library_path / "plant/hopp_config_wind_wave_solar.yaml"
filename_hopp_config_wind_wave_solar_battery = (
    orbit_library_path / "plant/hopp_config_wind_wave_solar_battery.yaml"
)

rtol = 1e-5


def test_simulation_wind(subtests):
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
        output_level=5,
    )
    lcoe, lcoh, _, hi = run_simulation(config)

    with subtests.test("lcoh"):
        assert lcoh == approx(6.672584971381463)  # TODO base this test value on something

    with subtests.test("lcoe"):
        assert lcoe == approx(0.11273307765405276)  # TODO base this test value on something

    with subtests.test("energy sources"):
        expected_annual_energy_hybrid = hi.system.annual_energies.wind
        assert hi.system.annual_energies.hybrid == approx(expected_annual_energy_hybrid)

    with subtests.test("num_turbines conflict raise warning"):
        config.orbit_config["plant"]["num_turbines"] = 400
        with warns(UserWarning, match="The 'num_turbines' value"):
            lcoe, lcoh, _, hi = run_simulation(config)

    with subtests.test("depth conflict raise warning"):
        config.orbit_config["site"]["depth"] = 4000
        with warns(UserWarning, match="The site depth value"):
            lcoe, lcoh, _, hi = run_simulation(config)

    with subtests.test("turbine_spacing conflict raise warning"):
        config.orbit_config["plant"]["turbine_spacing"] = 400
        with warns(UserWarning, match="The 'turbine_spacing' value"):
            lcoe, lcoh, _, hi = run_simulation(config)

    with subtests.test("row_spacing conflict raise warning"):
        config.orbit_config["plant"]["row_spacing"] = 400
        with warns(UserWarning, match="The 'row_spacing' value"):
            lcoe, lcoh, _, hi = run_simulation(config)


def test_simulation_wind_wave(subtests):
    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config_wind_wave,
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
        output_level=5,
    )

    lcoe, lcoh, _, hi = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert lcoh == approx(7.684496636250683, rel=rtol)

    # prior to 20240207 value was approx(0.11051228251811765) # TODO base value on something
    with subtests.test("lcoe"):
        assert lcoe == approx(0.1359140179164504, rel=rtol)


def test_simulation_wind_wave_solar(subtests):
    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config_wind_wave_solar,
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
        plant_design_scenario=11,
        output_level=5,
    )

    lcoe, lcoh, _, hi = run_simulation(config)

    # prior to 20240207 value was approx(10.823798551850347)
    # TODO base this test value on something. Currently just based on output at writing.
    with subtests.test("lcoh"):
        assert lcoh == approx(11.977286578936068, rel=rtol)

    # prior to 20240207 value was approx(0.11035426429749774)
    # TODO base this test value on something. Currently just based on output at writing.
    with subtests.test("lcoe"):
        assert lcoe == approx(0.13569490554319152, rel=rtol)


def test_simulation_io(subtests):
    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_h2integrate_config=filename_h2integrate_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        output_dir=output_path,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=8,
    )

    temp_file_path = Path("tmp.yaml")

    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_fixed"][0] = (
        config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
    )
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False
    output_o = run_simulation(config)

    with subtests.test("save_output"):
        output_o.save_to_file("tmp.yaml")

    with subtests.test("load_saved_output"):
        output_i = H2IntegrateSimulationOutput.load_from_file(temp_file_path)

    if temp_file_path.exists():
        temp_file_path.unlink()

    members_o = inspect.getmembers(output_o, lambda a: not (inspect.isroutine(a)))
    members_i = inspect.getmembers(output_i, lambda a: not (inspect.isroutine(a)))

    ignore = ["ammonia_finance", "steel_finance"]

    with subtests.test("WACC"):
        assert output_i.profast_sol_lcoh["wacc"] == approx(0.0620373)

    with subtests.test("CRF"):
        assert output_i.profast_sol_lcoh["crf"] == approx(0.071903176)

    for i, obj in enumerate(members_i):
        with subtests.test(f"io equality {i}/{obj}"):
            if obj[0] in ignore:
                skip(
                    "we do not expect equality for these indexes because of excluded information"
                    "in the yaml dump and complex data type nesting"
                )
            if i > 14:
                skip(
                    "we do not expect equality for these indexes because of excluded information"
                    "in the yaml dump and complex data type nesting"
                )

            assert isinstance(members_o[i], type(obj))

            if len(obj) > 1:
                if isinstance(obj, pd.Series):
                    assert obj.equals(members_i[i])
                elif isinstance(obj, dict):
                    for key in obj.keys():
                        if key.startswith("_"):
                            skip("don't compare private methods")
                        if len(obj[key] > 1):
                            for j, el in enumerate(obj[key]):
                                assert el == members_i[i][key][j]
                        else:
                            assert obj[key] == members_i[i][key]
                else:
                    for j, el in enumerate(obj):
                        if isinstance(el, pd.Series):
                            assert el.equals(members_i[i][j])
                        elif el is None:
                            skip("don't compare None type attributes")
                        elif type(el) is str and el.startswith("_"):
                            skip("don't compare private methods")
                        else:
                            assert el == members_o[i][j]
            else:
                assert obj == members_o[i]


def test_simulation_wind_wave_solar_battery(subtests):
    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config_wind_wave_solar_battery,
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
        plant_design_scenario=10,
        output_level=8,
    )

    results = run_simulation(config)

    with subtests.test("lcoh"):
        # TODO base this test value on something. Currently just based on output at writing.
        assert results.lcoh == approx(15.957807582256383, rel=rtol)

    with subtests.test("lcoe"):
        # TODO base this test value on something. Currently just based on output at writing.
        assert results.lcoe == approx(0.13588498391763934, rel=rtol)
    with subtests.test("no conflict in om cost does not raise warning"):
        with warnings.catch_warnings():
            warnings.simplefilter("error")

    with subtests.test("wind_om_per_kw conflict raise warning"):
        config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_capacity"][
            0
        ] = 1.0
        with warns(UserWarning, match="The 'om_capacity' value in the wind 'fin_model'"):
            _ = run_simulation(config)

    with subtests.test("pv_om_per_kw conflict raise warning"):
        config.hopp_config["technologies"]["pv"]["fin_model"]["system_costs"]["om_capacity"][0] = (
            1.0
        )
        with warns(UserWarning, match="The 'om_capacity' value in the pv 'fin_model'"):
            _ = run_simulation(config)

    with subtests.test("battery_om_per_kw conflict raise warning"):
        config.hopp_config["technologies"]["battery"]["fin_model"]["system_costs"]["om_capacity"][
            0
        ] = 1.0
        with warns(UserWarning, match="The 'om_capacity' value in the battery 'fin_model'"):
            _ = run_simulation(config)


def test_simulation_wind_onshore(subtests):
    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_h2integrate_config=filename_h2integrate_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=False,
        use_profast=True,
        post_processing=False,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=5,
    )
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False

    lcoe, lcoh, _, _ = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert lcoh == approx(2.8752521491871312, rel=rtol)

    # TODO base this test value on something
    with subtests.test("lcoe"):
        assert lcoe == approx(0.03486192934806013, rel=rtol)


def test_simulation_wind_onshore_steel_ammonia(subtests):
    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_h2integrate_config=filename_h2integrate_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=True,
        output_dir=output_path,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=7,
    )

    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_fixed"][0] = (
        config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
    )
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False
    lcoe, lcoh, steel_finance, ammonia_finance = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert lcoh == approx(2.8752542931148994, rel=rtol)

    # TODO base this test value on something
    with subtests.test("lcoe"):
        assert lcoe == approx(0.03486192934806013, rel=rtol)

    # TODO base this test value on something
    with subtests.test("steel_finance"):
        lcos_expected = 1394.8936273463223

        assert steel_finance.sol.get("price") == approx(lcos_expected, rel=rtol)

    # TODO base this test value on something
    with subtests.test("ammonia_finance"):
        lcoa_expected = 1.0614633836561882

        assert ammonia_finance.sol.get("price") == approx(lcoa_expected, rel=rtol)


def test_simulation_wind_battery_pv_onshore_steel_ammonia(subtests):
    plant_design_scenario = 12

    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config_wind_wave_solar_battery,
        filename_h2integrate_config=filename_h2integrate_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_orbit_config=filename_orbit_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=True,
        output_dir=output_path,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=plant_design_scenario,
        output_level=8,
    )

    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_fixed"][0] = (
        config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
    )
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False
    # exclude wave
    config.hopp_config["technologies"].pop("wave")
    config.hopp_config["site"]["wave"] = False
    # colocated end-use
    config.h2integrate_config["plant_design"][f"scenario{plant_design_scenario}"][
        "transportation"
    ] = "colocated"

    # run the simulation
    h2integrate_output = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert h2integrate_output.lcoh == approx(2.856219558092931, rel=rtol)

    # TODO base this test value on something
    with subtests.test("lcoe"):
        assert h2integrate_output.lcoe == approx(0.03475765253339192, rel=rtol)

    # TODO base this test value on something
    with subtests.test("steel_finance"):
        lcos_expected = 1386.766783710166

        assert h2integrate_output.steel_finance.sol.get("price") == approx(lcos_expected, rel=rtol)

    # TODO base this test value on something
    with subtests.test("ammonia_finance"):
        lcoa_expected = 1.0599198593495158

        assert h2integrate_output.ammonia_finance.sol.get("price") == approx(
            lcoa_expected, rel=rtol
        )

    with subtests.test("check time series lengths"):
        expected_length = 8760

        for key in h2integrate_output.hourly_energy_breakdown.keys():
            assert len(h2integrate_output.hourly_energy_breakdown[key]) == expected_length


def test_simulation_wind_onshore_steel_ammonia_ss_h2storage(subtests):
    config = H2IntegrateSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_h2integrate_config=filename_h2integrate_config_onshore,
        filename_turbine_config=filename_turbine_config,
        filename_floris_config=filename_floris_config,
        verbose=False,
        show_plots=False,
        save_plots=True,
        output_dir=output_path,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=9,
        output_level=7,
    )

    config.h2integrate_config["h2_storage"]["size_capacity_from_demand"]["flag"] = True
    config.h2integrate_config["h2_storage"]["type"] = "pipe"

    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_installed_cost_mw"] = 1434000.0
    # based on 2023 ATB moderate case for onshore wind
    config.hopp_config["config"]["cost_info"]["wind_om_per_kw"] = 29.567
    config.hopp_config["technologies"]["wind"]["fin_model"]["system_costs"]["om_fixed"][0] = (
        config.hopp_config["config"]["cost_info"]["wind_om_per_kw"]
    )
    # set skip_financial to false for onshore wind
    config.hopp_config["config"]["simulation_options"]["wind"]["skip_financial"] = False
    lcoe, lcoh, steel_finance, ammonia_finance = run_simulation(config)

    # TODO base this test value on something
    with subtests.test("lcoh"):
        assert lcoh == approx(9.770004584550266, rel=rtol)

    # TODO base this test value on something
    with subtests.test("lcoe"):
        assert lcoe == approx(0.03486192934806013, rel=rtol)

    # TODO base this test value on something
    with subtests.test("steel_finance"):
        lcos_expected = 1854.6647824504835
        assert steel_finance.sol.get("price") == approx(lcos_expected, rel=rtol)

    # TODO base this test value on something
    with subtests.test("ammonia_finance"):
        lcoa_expected = 1.0614633836561882
        assert ammonia_finance.sol.get("price") == approx(lcoa_expected, rel=rtol)

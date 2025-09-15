import copy

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def plot_ammonia(model):
    plt.clf()

    times = pd.date_range("2013", periods=8760, freq="1h")

    # HOPP Electricity Generation
    plt.subplot(3, 2, 1)
    plt.title("Electricity Generation")
    wind_elec_out = model.plant.hopp.hopp.get_val("wind_electricity_out")
    pv_elec_out = model.plant.hopp.hopp.get_val("solar_electricity_out")
    elec_out = wind_elec_out + pv_elec_out
    plt.plot(times, wind_elec_out, label="wind_electricity_out [kW]", color=[0, 0.5, 0.5])
    plt.plot(times, pv_elec_out, label="solar_electricity_out [kW]", color=[0.5, 0.5, 0])
    plt.plot(times, elec_out, label="electricity_out [kW]", color=[0.5, 0, 0.5])
    # plt.yscale("log")
    plt.legend()

    # HOPP Battery Dispatch
    plt.subplot(3, 2, 3)
    plt.title("Electricity to/from Storage")
    elec_in = elec_out
    batt_elec_out = model.plant.hopp.hopp.get_val("battery_electricity_out")
    total_elec_out = model.plant.hopp.hopp.get_val("electricity_out")
    plt.plot(times, elec_in, label="electricity_in [kW]", color=[0.5, 0, 0.5])
    plt.plot(times, batt_elec_out, label="battery_electricity_out [kW]", color=[0, 1, 0])
    plt.plot(times, total_elec_out, label="total_electricity_out [kW]", color=[0, 0, 1])
    # plt.yscale("log")
    plt.legend()

    # Electricity to H2 using Electrolyzer
    plt.subplot(3, 2, 5)
    plt.title("Electrolyzer")
    elyzer_elec_in = model.plant.electrolyzer.eco_pem_electrolyzer_performance.get_val(
        "electricity_in"
    )
    elyzer_h2_out = model.plant.electrolyzer.eco_pem_electrolyzer_performance.get_val(
        "hydrogen_out"
    )
    plt.plot(times, elyzer_elec_in / 1000, label="electricity_in [MW]", color=[0, 0, 1])
    plt.plot(times, elyzer_h2_out * 24 / 1000, label="hydrogen_out [tpd]", color=[1, 0, 0])
    # plt.yscale("log")
    plt.legend()

    # H2 and Storage
    plt.subplot(3, 2, 2)
    plt.title("H2 Storage")
    h2_storage_in = model.plant.h2_storage.h2_storage.get_val("hydrogen_in")
    h2_storage_out = model.plant.h2_storage_to_ammonia_pipe.get_val("hydrogen_out") * 3600
    plt.plot(times, h2_storage_in, label="hydrogen_in [kg/hr]", color=[1, 0, 0])
    plt.plot(times, h2_storage_out, label="hydrogen_out [kg/hr]", color=[1, 0.5, 0])
    # plt.yscale("log")
    plt.legend()

    # H2 and N2 to Ammonia
    plt.subplot(3, 2, 4)
    plt.title("Methanol")
    nh3_h2_in = model.plant.ammonia.synloop_ammonia_performance.get_val("hydrogen_in")
    nh3_out = model.plant.ammonia.synloop_ammonia_performance.get_val("ammonia_out")
    plt.plot(times, nh3_h2_in, label="hydrogen_in [kg/hr]", color=[1, 0.5, 0])
    plt.plot(times, nh3_out, label="ammonia_out [kg/hr]", color=[0, 0.5, 1])
    # plt.yscale("log")
    plt.legend()

    # H2 and Storage
    plt.subplot(3, 2, 6)
    plt.title("Storage")
    batt_kwh = model.plant.hopp.hopp.hopp_config["technologies"]["battery"]["system_capacity_kwh"]
    min_soc = model.plant.hopp.hopp.hopp_config["technologies"]["battery"]["minimum_SOC"]
    soc = model.plant.hopp.hopp.hopp_config["technologies"]["battery"]["initial_SOC"]
    batt_soc_change = -batt_elec_out / batt_kwh
    batt_storage_soc = []
    for _i, SOC_change in enumerate(batt_soc_change):
        soc += SOC_change * 100
        batt_storage_soc.append(copy.deepcopy(soc))
    soc_adjust = np.linspace(0, (soc - min_soc), len(batt_storage_soc))
    batt_storage_soc = batt_storage_soc - soc_adjust
    h2_storage_soc = model.plant.h2_storage.h2_storage.get_val("hydrogen_storage_soc")
    max_kg = model.plant.h2_storage.h2_storage.options["tech_config"]["model_inputs"][
        "control_parameters"
    ]["max_capacity"]
    h2_storage_soc = h2_storage_soc / max_kg * 100
    plt.plot(times, batt_storage_soc, label="battery_soc [%]", color=[0, 1, 0])
    plt.plot(times, h2_storage_soc, label="hydrogen_storage_soc [%]", color=[1, 0, 0])
    # plt.yscale("log")
    plt.legend()

    fig = plt.gcf()
    fig.tight_layout()
    plt.show()

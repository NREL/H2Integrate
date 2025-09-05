import pandas as pd
import matplotlib.pyplot as plt


def plot_methanol(model):
    plt.clf()

    times = pd.date_range("2013", periods=8760, freq="1h")

    # HOPP Electricity for Electrolyzer
    plt.subplot(3, 2, 1)
    plt.title("HOPP for Electrolyzer")
    hopp_elec_out = model.plant.hopp.hopp.get_val("electricity_out")
    plt.plot(times, hopp_elec_out, label="electricity_out [kW]")
    plt.yscale("log")
    plt.legend()

    # Electricity to H2 using Electrolyzer
    plt.subplot(3, 2, 3)
    plt.title("Electrolyzer")
    elyzer_elec_in = model.plant.electrolyzer.eco_pem_electrolyzer_performance.get_val(
        "electricity_in"
    )
    elyzer_h2_out = model.plant.electrolyzer.eco_pem_electrolyzer_performance.get_val(
        "hydrogen_out"
    )
    plt.plot(times, elyzer_elec_in, label="electricity_in [kW]")
    plt.plot(times, elyzer_h2_out, label="hydrogen_out [kg/hr]", color=[1, 0.5, 0])
    plt.yscale("log")
    plt.legend()

    # Wind Electricity for DOC
    plt.subplot(3, 2, 2)
    plt.title("Wind for DOC")
    wind_elec_out = model.plant.wind.wind_plant_performance.get_val("electricity_out")
    plt.plot(times, wind_elec_out, label="electricity_out [kW]")
    plt.yscale("log")
    plt.legend()

    # Electricity to CO2 using DOC
    plt.subplot(3, 2, 4)
    plt.title("DOC")
    doc_elec_in = model.plant.doc.direct_ocean_capture_performance.get_val("electricity_in") / 1000
    doc_co2_out = model.plant.doc.direct_ocean_capture_performance.get_val("co2_out")
    plt.plot(times, doc_elec_in, label="electricity_in [kW]")
    plt.plot(times, doc_co2_out, label="co2_out [kg/hr]", color=[0.5, 0.25, 0])
    plt.yscale("log")
    plt.legend()

    # H2 and Storage
    plt.subplot(3, 2, 5)
    plt.title("H2 Storage")
    h2_storage_in = model.plant.h2_storage.h2_storage.get_val("hydrogen_in")
    h2_storage_out = model.plant.h2_storage_to_methanol_pipe.get_val("hydrogen_out") * 3600
    plt.plot(times, h2_storage_in, label="hydrogen_in [kg/hr]", color=[1, 0.5, 0])
    plt.plot(times, h2_storage_out, label="hydrogen_out [kg/hr]", color=[0, 0.5, 0])
    plt.yscale("log")
    plt.legend()

    # H2 and CO2 to Methanol
    plt.subplot(3, 2, 6)
    plt.title("Methanol")
    meoh_h2_in = model.plant.methanol.co2h_methanol_plant_performance.get_val("hydrogen_in")
    meoh_co2_in = model.plant.methanol.co2h_methanol_plant_performance.get_val("co2_in")
    meoh_meoh_out = model.plant.methanol.co2h_methanol_plant_performance.get_val("methanol_out")
    plt.plot(times, meoh_h2_in, label="hydrogen_in [kg/hr]", color=[0, 0.5, 0])
    plt.plot(times, meoh_co2_in, label="co2_in [kg/hr]", color=[0.5, 0.25, 0])
    plt.plot(times, meoh_meoh_out, label="methanol_out [kg/hr]", color=[1, 0, 0.5])
    plt.yscale("log")
    plt.legend()

    fig = plt.gcf()
    fig.tight_layout()
    plt.show()

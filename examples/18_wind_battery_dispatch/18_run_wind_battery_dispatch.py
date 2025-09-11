import numpy as np
from matplotlib import pyplot as plt

from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create an H2Integrate model
model = H2IntegrateModel("h2i_wind_to_battery_storage.yaml")

demand_profile = np.ones(8760) * 100000.0

# TODO: Update with demand module once it is developed
model.setup()
model.prob.set_val("battery.demand_in", demand_profile)

# Run the model
model.run()


# Plot the results
fig, ax = plt.subplots(2, 1, sharex=True)

start_hour = 0
end_hour = 24

ax[0].plot(
    range(start_hour, end_hour),
    model.prob.get_val("battery.SOC", units="percent")[start_hour:end_hour],
    label="SOC",
)
ax[0].set_ylabel("SOC (%)")
ax[0].set_ylim([0, 110])

ax[1].plot(
    range(start_hour, end_hour),
    model.prob.get_val("battery.electricity_in", units="kW")[start_hour:end_hour],
    linestyle="-",
    label="Electricity In (kW)",
)
ax[1].plot(
    range(start_hour, end_hour),
    model.prob.get_val("battery.excess_resource_out", units="kW/h")[start_hour:end_hour],
    linestyle=":",
    label="Excess Electricity (kW)",
)
ax[1].plot(
    range(start_hour, end_hour),
    model.prob.get_val("battery.unmet_demand_out", units="kW/h")[start_hour:end_hour],
    linestyle=":",
    label="Unmet Electrical Demand (kW)",
)
ax[1].plot(
    range(start_hour, end_hour),
    model.prob.get_val("battery.electricity_out", units="kW/h")[start_hour:end_hour],
    linestyle="-",
    label="Electricity Out (kW)",
)
ax[1].plot(
    range(start_hour, end_hour),
    model.prob.get_val("battery.battery_electricity_out", units="kW/h")[start_hour:end_hour],
    linestyle="-.",
    label="Battery Electricity Out (kW)",
)
ax[1].plot(
    range(start_hour, end_hour),
    demand_profile[start_hour:end_hour],
    linestyle="--",
    label="Eletrical Demand (kW)",
)
ax[1].set_ylim([-1e5, 6e5])
ax[1].set_ylabel("Electricity Hourly (kW)")
ax[1].set_xlabel("Timestep (hr)")

# ax[2].plot(
#     range(start_hour, end_hour),
#     model.prob.get_val("battery.P_chargeable")[start_hour:end_hour],
#     linestyle="-.",
#     label="P_chargeable (kW)",
# )
# ax[2].plot(
#     range(start_hour, end_hour),
#     model.prob.get_val("battery.P_dischargeable")[start_hour:end_hour],
#     linestyle=":",
#     label="P_dischargeable (kW)",
# )
# ax[2].set_ylim([-6e5, 12e5])
# ax[2].set_ylabel("Electricity Hourly (kW)")
# ax[2].set_xlabel("Timestep (hr)")

plt.legend(ncol=2, frameon=False)
plt.savefig("plot.png")

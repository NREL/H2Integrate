import os
from pathlib import Path

from h2integrate.core.h2integrate_model import H2IntegrateModel


os.chdir(Path.parent(__file__))
# os.chdir(folder)
model = H2IntegrateModel("15_solar_pv.yaml")

# Run the model
model.run()

model.post_process()

lcoe = model.model.get_val("financials_group_default.LCOE")[0]  # $/kWh
aep_kWh_per_year = model.model.get_val("solar.annual_energy")[0]  # kWh/year
capacity_kWac = model.model.get_val("solar.capacity_kWac")[0]  # kW-AC
capacity_factor_AC = aep_kWh_per_year / (capacity_kWac * 8760)

capacity_factor_target = 0.318212860052615
lcoe_target = 31  # [$/MWh] - From ATB
lcoe_usd_per_mwh = lcoe * 1e3

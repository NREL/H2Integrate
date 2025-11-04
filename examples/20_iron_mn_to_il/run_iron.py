from pathlib import Path

from h2integrate.tools.run_cases import modify_tech_config, load_tech_config_cases
from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a H2Integrate model
model = H2IntegrateModel("20_iron.yaml")

# Load cases
case_file = Path("test_inputs.csv")
cases = load_tech_config_cases(case_file)

# Modify and run the model for different cases
casenames = [
    "Baseline H2 None",
    "Location H2 None",
    "Ore Grade H2 None",
    "Mine H2 None",
    "Transport H2 None",
    "LCOE 50 H2 None",
    "LCOH 6 H2 None",
    "LCOH 3 H2 None",
    "NG 8 H2 None",
    "Capex H2 None",
    "Baseline H2 EAF",
    "Location H2 EAF",
    "Ore Grade H2 EAF",
    "Mine H2 EAF",
    "Transport H2 EAF",
    "LCOE 50 H2 EAF",
    "LCOH 6 H2 EAF",
    "LCOH 3 H2 EAF",
    "NG 8 H2 EAF",
    "Capex H2 EAF",
    "Baseline NG None",
    "Location NG None",
    "Ore Grade NG None",
    "Mine NG None",
    "Transport NG None",
    "LCOE 50 NG None",
    "LCOH 6 NG None",
    "LCOH 3 NG None",
    "NG 8 NG None",
    "Capex NG None",
    "Baseline NG EAF",
    "Location NG EAF",
    "Ore Grade NG EAF",
    "Mine NG EAF",
    "Transport NG EAF",
    "LCOE 50 NG EAF",
    "LCOH 6 NG EAF",
    "LCOH 3 NG EAF",
    "NG 8 NG EAF",
    "Capex NG EAF",
]
lcois = []

for casename in casenames:
    model = modify_tech_config(model, cases[casename])
    model.run()
    model.post_process()
    lcois.append(float(model.model.get_val("iron.LCOI")[0]))

print(lcois)

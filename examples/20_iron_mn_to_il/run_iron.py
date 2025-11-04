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
    "Case 1",
    "Case 2",
    "Case 3",
    "Case 4",
]
lcois = []

for casename in casenames:
    model = modify_tech_config(model, cases[casename])
    model.run()
    model.post_process()
    lcois.append(float(model.model.get_val("finance_subgroup_iron_mine.price_iron_ore")[0]))

print(lcois)

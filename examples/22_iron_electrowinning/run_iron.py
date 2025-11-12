from pathlib import Path

from h2integrate.tools.run_cases import modify_tech_config, load_tech_config_cases
from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create H2Integrate model
model = H2IntegrateModel("22_iron_electrowinning.yaml")

# Load cases
case_file = Path("test_inputs.csv")
cases = load_tech_config_cases(case_file)

# Modify and run the model for different cases
casenames = [
    "Case 1",
    "Case 2",
    "Case 3",
]
lcois = []

for casename in casenames:
    model = modify_tech_config(model, cases[casename])
    model.run()
    model.post_process()
    lcois.append(float(model.model.get_val("finance_subgroup_hot_iron.price_hot_iron")[0]))

# Compare the LCOIs from iron_wrapper and modular iron
print(lcois)

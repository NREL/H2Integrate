from pathlib import Path

from h2integrate.tools.run_cases import modify_tech_config, load_tech_config_cases
from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a H2Integrate models
model = H2IntegrateModel("20_iron.yaml")
model_modular = H2IntegrateModel("20_iron_modular.yaml")

# Load cases
case_file = Path("test_inputs.csv")
case_file_modular = Path("test_inputs_modular.csv")
cases = load_tech_config_cases(case_file)
cases_modular = load_tech_config_cases(case_file_modular)

# Modify and run the model for different cases
casenames = [
    "Case 1",
    "Case 2",
    "Case 3",
    "Case 4",
]
lcois = []
lcois_modular = []

for casename in casenames:
    model = modify_tech_config(model, cases[casename])
    model_modular = modify_tech_config(model_modular, cases_modular[casename])
    model.run()
    model_modular.run()
    model.post_process()
    model_modular.post_process(
        exclude_other=[
            "*iron_mine_performance",
            "*iron_mine_cost",
            "*iron_plant_performance",
            "*iron_plant_cost",
        ]
    )
    lcois.append(float(model.model.get_val("iron.LCOI")[0]))
    lcois_modular.append(
        float(model_modular.model.get_val("finance_subgroup_pig_iron.price_pig_iron")[0])
    )

print(lcois)
print(lcois_modular)

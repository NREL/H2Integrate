from pathlib import Path

from plot_ammonia_synloop import plot_ammonia

from h2integrate.tools.run_cases import mod_tech_config, load_tech_config_cases
from h2integrate.core.h2integrate_model import H2IntegrateModel


# Create a H2Integrate model
model = H2IntegrateModel("12_ammonia_synloop.yaml")

# Load cases
case_file = Path("test_inputs.csv")
cases = load_tech_config_cases(case_file)

# Modify and run the model for Haber Bosch Big
case = cases["Haber Bosch Big"]
model = mod_tech_config(model, case)
model.run()
model.post_process()
plot_ammonia(model.prob.model)

# Modify and run the model for Haber Bosch Small
case = cases["Haber Bosch Small"]
model = mod_tech_config(model, case)
model.run()
model.post_process()
plot_ammonia(model.prob.model)

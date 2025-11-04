import os
from pathlib import Path

from h2integrate.core.h2integrate_model import H2IntegrateModel


os.chdir(Path(__file__).parent)
# Create an H2I model
h2i = H2IntegrateModel("22_solar_site_doe.yaml")

# Run the model
h2i.run()

# Post-process the results
h2i.post_process()

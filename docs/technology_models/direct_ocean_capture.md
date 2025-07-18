# Direct ocean capture model

The DOC model—short for Direct Ocean Capture—simulates the removal of carbon dioxide (CO₂) from ocean water. In the H2Integrate framework, this technology is implemented as a wrapper around the electrodialysis-based marine carbon capture unit from the [MarineCarbonManagement repository](https://github.com/NREL/MarineCarbonManagement).

The model requires a range of inputs, including parameters for the electrodialysis unit, seawater chemistry, initial operating conditions, and electrical power input to operate the system.

Note that the [MarineCarbonManagement repository](https://github.com/NREL/MarineCarbonManagement) is not available as a pip-installable package on PyPI. As a result, it is not included in the default installation of H2Integrate via pip or through the setup instructions on the H2Integrate GitHub page.

To enable the DOC model in your environment, install the required dependency manually:

```bash
pip install git+https://github.com/NREL/MarineCarbonManagement.git
```

Additional information on the DOC model—including its heuristic operational scenarios, control strategies, and example results—can be found in the publication:

["A Model of Large Scale Electrochemical Direct Ocean Capture Under Variable Power"](https://docs.nrel.gov/docs/fy24osti/90673.pdf)

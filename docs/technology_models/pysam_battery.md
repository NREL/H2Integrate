# PySAM Battery Model

The PySAM battery model in H2Integrate is a simple wrapper. For full documentation see the [PySAM battery model documentation](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html).

The PySAM battery model simulates the response of the battery to control commands. However, it is important for the user to be aware that the control commands may not be strictly followed. Specifically, the SOC bounds have been seen to be exceeded by nearly 4% SOC for the upper bound and close to 1% SOC on the lower bound.

To use the pysam battery model, specify `"pysam_battery"` as the performance model.

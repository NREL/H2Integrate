import numpy as np


def hydrogen_storage_capacity(H2_Results, electrolyzer_size_mw, hydrogen_demand_kgphr):
    """Calculate storage capacity based on hydrogen demand and production.

    Args:
        H2_Results (dict): Dictionary including electrolyzer physics results.
        electrolyzer_size_mw (float): Electrolyzer size in MW.
        hydrogen_demand_kgphr (float): Hydrogen demand in kg/hr.

    Returns:
        hydrogen_demand_kgphr (list): Hydrogen hourly demand in kilograms per hour.
        hydrogen_storage_capacity_kg (float): Hydrogen storage capacity in kilograms.
        hydrogen_storage_duration_hr (float): Hydrogen storage duration in hours using HHV/LHV.
        hydrogen_storage_soc (list): Timeseries of the hydrogen storage state of charge.
    """

    hydrogen_production_kgphr = H2_Results["Hydrogen Hourly Production [kg/hr]"]

    hydrogen_demand_kgphr = max(
        hydrogen_demand_kgphr, np.mean(hydrogen_production_kgphr)
    )  # TODO: potentially add buffer No buffer needed since we are already oversizing

    # TODO: SOC is just an absolute value and is not a percentage. Ideally would calculate as shortfall in future.
    hydrogen_production_kgphr = np.asarray(hydrogen_production_kgphr)
    hydrogen_storage_soc = np.cumsum(hydrogen_production_kgphr - hydrogen_demand_kgphr)

    minimum_soc = np.min(hydrogen_storage_soc)

    # adjust soc so it's not negative.
    if minimum_soc < 0:
        hydrogen_storage_soc = [x + np.abs(minimum_soc) for x in hydrogen_storage_soc]

    hydrogen_storage_capacity_kg = np.max(hydrogen_storage_soc) - np.min(hydrogen_storage_soc)
    h2_LHV = 119.96  # MJ/kg
    h2_HHV = 141.88  # MJ/kg
    hydrogen_storage_capacity_MWh_LHV = hydrogen_storage_capacity_kg * h2_LHV / 3600
    hydrogen_storage_capacity_kg * h2_HHV / 3600

    # Get average electrolyzer efficiency
    electrolyzer_average_efficiency_HHV = H2_Results["Sim: Average Efficiency [%-HHV]"]

    # Calculate storage duration
    hydrogen_storage_duration_hr = (
        hydrogen_storage_capacity_MWh_LHV
        / electrolyzer_size_mw
        / electrolyzer_average_efficiency_HHV
    )

    np.ones_like(hydrogen_storage_capacity_kg) * hydrogen_demand_kgphr

    return (
        np.ones_like(hydrogen_storage_capacity_kg) * hydrogen_demand_kgphr,
        hydrogen_storage_capacity_kg,
        hydrogen_storage_duration_hr,
        hydrogen_storage_soc,
    )

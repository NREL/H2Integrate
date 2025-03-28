def calc_custom_electrolysis_capex_fom(electrolyzer_capacity_kW, electrolyzer_config):
    """Calculates electrolyzer total installed capex and fixed O&M based on user-input values.

    Only used if h2integrate_config["electrolyzer"]["cost_model"] is set to "basic_custom"
    Requires additional inputs in h2integrate_config["electrolyzer"]:
        - fixed_om_per_kw: electrolyzer fixed o&m in $/kW-year
        - electrolyzer_capex: electrolyzer capex in $/kW

    Args:
        electrolyzer_capacity_kW (float or int): electrolyzer capacity in kW
        electrolyzer_config (dict): ``h2integrate_config["electrolyzer"]``

    Returns:
        2-element tuple containing

        - **capex** (float): electrolyzer overnight capex in $
        - **fixed_om** (float): electrolyzer fixed O&M in $/year
    """
    electrolyzer_capex = electrolyzer_config["electrolyzer_capex"] * electrolyzer_capacity_kW
    if "fixed_om_per_kw" in electrolyzer_config.keys():
        electrolyzer_fopex = electrolyzer_config["fixed_om_per_kw"] * electrolyzer_capacity_kW
    else:
        electrolyzer_fopex = 0.0
    return electrolyzer_capex, electrolyzer_fopex

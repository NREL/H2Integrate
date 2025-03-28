from h2integrate.simulation.technologies.steel import steel
from h2integrate.simulation.technologies.ammonia import ammonia
from h2integrate.simulation.technologies.hydrogen.electrolysis import PEM_tools


def size_electrolyzer_for_end_use(h2integrate_config):
    hybrid_electricity_estimated_cf = h2integrate_config["project_parameters"][
        "hybrid_electricity_estimated_cf"
    ]

    if "ammonia" in list(h2integrate_config.keys()):
        feedstocks = ammonia.Feedstocks(
            {
                "electricity_cost": 0,
                "hydrogen_cost": 0,
                "cooling_water_cost": 0,
                "iron_based_catalyst_cost": 0,
                "oxygen_cost": 0,
            }
        )
        config = ammonia.AmmoniaCapacityModelConfig(
            input_capacity_factor_estimate=h2integrate_config["ammonia"]["capacity"][
                "input_capacity_factor_estimate"
            ],
            feedstocks=feedstocks,
            desired_ammonia_kgpy=h2integrate_config["ammonia"]["capacity"][
                "annual_production_target"
            ],
        )
        output = ammonia.run_size_ammonia_plant_capacity(config)

    if "steel" in list(h2integrate_config.keys()):
        feedstocks = steel.Feedstocks(natural_gas_prices={})
        config = steel.SteelCapacityModelConfig(
            input_capacity_factor_estimate=h2integrate_config["steel"]["capacity"][
                "input_capacity_factor_estimate"
            ],
            feedstocks=feedstocks,
            desired_steel_mtpy=h2integrate_config["steel"]["capacity"]["annual_production_target"],
        )
        output = steel.run_size_steel_plant_capacity(config)

    hydrogen_production_capacity_required_kgphr = output.hydrogen_amount_kgpy / (
        8760 * hybrid_electricity_estimated_cf
    )

    deg_power_inc = h2integrate_config["electrolyzer"]["eol_eff_percent_loss"] / 100
    bol_or_eol_sizing = h2integrate_config["electrolyzer"]["sizing"]["size_for"]
    cluster_cap_mw = h2integrate_config["electrolyzer"]["cluster_rating_MW"]
    electrolyzer_capacity_BOL_MW = PEM_tools.size_electrolyzer_for_hydrogen_demand(
        hydrogen_production_capacity_required_kgphr,
        size_for=bol_or_eol_sizing,
        electrolyzer_degradation_power_increase=deg_power_inc,
    )
    electrolyzer_size_mw = PEM_tools.check_capacity_based_on_clusters(
        electrolyzer_capacity_BOL_MW, cluster_cap_mw
    )

    h2integrate_config["electrolyzer"]["rating"] = electrolyzer_size_mw
    h2integrate_config["electrolyzer"]["sizing"]["hydrogen_dmd"] = (
        hydrogen_production_capacity_required_kgphr
    )

    return h2integrate_config


def run_resizing_estimation(h2integrate_config):
    if h2integrate_config["project_parameters"]["hybrid_electricity_estimated_cf"] > 1:
        msg = (
            "hybrid plant capacity factor estimate (hybrid_electricity_estimated_cf) cannot"
            " exceed 1."
        )
        raise ValueError(msg)

    if h2integrate_config["project_parameters"]["grid_connection"]:
        if h2integrate_config["project_parameters"]["hybrid_electricity_estimated_cf"] < 1:
            print("hybrid_electricity_estimated_cf reset to 1 for grid-connected cases")
            h2integrate_config["project_parameters"]["hybrid_electricity_estimated_cf"] = 1

    if h2integrate_config["electrolyzer"]["sizing"]["resize_for_enduse"]:
        h2integrate_config = size_electrolyzer_for_end_use(h2integrate_config)

    return h2integrate_config

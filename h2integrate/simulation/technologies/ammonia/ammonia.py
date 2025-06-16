from attrs import define


@define
class AmmoniaCostModelConfig:
    """
    Configuration inputs for the ammonia cost model, including plant capacity and
    feedstock details.

    Attributes:
        plant_capacity_kgpy (float): Annual production capacity of the plant in kg.
        plant_capacity_factor (float): The ratio of actual production to maximum
            possible production over a year.
        electricity_cost (float): Cost per MWh of electricity.
        hydrogen_cost (float): Cost per kg of hydrogen.
        cooling_water_cost (float): Cost per gallon of cooling water.
        iron_based_catalyst_cost (float): Cost per kg of iron-based catalyst.
        oxygen_cost (float): Cost per kg of oxygen.
        electricity_consumption (float): Electricity consumption in MWh per kg of
            ammonia production, default is 0.1207 / 1000.
        hydrogen_consumption (float): Hydrogen consumption in kg per kg of ammonia
            production, default is 0.197284403.
        cooling_water_consumption (float): Cooling water consumption in gallons per
            kg of ammonia production, default is 0.049236824.
        iron_based_catalyst_consumption (float): Iron-based catalyst consumption in kg
            per kg of ammonia production, default is 0.000091295354067341.
        oxygen_byproduct (float): Oxygen byproduct in kg per kg of ammonia production,
            default is 0.29405077250145.
    """

    plant_capacity_kgpy: float
    plant_capacity_factor: float
    electricity_cost: float
    hydrogen_cost: float
    cooling_water_cost: float
    iron_based_catalyst_cost: float
    oxygen_cost: float
    electricity_consumption: float = 0.1207 / 1000
    hydrogen_consumption = 0.197284403
    cooling_water_consumption = 0.049236824
    iron_based_catalyst_consumption = 0.000091295354067341
    oxygen_byproduct = 0.29405077250145


@define
class AmmoniaCosts:
    """
    Base dataclass for calculated costs related to ammonia production, including
    capital expenditures (CapEx) and operating expenditures (OpEx).

    Attributes:
        capex_air_separation_cryogenic (float): Capital cost for air separation.
        capex_haber_bosch (float): Capital cost for the Haber-Bosch process.
        capex_boiler (float): Capital cost for boilers.
        capex_cooling_tower (float): Capital cost for cooling towers.
        capex_direct (float): Direct capital costs.
        capex_depreciable_nonequipment (float): Depreciable non-equipment capital costs.
        land_cost (float): Cost of land.
        labor_cost (float): Annual labor cost.
        general_administration_cost (float): Annual general and administrative cost.
        property_tax_insurance (float): Annual property tax and insurance cost.
        maintenance_cost (float): Annual maintenance cost.
        total_fixed_operating_cost (float): Total annual fixed operating cost.
        H2_cost_in_startup_year (float): Hydrogen cost in the startup year.
        energy_cost_in_startup_year (float): Energy cost in the startup year.
        non_energy_cost_in_startup_year (float): Non-energy cost in the startup year.
        variable_cost_in_startup_year (float): Variable cost in the startup year.
        credits_byproduct (float): Credits from byproducts.
    """

    # CapEx
    capex_air_separation_cryogenic: float
    capex_haber_bosch: float
    capex_boiler: float
    capex_cooling_tower: float
    capex_direct: float
    capex_depreciable_nonequipment: float
    land_cost: float

    # Fixed OpEx
    labor_cost: float
    general_administration_cost: float
    property_tax_insurance: float
    maintenance_cost: float
    total_fixed_operating_cost: float

    # Feedstock and Byproduct costs
    H2_cost_in_startup_year: float
    energy_cost_in_startup_year: float
    non_energy_cost_in_startup_year: float
    variable_cost_in_startup_year: float
    credits_byproduct: float


@define
class AmmoniaCostModelOutputs(AmmoniaCosts):
    """
    Outputs from the ammonia cost model, extending `AmmoniaCosts` with total capital
    expenditure calculations.

    Attributes:
        capex_total (float): The total capital expenditure for the ammonia plant.
    """

    # CapEx
    capex_total: float


def run_ammonia_model(plant_capacity_kgpy: float, plant_capacity_factor: float) -> float:
    """
    Calculates the annual ammonia production in kilograms based on the plant's
    capacity and its capacity factor.

    Args:
        plant_capacity_kgpy (float): The plant's annual capacity in kilograms per year.
        plant_capacity_factor (float): The capacity factor of the plant, a ratio of
            its actual output over a period of time to its potential output if it
            were possible for it to operate at full capacity continuously over the
            same period.

    Returns:
        float: The calculated annual ammonia production in kilograms per year.
    """
    ammonia_production_kgpy = plant_capacity_kgpy * plant_capacity_factor

    return ammonia_production_kgpy


def run_ammonia_cost_model(config: AmmoniaCostModelConfig) -> AmmoniaCostModelOutputs:
    """
    Calculates the various costs associated with ammonia production, including
    capital expenditures (CapEx), operating expenditures (OpEx), and credits from
    byproducts, based on the provided configuration settings.

    Args:
        config (AmmoniaCostModelConfig): Configuration object containing all necessary
            parameters for the cost calculation, including plant capacity, capacity
            factor, and feedstock costs.

    Returns:
        AmmoniaCostModelOutputs: Object containing detailed breakdowns of calculated
            costs, including total capital expenditure, operating costs, and credits
            from byproducts.
    """
    model_year_CEPCI = 816.0  # 2022
    equation_year_CEPCI = 541.7  # 2016

    # scale with respect to a baseline plant (What is this?)
    scaling_ratio = config.plant_capacity_kgpy / (365.0 * 1266638.4)

    # -------------------------------CapEx Costs------------------------------
    scaling_factor_equipment = 0.6

    capex_scale_factor = scaling_ratio**scaling_factor_equipment
    capex_air_separation_cryogenic = (
        model_year_CEPCI / equation_year_CEPCI * 22506100 * capex_scale_factor
    )
    capex_haber_bosch = model_year_CEPCI / equation_year_CEPCI * 18642800 * capex_scale_factor
    capex_boiler = model_year_CEPCI / equation_year_CEPCI * 7069100 * capex_scale_factor
    capex_cooling_tower = model_year_CEPCI / equation_year_CEPCI * 4799200 * capex_scale_factor
    capex_direct = (
        capex_air_separation_cryogenic + capex_haber_bosch + capex_boiler + capex_cooling_tower
    )
    capex_depreciable_nonequipment = capex_direct * 0.42 + 4112701.84103543 * scaling_ratio
    capex_total = capex_direct + capex_depreciable_nonequipment
    land_cost = capex_depreciable_nonequipment  # TODO: determine if this is the right method or the one in Fixed O&M costs

    # -------------------------------Fixed O&M Costs------------------------------
    scaling_factor_labor = 0.25
    labor_cost = 57 * 50 * 2080 * scaling_ratio**scaling_factor_labor
    general_administration_cost = labor_cost * 0.2
    property_tax_insurance = capex_total * 0.02
    maintenance_cost = capex_direct * 0.005 * scaling_ratio**scaling_factor_equipment
    land_cost = 2500000 * capex_scale_factor
    total_fixed_operating_cost = (
        land_cost
        + labor_cost
        + general_administration_cost
        + property_tax_insurance
        + maintenance_cost
    )

    # -------------------------------Feedstock Costs------------------------------
    H2_cost_in_startup_year = (
        config.hydrogen_cost
        * config.hydrogen_consumption
        * config.plant_capacity_kgpy
        * config.plant_capacity_factor
    )
    energy_cost_in_startup_year = (
        config.electricity_cost
        * config.electricity_consumption
        * config.plant_capacity_kgpy
        * config.plant_capacity_factor
    )
    non_energy_cost_in_startup_year = (
        (
            (config.cooling_water_cost * config.cooling_water_consumption)
            + (config.iron_based_catalyst_cost * config.iron_based_catalyst_consumption)
        )
        * config.plant_capacity_kgpy
        * config.plant_capacity_factor
    )
    variable_cost_in_startup_year = energy_cost_in_startup_year + non_energy_cost_in_startup_year
    # -------------------------------Byproduct Costs------------------------------
    credits_byproduct = (
        config.oxygen_cost
        * config.oxygen_byproduct
        * config.plant_capacity_kgpy
        * config.plant_capacity_factor
    )

    return AmmoniaCostModelOutputs(
        # Capex
        capex_air_separation_cryogenic=capex_air_separation_cryogenic,
        capex_haber_bosch=capex_haber_bosch,
        capex_boiler=capex_boiler,
        capex_cooling_tower=capex_cooling_tower,
        capex_direct=capex_direct,
        capex_depreciable_nonequipment=capex_depreciable_nonequipment,
        capex_total=capex_total,
        land_cost=land_cost,
        # Fixed OpEx
        labor_cost=labor_cost,
        general_administration_cost=general_administration_cost,
        property_tax_insurance=property_tax_insurance,
        maintenance_cost=maintenance_cost,
        total_fixed_operating_cost=total_fixed_operating_cost,
        # Feedstock & Byproducts
        H2_cost_in_startup_year=H2_cost_in_startup_year,
        energy_cost_in_startup_year=energy_cost_in_startup_year,
        non_energy_cost_in_startup_year=non_energy_cost_in_startup_year,
        variable_cost_in_startup_year=variable_cost_in_startup_year,
        credits_byproduct=credits_byproduct,
    )

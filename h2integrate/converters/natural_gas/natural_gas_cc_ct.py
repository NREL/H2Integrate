import openmdao.api as om
from attrs import field, define

from h2integrate.core.utilities import BaseConfig, CostModelBaseConfig, merge_shared_inputs
from h2integrate.core.validators import gt_zero
from h2integrate.core.model_baseclasses import CostModelBaseClass


n_timesteps = 8760


@define
class NaturalGasPerformanceConfig(BaseConfig):
    """
    Configuration class for natural gas plant performance model.

    This configuration class handles the parameters for both natural gas
    combustion turbines (NGCT) and natural gas combined cycle (NGCC) plants.

    Attributes:
        heat_rate (float): Heat rate of the natural gas plant in MMBtu/MWh.
            This represents the amount of fuel energy required to produce
            one MWh of electricity. Lower values indicate higher efficiency.
            Typical values:
            - NGCT: 10-14 MMBtu/MWh
            - NGCC: 6-8 MMBtu/MWh
    """

    heat_rate: float = field(validator=gt_zero)


class NaturalGasPerformanceModel(om.ExplicitComponent):
    """
    Performance model for natural gas power plants.

    This model calculates electricity output from natural gas input based on
    the plant's heat rate. It can be used for both natural gas combustion
    turbines (NGCT) and natural gas combined cycle (NGCC) plants by providing
    appropriate heat rate values.

    The model implements the relationship:
        electricity_out = natural_gas_in / heat_rate

    Inputs:
        natural_gas_in (array): Natural gas input energy in MMBtu for each timestep

    Outputs:
        electricity_out (array): Electricity output in MW for each timestep

    Parameters (from config):
        heat_rate (float): Plant heat rate in MMBtu/MWh
    """

    def initialize(self):
        self.options.declare("driver_config", types=dict)
        self.options.declare("plant_config", types=dict)
        self.options.declare("tech_config", types=dict)

    def setup(self):
        self.config = NaturalGasPerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )

        # Add natural gas input
        self.add_input(
            "natural_gas_in",
            val=0.0,
            shape=n_timesteps,
            units="MMBtu",
            desc="Natural gas input energy",
        )

        # Add electricity output
        self.add_output(
            "electricity_out",
            val=0.0,
            shape=n_timesteps,
            units="MW",
            desc="Electricity output from natural gas plant",
        )

        # Add heat_rate as an OpenMDAO input with config value as default
        self.add_input(
            "heat_rate",
            val=self.config.heat_rate,
            units="MMBtu/MW/h",
            desc="Plant heat rate in MMBtu/MWh",
        )

    def compute(self, inputs, outputs):
        """
        Compute electricity output from natural gas input.

        The computation uses the heat rate to convert natural gas energy input
        to electrical energy output. The heat rate represents the fuel energy
        required per unit of electrical energy produced.

        Args:
            inputs: OpenMDAO inputs object containing natural_gas_in and heat_rate
            outputs: OpenMDAO outputs object for electricity_out
        """
        natural_gas_in = inputs["natural_gas_in"]
        heat_rate = inputs["heat_rate"][0]

        # Convert natural gas input to electricity output using heat rate
        # electricity_out [MW] = natural_gas_in [MMBtu] / heat_rate [MMBtu/MWh]
        # Note: This assumes hourly timesteps, so MWh = MW for hourly data
        electricity_out = natural_gas_in / heat_rate

        outputs["electricity_out"] = electricity_out


@define
class NaturalGasCostModelConfig(CostModelBaseConfig):
    """
    Configuration class for natural gas plant cost model.

    This configuration handles cost parameters for both natural gas combustion
    turbines (NGCT) and natural gas combined cycle (NGCC) plants.

    Attributes:
        capex (float|int): Capital cost per unit capacity in $/kW. This includes
            all equipment, installation, and construction costs.
            Typical values:
            - NGCT: 600-1000 $/kW
            - NGCC: 800-1200 $/kW

        fopex (float|int): Fixed operating expenses per unit capacity in $/kW/year.
            This includes fixed O&M costs that don't vary with generation.
            Typical values: 5-15 $/kW/year

        vopex (float|int): Variable operating expenses per unit generation in $/MWh.
            This includes variable O&M costs that scale with electricity generation.
            Typical values: 1-5 $/MWh

        heat_rate (float): Heat rate in MMBtu/MWh, used for fuel cost calculations.
            This should match the heat rate used in the performance model.

        ng_price (float|str): Natural gas price in $/MMBtu.
            Can be a numeric value for fixed price or "variable" string to
            indicate external price management.

        project_life (int): Project lifetime in years for cost calculations.
            Default is 30 years, typical for power plants.

        cost_year (int): Dollar year corresponding to input costs.
    """

    capex: float | int = field(validator=gt_zero)
    fopex: float | int = field(validator=gt_zero)
    vopex: float | int = field(validator=gt_zero)
    heat_rate: float = field(validator=gt_zero)
    ng_price: float | str = field()
    project_life: int = field(default=30, validator=gt_zero)


class NaturalGasCostModel(CostModelBaseClass):
    """
    Cost model for natural gas power plants.

    This model calculates capital and operating costs for natural gas plants
    including fuel costs. It can be used for both NGCT and NGCC plants.

    The model calculates:
    - CapEx: Capital expenditure based on plant capacity
    - OpEx: Operating expenditure including fixed O&M, variable O&M, and fuel costs

    Cost components:
    1. Capital costs: capex * plant_capacity_kW
    2. Fixed O&M: fopex * plant_capacity_kW * project_life
    3. Variable O&M: vopex * delivered_electricity_MWh * project_life
    4. Fuel costs: ng_price * heat_rate * delivered_electricity_MWh * project_life

    Inputs:
        plant_capacity_kW (float): Plant capacity in kW
        delivered_electricity_MWh (float): Annual electricity generation in MWh
        capex (float): Capital cost per unit capacity in $/kW
        fopex (float): Fixed operating expenses per unit capacity in $/kW/year
        vopex (float): Variable operating expenses per unit generation in $/MWh
        heat_rate (float): Heat rate in MMBtu/MWh
        ng_price (float): Natural gas price in $/MMBtu
        project_life (int): Project lifetime in years

    Outputs:
        CapEx (float): Total capital expenditure in USD
        OpEx (float): Total operating expenditure over project life in USD
        cost_year (int): Dollar year for the costs
    """

    def setup(self):
        self.config = NaturalGasCostModelConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "cost")
        )

        super().setup()

        # Add inputs specific to the cost model with config values as defaults
        self.add_input("plant_capacity_kW", val=0.0, units="kW", desc="Natural gas plant capacity")
        self.add_input(
            "delivered_electricity_MWh", val=0.0, units="MW*h", desc="Annual electricity generation"
        )
        self.add_input(
            "capex", val=self.config.capex, units="USD/kW", desc="Capital cost per unit capacity"
        )
        self.add_input(
            "fopex",
            val=self.config.fopex,
            units="USD/kW/year",
            desc="Fixed operating expenses per unit capacity per year",
        )
        self.add_input(
            "vopex",
            val=self.config.vopex,
            units="USD/MW/h",
            desc="Variable operating expenses per unit generation",
        )
        self.add_input(
            "heat_rate", val=self.config.heat_rate, units="MMBtu/MW/h", desc="Plant heat rate"
        )
        # Handle ng_price - only add as input if it's not "variable"
        if self.config.ng_price != "variable":
            self.add_input(
                "ng_price", val=self.config.ng_price, units="USD/MMBtu", desc="Natural gas price"
            )
        self.add_input(
            "project_life", val=self.config.project_life, units="year", desc="Project lifetime"
        )

    def compute(self, inputs, outputs, discrete_inputs, discrete_outputs):
        """
        Compute capital and operating costs for the natural gas plant.

        This method implements the cost calculation logic, computing
        capital costs, fixed O&M, variable O&M, and fuel costs over the project
        lifetime.

        Args:
            inputs: OpenMDAO inputs containing all cost parameters
            outputs: OpenMDAO outputs for CapEx and OpEx
            discrete_inputs: OpenMDAO discrete inputs (unused)
            discrete_outputs: OpenMDAO discrete outputs for cost_year
        """
        plant_capacity_kW = inputs["plant_capacity_kW"][0]
        delivered_electricity_MWh = inputs["delivered_electricity_MWh"][0]
        capex_per_kw = inputs["capex"][0]
        fopex_per_kw_year = inputs["fopex"][0]
        vopex_per_mwh = inputs["vopex"][0]
        heat_rate = inputs["heat_rate"][0]
        project_life = inputs["project_life"][0]

        # Calculate capital expenditure
        capex = capex_per_kw * plant_capacity_kW

        # Calculate fixed operating expenses over project life
        fixed_om = fopex_per_kw_year * plant_capacity_kW * project_life

        # Calculate variable operating expenses over project life
        variable_om = vopex_per_mwh * delivered_electricity_MWh * project_life

        # Calculate fuel costs over project life
        if self.config.ng_price == "variable":
            # If price is variable, set fuel cost to 0 (handled externally)
            fuel_cost = 0.0
        else:
            # Natural gas price is now in $/MMBtu, no conversion needed
            ng_price = inputs["ng_price"][0]
            fuel_cost = ng_price * heat_rate * delivered_electricity_MWh * project_life

        # Total operating expenditure includes all O&M and fuel costs
        opex = fixed_om + variable_om + fuel_cost

        outputs["CapEx"] = capex
        outputs["OpEx"] = opex

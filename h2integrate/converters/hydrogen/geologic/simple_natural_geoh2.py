import numpy as np
from attrs import field, define

from h2integrate.core.utilities import merge_shared_inputs
from h2integrate.converters.hydrogen.geologic.h2_well_subsurface_baseclass import (
    GeoH2SubsurfacePerformanceConfig,
    GeoH2SubsurfacePerformanceBaseClass,
)


@define
class NaturalGeoH2PerformanceConfig(GeoH2SubsurfacePerformanceConfig):
    """Configuration for performance parameters for a natural geologic hydrogen subsurface well.
    This class defines performance parameters specific to **natural** geologic hydrogen
    systems (as opposed to stimulated systems).

    Inherits from:
        GeoH2SubsurfacePerformanceConfig

    Attributes:
        site_prospectivity (float):
            Dimensionless site assessment factor representing the natural hydrogen
            production potential of the location.

        initial_wellhead_flow (float):
            Hydrogen flow rate measured immediately after well completion, in kilograms
            per hour (kg/h).

        gas_reservoir_size (float):
            Total amount of hydrogen stored in the geologic accumulation, in tonnes (t).
    """

    site_prospectivity: float = field()
    initial_wellhead_flow: float = field()
    gas_reservoir_size: float = field()


class NaturalGeoH2PerformanceModel(GeoH2SubsurfacePerformanceBaseClass):
    """OpenMDAO component for modeling the performance of a subsurface well for a
        natural geologic hydrogen plant.

    This component estimates hydrogen production performance for **naturally occurring**
    geologic hydrogen systems.

    The modeling approach is informed by the following studies:
        - Mathur et al. (Stanford): https://doi.org/10.31223/X5599G
        - Gelman et al. (USGS): https://doi.org/10.3133/pp1900

    Attributes:
        config (NaturalGeoH2PerformanceConfig):
            Configuration object containing model parameters specific to natural geologic
            hydrogen systems.

    Inputs:
        site_prospectivity (float):
            Dimensionless measure of natural hydrogen production potential at a given site.

        initial_wellhead_flow (float):
            Hydrogen flow rate immediately after well completion, in kilograms per hour (kg/h).

        gas_reservoir_size (float):
            Total mass of hydrogen stored in the subsurface accumulation, in tonnes (t).

        well_lifetime (float):
            Duration of well operation, in years (inherited from base class).

        grain_size (float):
            Rock grain size influencing hydrogen diffusion and reaction rates, in meters
            (inherited from base class).

    Outputs:
        wellhead_h2_conc (float):
            Mass percentage of hydrogen in the wellhead gas mixture.

        lifetime_wellhead_flow (float):
            Average gas flow rate over the operational lifetime of the well, in kg/h.

        hydrogen_out_natural (ndarray):
            Hourly hydrogen production profile from natural accumulations,
            covering one simulated year (8760 hours), in kg/h.

        hydrogen_out (ndarray):
            Total hydrogen output array used by downstream system models, in kg/h.
    """

    def setup(self):
        self.config = NaturalGeoH2PerformanceConfig.from_dict(
            merge_shared_inputs(self.options["tech_config"]["model_inputs"], "performance")
        )
        super().setup()
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]

        self.add_input("site_prospectivity", units=None, val=self.config.site_prospectivity)
        self.add_input("initial_wellhead_flow", units="kg/h", val=self.config.initial_wellhead_flow)
        self.add_input("gas_reservoir_size", units="t", val=self.config.gas_reservoir_size)

        self.add_output("wellhead_h2_conc", units="percent")
        self.add_output("lifetime_wellhead_flow", units="kg/h")
        self.add_output("hydrogen_out_natural", units="kg/h", shape=(n_timesteps,))

    def compute(self, inputs, outputs):
        if self.config.rock_type == "peridotite":  # TODO: sub-models for different rock types
            # Calculate expected wellhead h2 concentration from prospectivity
            prospectivity = inputs["site_prospectivity"]
            wh_h2_conc = 58.92981751 * prospectivity**2.460718753  # percent

        # Calculated average wellhead gas flow over well lifetime
        init_wh_flow = inputs["initial_wellhead_flow"]
        lifetime = int(inputs["well_lifetime"][0])
        res_size = inputs["gas_reservoir_size"]
        n_timesteps = self.options["plant_config"]["plant"]["simulation"]["n_timesteps"]
        avg_wh_flow = min(init_wh_flow, res_size / lifetime * 1000 / n_timesteps)

        # Calculate hydrogen flow out from accumulated gas
        h2_accum = wh_h2_conc / 100 * avg_wh_flow

        # Parse outputs
        outputs["wellhead_h2_conc"] = wh_h2_conc
        outputs["lifetime_wellhead_flow"] = avg_wh_flow
        outputs["hydrogen_out_natural"] = np.full(n_timesteps, h2_accum)
        outputs["hydrogen_out"] = np.full(n_timesteps, h2_accum)


# class NaturalGeoH2FinanceModel(GeoH2FinanceBaseClass):
#     """
#     An OpenMDAO component for modeling the financing of a natural geologic hydrogen plant
#     Based on the work of:
#         - Mathur et al. (Stanford): https://eartharxiv.org/repository/view/8321/
#         - NETL Quality Guidelines: https://doi.org/10.2172/1567736


#     All inputs come from NaturalGeoH2FinanceConfig, except for inputs in *asterisks* which come
#         from NaturalGeoH2PerformanceModel or NaturalGeoH2CostModel outputs

#     Currently no inputs/outputs other than those in geoh2_baseclass.GeoH2FinanceBaseClass
#     """

#     def setup(self):
#         self.config = GeoH2FinanceConfig.from_dict(
#             merge_shared_inputs(self.options["tech_config"]["model_inputs"], "finance")
#         )
#         super().setup()

#     def compute(self, inputs, outputs):
#         # Calculate fixed charge rate
#         lifetime = int(inputs["well_lifetime"][0])
#         etr = inputs["eff_tax_rate"] / 100
#         atwacc = inputs["atwacc"] / 100
#         dep_n = 1 / lifetime  # simplifying the IRS tax depreciation tables to avoid lookup
#         crf = (
#             atwacc * (1 + atwacc) ** lifetime / ((1 + atwacc) ** lifetime - 1)
#         )  # capital recovery factor
#         dep = crf * np.sum(dep_n / np.power(1 + atwacc, np.linspace(1, lifetime, lifetime)))
#         fcr = crf / (1 - etr) - etr * dep / (1 - etr)

#         # Calculate levelized cost of geoH2
#         capex = inputs["CapEx"]
#         fopex = inputs["Fixed_OpEx"]
#         vopex = inputs["Variable_OpEx"]
#         production = np.sum(inputs["hydrogen_out"])
#         lcoh = (capex * fcr + fopex) / production + vopex
#         outputs["LCOH"] = lcoh
#         outputs["LCOH_capex"] = (capex * fcr) / production
#         outputs["LCOH_fopex"] = fopex / production
#         outputs["LCOH_vopex"] = vopex

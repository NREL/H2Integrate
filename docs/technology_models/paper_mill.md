Paper mill model

The paper mill model represents the production and costs of paper, pulp, and lignin at an integrated paper mill. The model calculates production from the mill’s annual nameplate capacity and capacity factor. Paper is the primary product, while pulp and lignin are additional output streams that can be used by other technologies in an H2Integrate plant configuration.

The model is implemented in h2integrate/converters/paper_mill/. An example integrating the paper mill with a sustainable aviation fuel plant is provided in examples/37_paper_mill/.

The annual paper production is calculated as plant_capacity_mtpy × capacity_factor. The model assumes that pulp production is 1.1 tonnes per tonne of paper and that lignin production is 6% of paper production by mass. The resulting hourly profiles are exposed as paper_out, pulp_out, and lignin_out.

The paper mill cost model calculates capital expenditures, fixed operating expenditures, and variable operating expenditures. Capital expenditures are proportional to the mill’s nameplate capacity. Fixed operating costs include capacity-dependent expenses and property tax and insurance. Variable operating costs include wood, raw water, electricity, wastewater disposal, calcium carbonate, sodium sulfide, sodium hydroxide, chlorine dioxide, hydrogen peroxide, magnesium sulfate, oxygen, and applicable transportation costs. The default cost assumptions use a 2023 cost year and can be replaced with project-specific values through the technology configuration.

Lignin output

The paper mill exposes lignin as an hourly commodity stream named lignin_out, with units of kg/h. This stream can be connected to a downstream technology requiring a lignin_in input.

For example, the following plant-level interconnection supplies paper mill lignin to a sustainable aviation fuel plant:

technology_interconnections:
  - [paper_mill, saf, lignin, pipe]

For this connection, H2Integrate associates the lignin commodity with the paper mill’s lignin_out output and the SAF plant’s lignin_in input. Assuming that the selected connection model does not introduce material losses, the delivered lignin profile satisfies:

saf.lignin_in = paper_mill.lignin_out

The lignin stream is represented as a time-dependent profile. Consequently, changes in paper mill capacity or capacity factor affect both lignin availability and the operation of connected lignin-consuming technologies.

The current paper mill model uses constant production ratios and does not represent startup, shutdown, ramping, minimum operating loads, intermediate product storage, or changes in product yield.

# Wind Plant - Ard

The intent of [Ard](https://github.com/WISDEM/Ard) is to be a modular, full-stack multi-disciplinary optimization tool for wind farms. By incorporating Ard in H2Integrate, we are able to draw on many wind technology models developed at NREL and other institutions without managing them or their connections in Ard. Models connected in Ard include many parts of [WISDEM](https://github.com/WISDEM/WISDEM), [FLORIS](https://github.com/NREL/floris), and [OptiWindNet](https://github.com/DTUWindEnergy/OptiWindNet). Ard also provides constraint functions and wind farm layout generation capabilities among other things. Because Ard has been developed in a modular way, you may extend Ard fairly easily to include other wind models of interest.

Ard is included in H2Integrate as an [OpenMDAO sub-model](https://openmdao.org/newdocs/versions/latest/features/building_blocks/components/submodel_comp.html), which means that Ard is treated as an OpenMDAO system within an OpenMDAO system. In this way, the user can run an independent wind farm optimization within Ard, or allow H2Integrate to manage the wind farm design variables directly. The drawback of including Ard as a sub-model is that N2 diagrams made from the H2Integrate problems will show Ard only as a single model, rather than showing all the subsystems within Ard. IF you wish to view an N2 diagram of Ard, you will need to use the Ard problem instead.

## Wind Resource
The wind resource capabilities of H2Integrate are not yet connected with Ard, so the user must provide a wind resource file directly to the Ard model inputs.

## Examples
For an example of using Ard in an H2Integrate model, see `examples/xx_wind_ard`. Note that Ard uses a combination of input files, including a [wind IO](https://github.com/IEAWindSystems/windIO) file.

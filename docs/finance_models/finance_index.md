
(finance:overview)=
# Finance Models Overview

**General finance models** compute finance metrics and are not specific to individual technologies.
These models live in the `h2integrate/finances/` folder and accept `driver_config`, `tech_config`, `plant_config`, `commodity_type`, and a `description` as the inputs and options.

- `driver_config` (dict): the `folder_outputs` specified here may be used by the finance model if the finance model outputs data to a file.
- `tech_config` (dict): the technology configs for the technologies to include in the finance calculations
- `plant_config` (dict): contains the `finance_parameters` for the finance model (see [Finance Parameters](financeparameters:specifiyingfinanceparameters)).
- `commodity_type` (str): the name of the commodity to use in the finance calculation.
- `description` (str, optional): an additional description to use for naming outputs of the finance model.

```{note}
The `commodity_type` and `description` are used in the finance model naming convention. Specifics on the output naming convention for each finance model can be found in their docs.
```

(finance:supportedmodels)=
## Currently supported general finance models

- [``ProFastComp``](profastcomp:profastcompmodel): calculates levelized cost of commodity using ProFAST.

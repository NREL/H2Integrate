
(finance:overview)=
# Finance Models Overview

**General finance models** are not technology specific finance models. These models live in the `h2integrate/finances/` folder. These models accept `driver_config`, `tech_config`, `plant_config`, `commodity_type`, and a `description` as the inputs and options.

- `driver_config` (dict): the `folder_outputs` specified here may be used by the finance model if the finance model outputs data to a file.
- `tech_config` (dict): the technology configs for the technologies to include in the finance calculations
- `plant_config` (dict): contains the `model_inputs` for the finance model.
- `commodity_type` (str): the name of the commodity to use in the finance calculation.
- `description` (str, optional): an additional description to use for naming outputs of the finance model.

```{note}
The `commodity_type` and `description` are used in the finance model naming convention. Specifics on the output naming convention for each finance model can be found in their docs.
```

```{note}
The `tech_config` and `plant_config` may be reformatted from their original format within `H2IntegrateModel` when creating the finance models.
```

(finance:supportedmodels)=
## Currently supported general finance models

- [``"ProFastComp"``](profastcomp:profastcompmodel): calculates levelized cost of commodity using ProFAST.

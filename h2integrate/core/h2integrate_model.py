import importlib.util
from pathlib import Path

import yaml
import numpy as np
import openmdao.api as om

from h2integrate.core.finances import ProFastComp, AdjustedCapexOpexComp
from h2integrate.core.utilities import create_xdsm_from_config
from h2integrate.core.feedstocks import FeedstockComponent
from h2integrate.core.resource_summer import ElectricitySumComp
from h2integrate.core.supported_models import supported_models, electricity_producing_techs
from h2integrate.core.inputs.validation import load_tech_yaml, load_plant_yaml, load_driver_yaml
from h2integrate.core.pose_optimization import PoseOptimization


try:
    import pyxdsm
except ImportError:
    pyxdsm = None


class H2IntegrateModel:
    def __init__(self, config_file):
        # read in config file; it's a yaml dict that looks like this:
        self.load_config(config_file)

        # load in supported models
        self.supported_models = supported_models.copy()

        # load custom models
        self.collect_custom_models()

        self.prob = om.Problem()
        self.model = self.prob.model

        # create site-level model
        # this is an OpenMDAO group that contains all the site information
        self.create_site_model()

        # create plant-level model
        # this is an OpenMDAO group that contains all the technologies
        # it will need plant_config but not driver or tech config
        self.create_plant_model()

        # create technology models
        # these are OpenMDAO groups that contain all the components for each technology
        # they will need tech_config but not driver or plant config
        self.create_technology_models()

        self.create_financial_model()

        # connect technologies
        # technologies are connected within the `technology_interconnections` section of the
        # plant config
        self.connect_technologies()

        # create driver model
        # might be an analysis or optimization
        self.create_driver_model()

    def load_config(self, config_file):
        config_path = Path(config_file)
        with config_path.open() as file:
            config = yaml.safe_load(file)

        self.name = config.get("name")
        self.system_summary = config.get("system_summary")

        # Load each config file as yaml and save as dict on this object
        self.driver_config = load_driver_yaml(config_path.parent / config.get("driver_config"))
        self.tech_config_path = config_path.parent / config.get("technology_config")
        self.technology_config = load_tech_yaml(self.tech_config_path)
        self.plant_config = load_plant_yaml(config_path.parent / config.get("plant_config"))

    def collect_custom_models(self):
        """
        Collect custom models from the technology configuration.

        This method loads custom models from the specified directory and adds them to the
        supported models dictionary.
        """

        for tech_name, tech_config in self.technology_config["technologies"].items():
            for model_type in ["performance_model", "cost_model", "financial_model"]:
                if model_type in tech_config:
                    model_name = tech_config[model_type].get("model")
                    if (model_name not in self.supported_models) and (model_name is not None):
                        model_class_name = tech_config[model_type].get("model_class_name")
                        model_location = tech_config[model_type].get("model_location")

                        if not model_class_name or not model_location:
                            raise ValueError(
                                f"Custom {model_type} for {tech_name} must specify "
                                "'model_class_name' and 'model_location'."
                            )

                        # Resolve the full path of the model location
                        model_path = self.tech_config_path.parent / model_location

                        if not model_path.exists():
                            raise FileNotFoundError(
                                f"Custom model location {model_path} does not exist."
                            )

                        # Dynamically import the custom model class
                        spec = importlib.util.spec_from_file_location(model_class_name, model_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        custom_model_class = getattr(module, model_class_name)

                        # Add the custom model to the supported models dictionary
                        self.supported_models[model_name] = custom_model_class

                    else:
                        if (
                            tech_config[model_type].get("model_class_name") is not None
                            or tech_config[model_type].get("model_location") is not None
                        ):
                            msg = (
                                f"Custom model_class_name or model_location "
                                f"specified for '{model_name}', "
                                f"but '{model_name}' is a built-in H2Integrate "
                                "model. Using built-in model instead is not allowed. "
                                f"If you want to use a custom model, please rename it "
                                "in your configuration."
                            )
                            raise ValueError(msg)

    def create_site_model(self):
        site_group = om.Group()

        # Create a site-level component
        site_config = self.plant_config.get("site", {})
        site_component = om.IndepVarComp()
        site_component.add_output("latitude", val=site_config.get("latitude", 0.0))
        site_component.add_output("longitude", val=site_config.get("longitude", 0.0))
        site_component.add_output("elevation_m", val=site_config.get("elevation_m", 0.0))
        site_component.add_output("time_zone", val=site_config.get("time_zone", 0))

        # Add boundaries if they exist
        site_config = self.plant_config.get("site", {})
        boundaries = site_config.get("boundaries", [])
        for i, boundary in enumerate(boundaries):
            site_component.add_output(f"boundary_{i}_x", val=np.array(boundary.get("x", [])))
            site_component.add_output(f"boundary_{i}_y", val=np.array(boundary.get("y", [])))

        site_group.add_subsystem("site_component", site_component, promotes=["*"])

        # Add the site resource component
        if "resources" in site_config:
            for resource_name, resource_config in site_config["resources"].items():
                resource_class = self.supported_models.get(resource_name)
                if resource_class:
                    resource_component = resource_class(
                        filename=resource_config.get("filename"),
                    )
                    site_group.add_subsystem(resource_name, resource_component)

        self.model.add_subsystem("site", site_group, promotes=["*"])

    def create_plant_model(self):
        """
        Create the plant-level model.

        This method creates an OpenMDAO group that contains all the technologies.
        It uses the plant configuration but not the driver or technology configuration.

        Information at this level might be used by any technology and info stored here is
        the same for each technology. This includes site information, project parameters,
        control strategy, and finance parameters.
        """
        plant_group = om.Group()

        # Create the plant model group and add components
        self.plant = self.model.add_subsystem("plant", plant_group, promotes=["*"])

    def create_technology_models(self):
        # Loop through each technology and instantiate an OpenMDAO object (assume it exists)
        # for each technology

        self.tech_names = []
        self.performance_models = []
        self.control_strategys = []
        self.cost_models = []
        self.financial_models = []

        combined_performance_and_cost_models = ["hopp", "h2_storage", "wombat"]

        # Create a technology group for each technology
        for tech_name, individual_tech_config in self.technology_config["technologies"].items():
            if "feedstocks" in tech_name:
                feedstock_component = FeedstockComponent(feedstocks_config=individual_tech_config)
                self.plant.add_subsystem(tech_name, feedstock_component)
            else:
                tech_group = self.plant.add_subsystem(tech_name, om.Group())
                self.tech_names.append(tech_name)

                # Check if performance, cost, and financial models are the same
                # and in combined_performance_and_cost_models
                perf_model = individual_tech_config.get("performance_model", {}).get("model")
                cost_model = individual_tech_config.get("cost_model", {}).get("model")
                individual_tech_config.get("financial_model", {}).get("model")
                if (
                    perf_model
                    and perf_model == cost_model
                    and perf_model in combined_performance_and_cost_models
                ):
                    comp = self.supported_models[perf_model](
                        driver_config=self.driver_config,
                        plant_config=self.plant_config,
                        tech_config=individual_tech_config,
                    )
                    tech_group.add_subsystem(tech_name, comp, promotes=["*"])
                    self.performance_models.append(comp)
                    self.cost_models.append(comp)
                    self.financial_models.append(comp)

                    # Catch control models for systems that have the same performance & cost models
                    if "control_strategy" in individual_tech_config:
                        control_object = self._process_model(
                            "control_strategy", individual_tech_config, tech_group
                        )
                        self.control_strategys.append(control_object)
                    continue

                # Process the models
                # TODO: integrate financial_model into the loop below
                model_types = ["performance_model", "control_strategy", "cost_model"]
                for model_type in model_types:
                    if model_type in individual_tech_config:
                        model_object = self._process_model(
                            model_type, individual_tech_config, tech_group
                        )
                        getattr(self, model_type + "s").append(model_object)
                    elif model_type == "performance_model":
                        raise KeyError("Model definition requires 'performance_model'.")

                # Process the financial models
                if "financial_model" in individual_tech_config:
                    if "model" in individual_tech_config["financial_model"]:
                        financial_name = individual_tech_config["financial_model"]["model"]

                        financial_object = self.supported_models[financial_name]
                        tech_group.add_subsystem(
                            f"{tech_name}_financial",
                            financial_object(
                                driver_config=self.driver_config,
                                plant_config=self.plant_config,
                                tech_config=individual_tech_config,
                            ),
                            promotes=["*"],
                        )
                        self.financial_models.append(financial_object)

    def _process_model(self, model_type, individual_tech_config, tech_group):
        # Generalized function to process model definitions
        model_name = individual_tech_config[model_type]["model"]
        model_object = self.supported_models[model_name]
        tech_group.add_subsystem(
            model_name,
            model_object(
                driver_config=self.driver_config,
                plant_config=self.plant_config,
                tech_config=individual_tech_config,
            ),
            promotes=["*"],
        )
        return model_object

    def create_financial_model(self):
        """
        Creates and configures the financial model for the plant.

        Creates financial groups based on the technology configurations
        and adds the appropriate financial components to each group.
        """

        if "finance_parameters" not in self.plant_config:
            return

        # Create a dictionary to hold financial groups
        financial_groups = {}

        # Loop through each technology and add it to the appropriate financial group
        for tech_name, individual_tech_config in self.technology_config["technologies"].items():
            financial_group_id = individual_tech_config.get("financial_model", {}).get("group")
            if financial_group_id is not None:
                if financial_group_id not in financial_groups:
                    financial_groups[financial_group_id] = {}
                financial_groups[financial_group_id][tech_name] = individual_tech_config

        # Find technologies not assigned to any financial group and add them to group "default"
        all_grouped_techs = set()
        for group in financial_groups.values():
            all_grouped_techs.update(group.keys())

        for tech_name, tech_config in self.technology_config["technologies"].items():
            if tech_name not in all_grouped_techs:
                if "default" not in financial_groups:
                    financial_groups["default"] = {}
                financial_groups["default"][tech_name] = tech_config

        # Add each financial group to the plant
        for group_id, tech_configs in financial_groups.items():
            commodity_types = []
            if "steel" in tech_configs:
                commodity_types.append("steel")
            if "electrolyzer" in tech_configs:
                commodity_types.append("hydrogen")
            if "methanol" in tech_configs:
                commodity_types.append("methanol")
            if "ammonia" in tech_configs:
                commodity_types.append("ammonia")
            if "air_separator" in tech_configs:
                commodity_types.append("nitrogen")
            if "geoh2" in tech_configs:
                commodity_types.append("hydrogen")
            if "doc" in tech_configs:
                commodity_types.append("co2")
            for tech in electricity_producing_techs:
                if tech in tech_configs:
                    commodity_types.append("electricity")
                    continue

            # Steel, methanol provides their own financials
            if any(c in commodity_types for c in ("steel", "methanol")):
                continue

            # GeoH2 provides own financials
            if "geoh2" in tech_configs:
                continue

            if commodity_types == []:
                continue

            financial_group = om.Group()

            # Determine all technologies that should be included across all
            # commodity types for this group
            all_included_techs = set()
            for commodity_type in commodity_types:
                if commodity_type not in ["steel", "methanol"]:  # These handle their own financials
                    included_techs = self.get_included_technologies(
                        tech_configs, commodity_type, self.plant_config
                    )
                    all_included_techs.update(included_techs)

            # Filter tech_configs to only include technologies that are in at least one stackup
            filtered_tech_configs_for_capex = {
                tech: config for tech, config in tech_configs.items() if tech in all_included_techs
            }

            # Add the ExecComp to the plant model
            financial_group.add_subsystem(
                "electricity_sum", ElectricitySumComp(tech_configs=filtered_tech_configs_for_capex)
            )

            # Add adjusted capex component
            adjusted_capex_opex_comp = AdjustedCapexOpexComp(
                driver_config=self.driver_config,
                tech_config=filtered_tech_configs_for_capex,
                plant_config=self.plant_config,
            )
            financial_group.add_subsystem(
                "adjusted_capex_opex_comp", adjusted_capex_opex_comp, promotes=["*"]
            )

            # Add profast components
            for idx, commodity_type in enumerate(commodity_types):
                # Get included technologies for this commodity type
                included_techs = self.get_included_technologies(
                    tech_configs, commodity_type, self.plant_config
                )

                # Filter tech_configs to only include the technologies in the stackup
                filtered_tech_configs = {
                    tech: config for tech, config in tech_configs.items() if tech in included_techs
                }

                profast_comp = ProFastComp(
                    driver_config=self.driver_config,
                    tech_config=filtered_tech_configs,
                    plant_config=self.plant_config,
                    commodity_type=commodity_type,
                )
                financial_group.add_subsystem(f"profast_comp_{idx}", profast_comp, promotes=["*"])

            self.plant.add_subsystem(f"financials_group_{group_id}", financial_group)

        self.financial_groups = financial_groups

    def get_included_technologies(self, tech_config, commodity_type, plant_config):
        """
        Determine which technologies should be included in the financial metrics.

        Args:
            tech_config: Dictionary of technology configurations
            commodity_type: Type of commodity (e.g., 'hydrogen', 'electricity', 'ammonia')
            plant_config: Plant configuration dictionary

        Returns:
            List of technology names to include in the financial stackup
        """
        # Check if the user defined specific technologies to include in the metrics.
        # If provided, only include those technologies in the stackup.
        # If not provided, include all technologies in the financial group in the stackup.
        metrics_map = {
            "hydrogen": "LCOH",
            "electricity": "LCOE",
            "ammonia": "LCOA",
            "nitrogen": "LCON",
        }
        metric_key = metrics_map.get(commodity_type)
        included_techs = (
            plant_config["finance_parameters"]
            .get("technologies_included_in_metrics", {})
            .get(metric_key, None)
        )

        # Check if the included technologies are valid
        if included_techs is not None:
            missing_techs = [tech for tech in included_techs if tech not in tech_config]
            if missing_techs:
                raise ValueError(
                    f"Included technology(ies) {missing_techs} not found in tech_config. "
                    f"Available techs: {list(tech_config.keys())}"
                )

        # If no specific technologies are included, default to all technologies in tech_config
        if included_techs is None:
            included_techs = list(tech_config.keys())

        return included_techs

    def connect_technologies(self):
        technology_interconnections = self.plant_config.get("technology_interconnections", [])

        combiner_counts = {}

        # loop through each linkage and instantiate an OpenMDAO object (assume it exists) for
        # the connection type (e.g. cable, pipeline, etc)
        for connection in technology_interconnections:
            if len(connection) == 4:
                source_tech, dest_tech, transport_item, transport_type = connection

                # make the connection_name based on source, dest, item, type
                connection_name = f"{source_tech}_to_{dest_tech}_{transport_type}"

                # Create the transport object
                connection_component = self.supported_models[transport_type]()

                # Add the connection component to the model
                self.plant.add_subsystem(connection_name, connection_component)

                if "storage" in source_tech:
                    # Connect the source technology to the connection component
                    self.plant.connect(
                        f"{source_tech}.{transport_item}_out",
                        f"{connection_name}.{transport_item}_in",
                    )
                else:
                    # Connect the source technology to the connection component
                    self.plant.connect(
                        f"{source_tech}.{transport_item}_out",
                        f"{connection_name}.{transport_item}_in",
                    )

                # Check if the transport type is a combiner
                if "combiner" in dest_tech:
                    # Connect the source technology to the connection component
                    # with specific input names
                    if dest_tech not in combiner_counts:
                        combiner_counts[dest_tech] = 1
                    else:
                        combiner_counts[dest_tech] += 1

                    # Connect the connection component to the destination technology
                    self.plant.connect(
                        f"{connection_name}.{transport_item}_out",
                        f"{dest_tech}.electricity_in{combiner_counts[dest_tech]}",
                    )

                elif "storage" in dest_tech:
                    # Connect the connection component to the destination technology
                    self.plant.connect(
                        f"{connection_name}.{transport_item}_out",
                        f"{dest_tech}.{transport_item}_in",
                    )

                else:
                    # Connect the connection component to the destination technology
                    self.plant.connect(
                        f"{connection_name}.{transport_item}_out",
                        f"{dest_tech}.{transport_item}_in",
                    )

            elif len(connection) == 3:
                # connect directly from source to dest
                source_tech, dest_tech, connected_parameter = connection

                self.plant.connect(
                    f"{source_tech}.{connected_parameter}", f"{dest_tech}.{connected_parameter}"
                )

            else:
                err_msg = f"Invalid connection: {connection}"
                raise ValueError(err_msg)

        resource_to_tech_connections = self.plant_config.get("resource_to_tech_connections", [])

        for connection in resource_to_tech_connections:
            if len(connection) != 3:
                err_msg = f"Invalid resource to tech connection: {connection}"
                raise ValueError(err_msg)

            resource_name, tech_name, variable = connection

            # Connect the resource output to the technology input
            self.model.connect(f"{resource_name}.{variable}", f"{tech_name}.{variable}")

        # TODO: connect outputs of the technology models to the cost and financial models of the
        # same name if the cost and financial models are not None
        if "finance_parameters" in self.plant_config:
            # Connect the outputs of the technology models to the appropriate financial groups
            for group_id, tech_configs in self.financial_groups.items():
                # Skip steel financials; it provides its own financials
                if any(c in tech_configs for c in ("steel", "methanol", "geoh2")):
                    continue

                plant_producing_electricity = False

                # Determine which commodity types this financial group handles
                commodity_types = []
                if "steel" in tech_configs:
                    commodity_types.append("steel")
                if "electrolyzer" in tech_configs:
                    commodity_types.append("hydrogen")
                if "methanol" in tech_configs:
                    commodity_types.append("methanol")
                if "ammonia" in tech_configs:
                    commodity_types.append("ammonia")
                if "geoh2" in tech_configs:
                    commodity_types.append("hydrogen")
                if "doc" in tech_configs:
                    commodity_types.append("co2")
                if "air_separator" in tech_configs:
                    commodity_types.append("nitrogen")
                for tech in electricity_producing_techs:
                    if tech in tech_configs:
                        commodity_types.append("electricity")
                        break

                # Get all included technologies for all commodity types in this group
                all_included_techs = set()
                for commodity_type in commodity_types:
                    if commodity_type not in [
                        "steel",
                        "methanol",
                    ]:  # These handle their own financials
                        included_techs = self.get_included_technologies(
                            tech_configs, commodity_type, self.plant_config
                        )
                        all_included_techs.update(included_techs)

                # Loop through technologies and connect electricity outputs to the ExecComp
                # Only connect if the technology is included in at least one commodity's stackup
                # and in this financial group
                for tech_name in tech_configs.keys():
                    if tech_name in electricity_producing_techs and tech_name in all_included_techs:
                        self.plant.connect(
                            f"{tech_name}.electricity_out",
                            f"financials_group_{group_id}.electricity_sum.electricity_{tech_name}",
                        )
                        plant_producing_electricity = True

                if plant_producing_electricity:
                    # Connect total electricity produced to the financial group
                    self.plant.connect(
                        f"financials_group_{group_id}.electricity_sum.total_electricity_produced",
                        f"financials_group_{group_id}.total_electricity_produced",
                    )

                # Only connect technologies that are included in the financial stackup
                for tech_name in tech_configs.keys():
                    if tech_name in all_included_techs:
                        self.plant.connect(
                            f"{tech_name}.CapEx", f"financials_group_{group_id}.capex_{tech_name}"
                        )
                        self.plant.connect(
                            f"{tech_name}.OpEx", f"financials_group_{group_id}.opex_{tech_name}"
                        )

                        if "electrolyzer" in tech_name:
                            self.plant.connect(
                                f"{tech_name}.total_hydrogen_produced",
                                f"financials_group_{group_id}.total_hydrogen_produced",
                            )
                            self.plant.connect(
                                f"{tech_name}.time_until_replacement",
                                f"financials_group_{group_id}.time_until_replacement",
                            )

                        if "ammonia" in tech_name:
                            self.plant.connect(
                                f"{tech_name}.total_ammonia_produced",
                                f"financials_group_{group_id}.total_ammonia_produced",
                            )

                        if "doc" in tech_name:
                            self.plant.connect(
                                f"{tech_name}.co2_capture_mtpy",
                                f"financials_group_{group_id}.co2_capture_kgpy",
                            )
                        if "air_separator" in tech_name:
                            self.plant.connect(
                                f"{tech_name}.total_nitrogen_produced",
                                f"financials_group_{group_id}.total_nitrogen_produced",
                            )

        self.plant.options["auto_order"] = True

        # Check if there are any connections FROM a financial group to ammonia
        # This handles the case where LCOH is computed in the financial group and passed to ammonia
        for connection in technology_interconnections:
            if connection[0].startswith("financials_group_") and connection[1] == "ammonia":
                # If the connection is from a financial group, set solvers for the
                # plant to resolve the coupling
                self.plant.nonlinear_solver = om.NonlinearBlockGS()
                self.plant.linear_solver = om.DirectSolver()
                break

        if pyxdsm is not None:
            create_xdsm_from_config(self.plant_config)

    def create_driver_model(self):
        """
        Add the driver to the OpenMDAO model.
        """
        if "driver" in self.driver_config:
            myopt = PoseOptimization(self.driver_config)
            myopt.set_driver(self.prob)
            myopt.set_objective(self.prob)
            myopt.set_design_variables(self.prob)
            myopt.set_constraints(self.prob)

    def run(self):
        # do model setup based on the driver config
        # might add a recorder, driver, set solver tolerances, etc

        # Add a recorder if specified in the driver config
        if "recorder" in self.driver_config:
            recorder_config = self.driver_config["recorder"]
            recorder = om.SqliteRecorder(recorder_config["file"])
            self.model.add_recorder(recorder)

        self.prob.setup()

        self.prob.run_driver()

    def post_process(self):
        self.prob.model.list_inputs(units=True)
        self.prob.model.list_outputs(units=True)
